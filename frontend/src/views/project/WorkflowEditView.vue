<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { projectsApi } from '@/api/projects'
import { Plus, Trash2, Save, ArrowLeft, ChevronUp, ChevronDown } from 'lucide-vue-next'
import WorkflowEditorCanvas from '@/components/WorkflowEditorCanvas.vue'
import type { WNode } from '@/components/WorkflowEditorCanvas.vue'

const route = useRoute()
const router = useRouter()

const projectId = computed(() => route.params.projectId as string)
const workflowId = computed(() => route.params.workflowId as string | undefined)
const isEdit = computed(() => !!workflowId.value)

// ── Form state ────────────────────────────────────────────────────────────
const name = ref('')
const description = ref('')
const allowParallel = ref(false)
const suppressSuccessAlerts = ref(false)
const artifactCacheId = ref('')
const artifactCaches = ref<any[]>([])

const nodes = ref<WNode[]>([])

interface SurveyVar {
  name: string
  title: string
  description: string
  type: string
  required: boolean
  default: string
  values: string[]
  _valuesStr: string
}

const surveyVars = ref<SurveyVar[]>([])
const templates = ref<any[]>([])

const saving = ref(false)
const loading = ref(false)
const error = ref('')

function addSurveyVar() {
  surveyVars.value.push({ name: '', title: '', description: '', type: 'string', required: false, default: '', values: [], _valuesStr: '' })
}
function removeSurveyVar(index: number) { surveyVars.value.splice(index, 1) }
function moveSurveyVar(i: number, dir: -1 | 1) {
  const j = i + dir
  if (j < 0 || j >= surveyVars.value.length) return
  const tmp = surveyVars.value[i]; surveyVars.value[i] = surveyVars.value[j]; surveyVars.value[j] = tmp
}
function addSeparator() {
  surveyVars.value.push({ name: `sep_${Date.now()}`, title: '', description: '', type: 'separator', required: false, default: '', values: [], _valuesStr: '' })
}

async function loadTemplates() {
  try {
    const { data } = await projectsApi.listTemplates(projectId.value, 1, 200)
    templates.value = data.items ?? []
  } catch {
    templates.value = []
  }
}

async function loadWorkflow() {
  if (!isEdit.value || !workflowId.value) return
  loading.value = true
  try {
    const { data } = await projectsApi.getWorkflow(projectId.value, workflowId.value)
    name.value = data.name ?? ''
    description.value = data.description ?? ''
    allowParallel.value = data.allow_parallel ?? false
    suppressSuccessAlerts.value = data.suppress_success_alerts ?? false
    artifactCacheId.value = data.artifact_cache_id ?? ''
    nodes.value = (data.nodes ?? []).map((n: any) => ({
      node_id: n.node_id,
      node_type: n.node_type ?? 'task',
      slug: n.slug ?? '',
      label: n.label ?? '',
      template_id: n.template_id ?? null,
      on_success: n.on_success ?? [],
      on_failure: n.on_failure ?? [],
      on_always: n.on_always ?? [],
      position_x: n.position_x ?? 0,
      position_y: n.position_y ?? 0,
    }))
    surveyVars.value = (data.survey_vars ?? []).map((sv: any) => ({
      name: sv.name ?? '',
      title: sv.title ?? '',
      description: sv.description ?? '',
      type: sv.type ?? 'string',
      required: sv.required ?? false,
      default: sv.default ?? '',
      values: sv.values ?? [],
      _valuesStr: Array.isArray(sv.values) ? sv.values.join('\n') : '',
    }))
  } catch (e: any) {
    error.value = e.response?.data?.message || 'Failed to load workflow'
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  const [,, acRes] = await Promise.all([
    loadTemplates(),
    loadWorkflow(),
    import('@/api/client').then(m => m.default.get(`/projects/${projectId.value}/artifact-caches`)),
  ])
  artifactCaches.value = acRes.data ?? []
})

