<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import { projectsApi } from '@/api/projects'
import api from '@/api/client'
import { Plus, Trash2, ChevronUp, ChevronDown } from 'lucide-vue-next'
import { parseEnumOptions } from '@/composables/useEnumOptions'

const route = useRoute()
const router = useRouter()
const projectId = computed(() => route.params.projectId as string)
const templateId = computed(() => route.params.templateId as string | undefined)
const isEdit = computed(() => !!templateId.value)

// ── Resources ────────────────────────────────────────────────────────────
const repos = ref<any[]>([])
const inventories = ref<any[]>([])
const environments = ref<any[]>([])
const keys = ref<any[]>([])
const customApps = ref<any[]>([])
const allCredentials = ref<any[]>([])
const allCredentialTypes = ref<any[]>([])
const artifactCaches = ref<any[]>([])

// ── Form state ───────────────────────────────────────────────────────────
const form = ref({
  name: '',
  description: '',
  app: 'bash',
  type: 'task',
  playbook: '',
  repository_id: '',
  inventory_id: '',
  environment_id: '',
  arguments: '[]',
  allow_override_args: false,
  allow_parallel: false,
  suppress_success_alerts: false,
  autorun: false,
  start_version: '',       // build type: e.g. "1.0.0"
  build_template_id: '',   // deploy type: linked build template
  artifact_cache_id: '',   // optional: artifact cache for this template
})

interface SurveyVar {
  name: string
  title: string
  description: string
  type: 'string' | 'int' | 'enum' | 'secret' | 'bool' | 'separator'
  required: boolean
  default: string
  values: string
}

const surveyVars = ref<SurveyVar[]>([])
const vaultKeys = ref<{ vault_id: string; name: string; key_id: string }[]>([])
const selectedCredentialIds = ref<string[]>([])

const saving = ref(false)
const error = ref('')
const argumentsRaw = ref('') // displayed in textarea, validated on save

const appTypes = computed(() => [
  { value: 'bash', label: 'Shell / Bash' },
  { value: 'python', label: 'Python' },
  { value: 'ansible', label: 'Ansible Playbook' },
  ...customApps.value.map(ca => ({ value: ca.slug, label: ca.title })),
])

const isAnsible  = computed(() => form.value.app === 'ansible')
const isBuild    = computed(() => form.value.type === 'build')
const isDeploy   = computed(() => form.value.type === 'deploy')
// For deploy: only show build-type templates from the same project
const buildTemplates = computed(() => repos.value ? [] : []) // populated below
const buildTemplateList = ref<any[]>([])
const vaultKeysOptions = computed(() => keys.value.filter(k => k.type === 'vault'))

// ── Lifecycle ────────────────────────────────────────────────────────────
onMounted(async () => {
  const [reposRes, invRes, envRes, keysRes, appsRes, tmplRes, credsRes, ctRes, acRes] = await Promise.all([
    projectsApi.listRepos(projectId.value),
    projectsApi.listInventories(projectId.value),
    projectsApi.listEnvironments(projectId.value),
    projectsApi.listKeys(projectId.value),
    api.get('/custom-apps'),
    projectsApi.listTemplates(projectId.value),
    projectsApi.listCredentials(projectId.value),
    api.get('/credential-types'),
    api.get(`/projects/${projectId.value}/artifact-caches`),
  ])
  repos.value = reposRes.data
  inventories.value = invRes.data
  environments.value = envRes.data
  keys.value = keysRes.data
  customApps.value = appsRes.data
  allCredentials.value = credsRes.data
  allCredentialTypes.value = ctRes.data
  artifactCaches.value = acRes.data ?? []
  // Only build-type templates can be referenced by deploy templates
  const tmplItems: any[] = tmplRes.data?.items ?? tmplRes.data ?? []
  buildTemplateList.value = tmplItems.filter((t: any) => t.type === 'build')

  if (isEdit.value) {
    const { data } = await projectsApi.getTemplate(projectId.value, templateId.value!)
    form.value = {
      name: data.name,
      description: data.description || '',
      app: data.app,
      type: data.type,
      playbook: data.playbook || '',
      repository_id: data.repository_id || '',
      inventory_id: data.inventory_id || '',
      environment_id: data.environment_id || '',
      arguments: data.arguments || '[]',
      allow_override_args: data.allow_override_args,
      allow_parallel: data.allow_parallel,
      suppress_success_alerts: data.suppress_success_alerts,
      autorun: data.autorun || false,
      start_version: data.start_version || '',
      build_template_id: data.build_template_id || '',
    }
    argumentsRaw.value = formatArgs(data.arguments)
    surveyVars.value = (data.survey_vars || []).map((sv: any) => ({
      ...sv,
      values: Array.isArray(sv.values) ? sv.values.join('\n') : '',
    }))
    vaultKeys.value = (data.vaults || []).map((v: any) => ({
      vault_id: v.vault_id,
      name: v.name || '',
      key_id: v.key_id || '',
    }))
    selectedCredentialIds.value = data.credential_ids || []
    form.value.artifact_cache_id = data.artifact_cache_id || ''
  } else {
    argumentsRaw.value = ''
  }
})

function formatArgs(raw: string): string {
  try {
    const arr = JSON.parse(raw || '[]')
    return Array.isArray(arr) ? arr.join('\n') : ''
  } catch {
    return ''
  }
}

function parseArgs(raw: string): string {
  const lines = raw.split('\n').map(l => l.trim()).filter(Boolean)
  return JSON.stringify(lines)
}

// ── Survey vars ──────────────────────────────────────────────────────────
function addSurveyVar() {
  surveyVars.value.push({ name: '', title: '', description: '', type: 'string', required: false, default: '', values: '' })
}
function removeSurveyVar(i: number) {
  surveyVars.value.splice(i, 1)
}
function moveSurveyVar(i: number, dir: -1 | 1) {
  const j = i + dir
  if (j < 0 || j >= surveyVars.value.length) return
  const tmp = surveyVars.value[i]
  surveyVars.value[i] = surveyVars.value[j]
  surveyVars.value[j] = tmp
}
function addSeparator() {
  surveyVars.value.push({ name: `sep_${Date.now()}`, title: '', description: '', type: 'separator', required: false, default: '', values: '' })
}

// ── Vault refs ───────────────────────────────────────────────────────────
function addVault() {
  vaultKeys.value.push({ vault_id: `vault${vaultKeys.value.length + 1}`, name: '', key_id: '' })
}
function removeVault(i: number) {
  vaultKeys.value.splice(i, 1)
}

// ── Save ─────────────────────────────────────────────────────────────────
async function save() {
  error.value = ''
  saving.value = true
  try {
    const payload = {
      ...form.value,
      arguments: parseArgs(argumentsRaw.value),
      repository_id: form.value.repository_id || null,
      inventory_id: form.value.inventory_id || null,
      environment_id: form.value.environment_id || null,
      survey_vars: surveyVars.value.map(sv => ({
        name: sv.name,
        title: sv.title,
        description: sv.description,
        type: sv.type,
        required: sv.required,
        default: sv.default,
        values: sv.type === 'enum' ? sv.values.split('\n').map((v: string) => v.trim()).filter(Boolean) : [],
      })),
      credential_ids: selectedCredentialIds.value,
      artifact_cache_id: form.value.artifact_cache_id || null,
      vaults: vaultKeys.value.filter(v => v.vault_id && v.key_id).map(v => ({
        vault_id: v.vault_id,
        name: v.name,
        key_id: v.key_id || null,
      })),
      start_version:     isBuild.value  ? form.value.start_version : '',
      build_template_id: isDeploy.value ? form.value.build_template_id || null : null,
    }
    if (isEdit.value) {
      await projectsApi.updateTemplate(projectId.value, templateId.value!, payload)
    } else {
      await projectsApi.createTemplate(projectId.value, payload)
    }
    router.push(`/projects/${projectId.value}`)
  } catch (e: any) {
    error.value = e.response?.data?.message || 'Failed to save template'
  } finally {
    saving.value = false
  }
}

const playbookLabel = computed(() => {
  if (form.value.app === 'ansible') return 'Playbook file (relative to repo root)'
  if (form.value.app === 'python') return 'Script file (relative to repo root)'
  return 'Script file (relative to repo root)'
})