async function save() {
  error.value = ''
  if (!name.value.trim()) {
    error.value = 'Name is required'
    return
  }

  const payload = {
    name: name.value.trim(),
    description: description.value.trim(),
    allow_parallel: allowParallel.value,
    suppress_success_alerts: suppressSuccessAlerts.value,
    artifact_cache_id: artifactCacheId.value || null,
    nodes: nodes.value.map(n => ({
      node_id: n.node_id,
      node_type: n.node_type ?? 'task',
      slug: n.node_type === 'question' ? (n.slug || '') : '',
      label: n.label,
      template_id: n.node_type === 'question' ? null : (n.template_id || null),
      on_success: n.on_success,
      on_failure: n.on_failure,
      on_always: n.on_always,
      position_x: n.position_x,
      position_y: n.position_y,
    })),
    survey_vars: surveyVars.value.map(sv => ({
      name: sv.name,
      title: sv.title,
      description: sv.description,
      type: sv.type,
      required: sv.required,
      default: sv.default,
      values: sv.type === 'enum' ? sv._valuesStr.split('\n').map((v: string) => v.trim()).filter(Boolean) : [],
    })),
  }

  saving.value = true
  try {
    if (isEdit.value && workflowId.value) {
      await projectsApi.updateWorkflow(projectId.value, workflowId.value, payload)
    } else {
      await projectsApi.createWorkflow(projectId.value, payload)
    }
    router.push(`/projects/${projectId.value}/workflows`)
  } catch (e: any) {
    error.value = e.response?.data?.message || 'Failed to save workflow'
  } finally {
    saving.value = false
  }
}

function cancel() {
  router.push(`/projects/${projectId.value}/workflows`)
}

const SURVEY_TYPES = ['string', 'int', 'enum', 'secret', 'bool', 'separator']
</script>