const playbookPlaceholder = computed(() => {
  if (form.value.app === 'ansible') return 'site.yml'
  if (form.value.app === 'python') return 'main.py'
  return 'run.sh'
})
</script>

<template>
  <div class="max-w-3xl">
    <div class="flex items-center gap-3 mb-6">
      <button @click="router.back()" class="text-sm text-gray-400 hover:text-gray-600">← Back</button>
      <h2 class="text-xl font-semibold text-gray-900">{{ isEdit ? 'Edit Template' : 'New Template' }}</h2>
    </div>

    <form @submit.prevent="save" class="space-y-6">

      <!-- Basic info -->
      <section class="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
        <h3 class="font-medium text-gray-900">Basic info</h3>
        <div class="grid grid-cols-2 gap-4">
          <div class="col-span-2">
            <label class="label">Name *</label>
            <input v-model="form.name" required class="input" placeholder="Deploy production" />
          </div>
          <div class="col-span-2">
            <label class="label">Description</label>
            <input v-model="form.description" class="input" placeholder="Optional description" />
          </div>
          <div>
            <label class="label">App type *</label>
            <select v-model="form.app" class="input">
              <option v-for="a in appTypes" :key="a.value" :value="a.value">{{ a.label }}</option>
            </select>
          </div>
          <div>
            <label class="label">Template type *</label>
            <select v-model="form.type" class="input">
              <option value="task">Task — standard run</option>
              <option value="build">Build — produces a versioned artifact</option>
              <option value="deploy">Deploy — deploys a build artifact</option>
            </select>
          </div>

          <!-- Build: start version -->
          <template v-if="isBuild">
            <div class="col-span-2 bg-green-50 border border-green-200 rounded-xl p-4 space-y-2">
              <p class="text-xs font-semibold text-green-800">🏗 Build configuration</p>
              <p class="text-xs text-green-700">
                Defines the start version of your artifact. Each run automatically increments the patch number
                (e.g. <code class="bg-green-100 px-1 rounded">1.0.0</code> → <code class="bg-green-100 px-1 rounded">1.0.1</code> → <code class="bg-green-100 px-1 rounded">1.0.2</code>).
                The current version is available in your script as <code class="bg-green-100 px-1 rounded">$OACHKATZL_BUILD_VERSION</code>.
              </p>
              <div>
                <label class="label">Start version *</label>
                <input v-model="form.start_version" required
                  class="input font-mono"
                  placeholder="1.0.0"
                  pattern="^\d+\.\d+\.\d+$"
                  title="Format: x.y.z (e.g. 1.0.0)"
                />
                <p class="text-xs text-gray-400 mt-1">Format: <code>x.y.z</code> — only the last number is incremented per run.</p>
              </div>
            </div>
          </template>

          <!-- Deploy: link to build template -->
          <template v-if="isDeploy">
            <div class="col-span-2 bg-orange-50 border border-orange-200 rounded-xl p-4 space-y-2">
              <p class="text-xs font-semibold text-orange-800">🚀 Deploy configuration</p>
              <p class="text-xs text-orange-700">
                This template deploys artifacts to destination servers. It must be associated with a Build template.
                When running a deploy task, you select which build version to deploy.
                The version is available as <code class="bg-orange-100 px-1 rounded">$OACHKATZL_BUILD_VERSION</code>.
              </p>
              <div>
                <label class="label">Source build template *</label>
                <select v-model="form.build_template_id" class="input" :required="isDeploy">
                  <option value="">— Select build template —</option>
                  <option v-for="t in buildTemplateList" :key="t.id" :value="t.id">{{ t.name }}</option>
                </select>
                <p v-if="buildTemplateList.length === 0" class="text-xs text-orange-600 mt-1">
                  No build templates found. Create a template with type "Build" first.
                </p>
              </div>
            </div>
          </template>
        </div>
      </section>

      <!-- Execution -->
      <section class="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
        <h3 class="font-medium text-gray-900">Execution</h3>
        <div class="grid grid-cols-2 gap-4">
          <div class="col-span-2">
            <label class="label">{{ playbookLabel }}</label>
            <input v-model="form.playbook" class="input font-mono text-sm" :placeholder="playbookPlaceholder" />
            <p class="text-xs text-gray-400 mt-1">Path relative to the repository root. Leave blank to use the repo root.</p>
          </div>
          <div>
            <label class="label">Repository</label>
            <select v-model="form.repository_id" class="input">
              <option value="">— None —</option>
              <option v-for="r in repos" :key="r.id" :value="r.id">{{ r.name }} ({{ r.git_branch }})</option>
            </select>
          </div>
          <div v-if="isAnsible">
            <label class="label">Inventory</label>
            <select v-model="form.inventory_id" class="input">
              <option value="">— None —</option>
              <option v-for="i in inventories" :key="i.id" :value="i.id">{{ i.name }} ({{ i.type }})</option>
            </select>
          </div>
          <div :class="isAnsible ? '' : 'col-span-2'">
            <label class="label">Environment / Variables</label>
            <select v-model="form.environment_id" class="input">
              <option value="">— None —</option>
              <option v-for="e in environments" :key="e.id" :value="e.id">{{ e.name }}</option>
            </select>
          </div>
        </div>
      </section>

      <!-- Arguments -->
      <section class="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
        <h3 class="font-medium text-gray-900">Arguments &amp; flags</h3>
        <div>
          <label class="label">Extra arguments (one per line)</label>
          <textarea
            v-model="argumentsRaw"
            rows="3"
            class="input font-mono text-sm"
            :placeholder="isAnsible ? '--tags deploy\n--limit webservers' : '--verbose\n--dry-run'"
          />
          <p class="text-xs text-gray-400 mt-1">
            <span v-if="isAnsible">Passed directly to <code>ansible-playbook</code>.</span>
            <span v-else>Passed as CLI arguments to the script.</span>
          </p>
        </div>
        <div class="flex flex-wrap gap-6">
          <label class="flex items-center gap-2 text-sm">
            <input v-model="form.allow_override_args" type="checkbox" class="rounded" />
            Allow override arguments at run time
          </label>
          <label class="flex items-center gap-2 text-sm">
            <input v-model="form.allow_parallel" type="checkbox" class="rounded" />
            Allow parallel task runs
          </label>
          <label class="flex items-center gap-2 text-sm">
            <input v-model="form.suppress_success_alerts" type="checkbox" class="rounded" />
            Suppress success notifications
          </label>
          <label class="flex items-center gap-2 text-sm" :title="form.repository_id ? '' : 'Select a repository to enable commit watching'">
            <input v-model="form.autorun" type="checkbox" class="rounded" :disabled="!form.repository_id" />
            <span :class="!form.repository_id ? 'text-gray-400' : ''">
              Run a task when a new commit is added to the repository
            </span>
          </label>
        </div>
      </section>

      <!-- Ansible Vault -->
      <section v-if="isAnsible" class="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
        <div class="flex items-center justify-between">
          <h3 class="font-medium text-gray-900">Vault passwords</h3>
          <button type="button" @click="addVault" class="text-sm text-brand-600 hover:text-brand-700 flex items-center gap-1">
            <Plus class="w-3.5 h-3.5" /> Add vault
          </button>
        </div>
        <p v-if="vaultKeys.length === 0" class="text-sm text-gray-400">No vault passwords configured.</p>
        <div v-for="(v, i) in vaultKeys" :key="i" class="grid grid-cols-3 gap-3 items-end">
          <div>
            <label class="label">Vault ID</label>
            <input v-model="v.vault_id" class="input font-mono text-sm" placeholder="default" />
          </div>
          <div>
            <label class="label">Key (vault type)</label>
            <select v-model="v.key_id" class="input">
              <option value="">— Select key —</option>
              <option v-for="k in vaultKeysOptions" :key="k.id" :value="k.id">{{ k.name }}</option>
            </select>
          </div>
          <button type="button" @click="removeVault(i)" class="text-red-400 hover:text-red-600 pb-1">
            <Trash2 class="w-4 h-4" />
          </button>
        </div>
      </section>

      <!-- Credentials -->
      <section v-if="allCredentials.length > 0 || allCredentialTypes.length > 0"
        class="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
        <div class="flex items-center justify-between">
          <div>
            <h3 class="font-medium text-gray-900">Credentials</h3>
            <p class="text-xs text-gray-400 mt-0.5">Attach credentials whose values are injected at run time (env vars, extra vars, files).</p>
          </div>
        </div>

        <div v-if="allCredentials.length === 0" class="text-sm text-gray-400">
          No credentials in this project yet.
          <RouterLink :to="`/projects/${projectId}/credentials`" class="text-brand-600 hover:underline ml-1">Create one →</RouterLink>
        </div>

        <div v-else class="space-y-2">
          <div v-for="cred in allCredentials" :key="cred.id"
            class="flex items-center gap-3 p-3 rounded-lg border transition-colors cursor-pointer"
            :class="selectedCredentialIds.includes(cred.id)
              ? 'border-brand-300 bg-brand-50'
              : 'border-gray-200 hover:border-gray-300'"
            @click="selectedCredentialIds.includes(cred.id)
              ? selectedCredentialIds.splice(selectedCredentialIds.indexOf(cred.id), 1)
              : selectedCredentialIds.push(cred.id)"
          >
            <input type="checkbox" :checked="selectedCredentialIds.includes(cred.id)"
              class="rounded text-brand-600" @click.stop />
            <div class="min-w-0">
              <p class="text-sm font-medium text-gray-900">{{ cred.name }}</p>
              <p class="text-xs text-gray-400">{{ cred.credential_type_name }}</p>
            </div>
          </div>
        </div>
      </section>

      <!-- Artifact Cache -->
      <section class="bg-white rounded-xl border border-gray-200 p-5 space-y-3">
        <h3 class="font-medium text-gray-900">Artifact Cache</h3>
        <p class="text-xs text-gray-400">When a cache is selected, the task receives <code class="bg-gray-100 px-1 rounded">OACHKATZL_ARTIFACT_TOKEN</code> and <code class="bg-gray-100 px-1 rounded">OACHKATZL_ARTIFACT_URL</code> to upload files or JSON. In a workflow all nodes sharing the same cache token can read each other's artifacts.</p>
        <div>
          <label class="block text-xs font-medium text-gray-600 mb-1">Cache</label>
          <select v-model="form.artifact_cache_id"
            class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 bg-white">
            <option value="">— none —</option>
            <option v-for="ac in artifactCaches" :key="ac.id" :value="ac.id">
              {{ ac.name }}{{ ac.retention_days ? ` (${ac.retention_days}d)` : ' (no expiry)' }}
            </option>
          </select>
          <p v-if="artifactCaches.length === 0" class="text-xs text-gray-400 mt-1">
            No artifact caches in this project.
            <RouterLink :to="`/projects/${projectId}/artifact-caches`" class="text-brand-600 hover:underline ml-1">Create one →</RouterLink>
          </p>
        </div>
      </section>

      <!-- Survey Variables -->
      <section class="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
        <div class="flex items-center justify-between">
          <div>
            <h3 class="font-medium text-gray-900">Survey variables</h3>
            <p class="text-xs text-gray-400 mt-0.5">Prompted before each run — passed as extra variables to the script.</p>
          </div>
          <div class="flex items-center gap-3">
            <button type="button" @click="addSurveyVar" class="text-sm text-brand-600 hover:text-brand-700 flex items-center gap-1">
              <Plus class="w-3.5 h-3.5" /> Add variable
            </button>
            <button type="button" @click="addSeparator" class="text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1">
              <Plus class="w-3.5 h-3.5" /> Add separator
            </button>
          </div>
        </div>

        <p v-if="surveyVars.length === 0" class="text-sm text-gray-400">No survey variables.</p>

        <div v-for="(sv, i) in surveyVars" :key="i" class="border border-gray-100 rounded-lg p-4 space-y-3 bg-gray-50">
          <div class="flex items-center justify-between mb-1">
            <span class="text-xs font-medium text-gray-500 uppercase tracking-wide">
              {{ sv.type === 'separator' ? 'Separator' : `Variable ${i + 1}` }}
            </span>
            <div class="flex items-center gap-1">
              <button type="button" @click="moveSurveyVar(i, -1)" :disabled="i === 0"
                class="p-1 rounded text-gray-400 hover:text-gray-700 disabled:opacity-30 disabled:cursor-not-allowed"
                title="Move up">
                <ChevronUp class="w-3.5 h-3.5" />
              </button>
              <button type="button" @click="moveSurveyVar(i, 1)" :disabled="i === surveyVars.length - 1"
                class="p-1 rounded text-gray-400 hover:text-gray-700 disabled:opacity-30 disabled:cursor-not-allowed"
                title="Move down">
                <ChevronDown class="w-3.5 h-3.5" />
              </button>
              <button type="button" @click="removeSurveyVar(i)" class="p-1 text-red-400 hover:text-red-600">
                <Trash2 class="w-4 h-4" />
              </button>
            </div>
          </div>
          <!-- Separator: only title field -->
          <div v-if="sv.type === 'separator'" class="grid grid-cols-1 gap-3">
            <div>
              <label class="label">Section title <span class="font-normal text-gray-400">(optional)</span></label>
              <input v-model="sv.title" class="input" placeholder="e.g. Deployment options" />
            </div>
          </div>

          <div v-else class="grid grid-cols-2 gap-3">
            <div>
              <label class="label">Name (identifier) *</label>
              <input v-model="sv.name" class="input font-mono text-sm" placeholder="target_env" />
            </div>
            <div>
              <label class="label">Title (display label)</label>
              <input v-model="sv.title" class="input" placeholder="Target environment" />
            </div>
            <div>
              <label class="label">Type</label>
              <select v-model="sv.type" class="input">
                <option value="string">String</option>
                <option value="int">Integer</option>
                <option value="enum">Enum (dropdown)</option>
                <option value="secret">Secret (masked)</option>
                <option value="bool">Boolean (checkbox)</option>
              </select>
            </div>
            <div>
              <label class="label">Default value</label>
              <select v-if="sv.type === 'bool'" v-model="sv.default" class="input">
                <option value="false">false</option>
                <option value="true">true</option>
              </select>
              <input v-else v-model="sv.default" class="input" :type="sv.type === 'secret' ? 'password' : 'text'" />
            </div>
            <div v-if="sv.type === 'enum'" class="col-span-2">
              <label class="label">Choices — one per line</label>
              <textarea v-model="sv.values" rows="4" class="input font-mono text-xs"
                placeholder="staging|Staging Environment&#10;production|Production (live!)&#10;development" />
              <p class="text-xs text-gray-400 mt-1">
                Format: <code class="bg-gray-100 px-1 rounded">value</code> or
                <code class="bg-gray-100 px-1 rounded">value|Display label</code>
                — the part before <code class="bg-gray-100 px-1 rounded">|</code> is passed to the script,
                the part after is shown in the dropdown.
              </p>
            </div>
            <div class="col-span-2">
              <label class="label">Description / help text</label>
              <input v-model="sv.description" class="input" placeholder="Shown to the operator before run" />
            </div>
            <div class="col-span-2">
              <label class="flex items-center gap-2 text-sm">
                <input v-model="sv.required" type="checkbox" class="rounded" />
                Required — run cannot start without a value
              </label>
            </div>
          </div><!-- /v-else variable grid -->
        </div>
      </section>

      <!-- Error + Submit -->
      <div class="flex items-center gap-4">
        <button type="submit" :disabled="saving"
          class="bg-brand-600 hover:bg-brand-700 text-white font-medium px-6 py-2 rounded-lg disabled:opacity-60 transition-colors">
          {{ saving ? 'Saving…' : isEdit ? 'Save changes' : 'Create template' }}
        </button>
        <button type="button" @click="router.back()" class="text-sm text-gray-500 hover:text-gray-700">Cancel</button>
        <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
      </div>
    </form>
  </div>
</template>

<style scoped>
.label { @apply block text-xs font-medium text-gray-600 mb-1; }
.input { @apply w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500; }
</style>