<template>
  <div>
    <!-- Header -->
    <div class="flex items-center gap-3 mb-6">
      <button @click="cancel" class="p-1.5 text-gray-400 hover:text-gray-600 transition-colors">
        <ArrowLeft class="w-5 h-5" />
      </button>
      <h2 class="text-lg font-medium text-gray-900">
        {{ isEdit ? 'Edit Workflow' : 'New Workflow' }}
      </h2>
    </div>

    <div v-if="loading" class="text-center text-gray-400 py-12">Loading…</div>
    <form v-else @submit.prevent="save" class="space-y-8">

      <!-- Basic Info -->
      <div class="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
        <h3 class="text-sm font-semibold text-gray-700 uppercase tracking-wide">Basic Info</h3>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Name <span class="text-red-500">*</span></label>
          <input
            v-model="name"
            type="text"
            class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            placeholder="My Workflow"
          />
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Description</label>
          <textarea
            v-model="description"
            rows="2"
            class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            placeholder="Optional description"
          />
        </div>

        <div class="flex gap-6">
          <label class="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
            <input type="checkbox" v-model="allowParallel" class="rounded" />
            Allow parallel execution
          </label>
          <label class="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
            <input type="checkbox" v-model="suppressSuccessAlerts" class="rounded" />
            Suppress success alerts
          </label>
        </div>
      </div>

      <!-- Artifact Cache -->
      <div class="bg-white rounded-xl border border-gray-200 p-5 space-y-3">
        <h3 class="text-sm font-semibold text-gray-700 uppercase tracking-wide">Artifact Cache</h3>
        <p class="text-xs text-gray-400">All nodes in this workflow share one artifact token. Downstream tasks can read artifacts uploaded by earlier nodes.</p>
        <div>
          <label class="block text-xs font-medium text-gray-600 mb-1">Cache</label>
          <select v-model="artifactCacheId"
            class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 bg-white">
            <option value="">— none —</option>
            <option v-for="ac in artifactCaches" :key="ac.id" :value="ac.id">
              {{ ac.name }}{{ ac.retention_days ? ` (${ac.retention_days}d)` : ' (no expiry)' }}
            </option>
          </select>
        </div>
      </div>

      <!-- Workflow Canvas -->
      <div class="bg-white rounded-xl border border-gray-200 p-6 space-y-3">
        <div>
          <h3 class="text-sm font-semibold text-gray-700 uppercase tracking-wide">Workflow</h3>
          <p class="text-xs text-gray-400 mt-1">
            Hover over a node and click ✓ / ✗ / → to add a connected step.
            Click a node to edit or delete it. Drag to reposition.
          </p>
        </div>
        <WorkflowEditorCanvas
          v-model:nodes="nodes"
          :templates="templates"
        />
      </div>

      <!-- Survey Variables -->
      <div class="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
        <div class="flex items-center justify-between">
          <div>
            <h3 class="text-sm font-semibold text-gray-700 uppercase tracking-wide">Survey Variables</h3>
            <p class="text-xs text-gray-400 mt-0.5">Prompted before each run — passed as extra variables to node tasks.</p>
          </div>
          <div class="flex items-center gap-3">
            <button type="button" @click="addSurveyVar"
              class="flex items-center gap-1.5 text-xs text-brand-600 hover:text-brand-700">
              <Plus class="w-3.5 h-3.5" /> Add variable
            </button>
            <button type="button" @click="addSeparator"
              class="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-700">
              <Plus class="w-3.5 h-3.5" /> Add separator
            </button>
          </div>
        </div>

        <p v-if="surveyVars.length === 0" class="text-sm text-gray-400 italic">
          No survey variables. These are prompted before the workflow starts.
        </p>

        <div v-for="(sv, i) in surveyVars" :key="i" class="border border-gray-100 rounded-lg p-4 space-y-3 bg-gray-50">
          <div class="flex items-center justify-between mb-1">
            <span class="text-xs font-medium text-gray-500 uppercase tracking-wide">
              {{ sv.type === 'separator' ? 'Separator' : `Variable ${i + 1}` }}
            </span>
            <div class="flex items-center gap-1">
              <button type="button" @click="moveSurveyVar(i, -1)" :disabled="i === 0"
                class="p-1 rounded text-gray-400 hover:text-gray-700 disabled:opacity-30 disabled:cursor-not-allowed">
                <ChevronUp class="w-3.5 h-3.5" />
              </button>
              <button type="button" @click="moveSurveyVar(i, 1)" :disabled="i === surveyVars.length - 1"
                class="p-1 rounded text-gray-400 hover:text-gray-700 disabled:opacity-30 disabled:cursor-not-allowed">
                <ChevronDown class="w-3.5 h-3.5" />
              </button>
              <button type="button" @click="removeSurveyVar(i)" class="p-1 text-red-400 hover:text-red-600">
                <Trash2 class="w-4 h-4" />
              </button>
            </div>
          </div>

          <!-- Separator -->
          <div v-if="sv.type === 'separator'">
            <label class="block text-xs font-medium text-gray-600 mb-1">Section title <span class="font-normal text-gray-400">(optional)</span></label>
            <input v-model="sv.title" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" placeholder="e.g. Deployment options" />
          </div>

          <!-- Variable fields -->
          <div v-else class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-xs font-medium text-gray-600 mb-1">Name (identifier) *</label>
              <input v-model="sv.name" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-brand-500" placeholder="my_var" />
            </div>
            <div>
              <label class="block text-xs font-medium text-gray-600 mb-1">Title (display label)</label>
              <input v-model="sv.title" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
            </div>
            <div>
              <label class="block text-xs font-medium text-gray-600 mb-1">Type</label>
              <select v-model="sv.type" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500">
                <option value="string">String</option>
                <option value="int">Integer</option>
                <option value="enum">Enum (dropdown)</option>
                <option value="secret">Secret (masked)</option>
                <option value="bool">Boolean (checkbox)</option>
              </select>
            </div>
            <div>
              <label class="block text-xs font-medium text-gray-600 mb-1">Default value</label>
              <select v-if="sv.type === 'bool'" v-model="sv.default" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500">
                <option value="false">false</option>
                <option value="true">true</option>
              </select>
              <input v-else v-model="sv.default" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                :type="sv.type === 'secret' ? 'password' : 'text'" />
            </div>
            <div v-if="sv.type === 'enum'" class="col-span-2">
              <label class="block text-xs font-medium text-gray-600 mb-1">Choices — one per line</label>
              <textarea v-model="sv._valuesStr" rows="4" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-xs font-mono focus:outline-none focus:ring-2 focus:ring-brand-500"
                placeholder="staging|Staging Environment&#10;production|Production (live!)&#10;development" />
              <p class="text-xs text-gray-400 mt-1">
                Format: <code class="bg-gray-100 px-1 rounded">value</code> or
                <code class="bg-gray-100 px-1 rounded">value|Display label</code>
              </p>
            </div>
            <div class="col-span-2">
              <label class="block text-xs font-medium text-gray-600 mb-1">Description / help text</label>
              <input v-model="sv.description" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
            </div>
            <div class="col-span-2">
              <label class="flex items-center gap-2 text-sm">
                <input v-model="sv.required" type="checkbox" class="rounded" />
                Required — run cannot start without a value
              </label>
            </div>
          </div>
        </div>
      </div>

      <!-- Error -->
      <p v-if="error" class="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-3">
        {{ error }}
      </p>

      <!-- Actions -->
      <div class="flex gap-3">
        <button
          type="submit"
          :disabled="saving"
          class="flex items-center gap-2 bg-brand-600 hover:bg-brand-700 text-white text-sm px-4 py-2 rounded-lg disabled:opacity-60"
        >
          <Save class="w-4 h-4" />
          {{ saving ? 'Saving…' : (isEdit ? 'Save changes' : 'Create workflow') }}
        </button>
        <button
          type="button"
          @click="cancel"
          class="text-sm text-gray-600 hover:text-gray-800 px-4 py-2 rounded-lg border border-gray-200 hover:bg-gray-50"
        >
          Cancel
        </button>
      </div>
    </form>
  </div>
</template>
