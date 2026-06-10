<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import api from '@/api/client'
import { X, Plus, Trash2, Copy, Check, Key } from 'lucide-vue-next'
import { parseEnumOptions } from '@/composables/useEnumOptions'

const props = defineProps<{
  open: boolean
  projectId: string
  template: { id: string; name: string; type?: string; survey_vars?: any[] } | null
}>()

const emit = defineEmits<{ close: [] }>()

// ── State ──────────────────────────────────────────────────────────────────
const tokens   = ref<any[]>([])
const loading  = ref(false)
const showForm = ref(false)
const saving   = ref(false)
const newToken = ref<{ id: string; token: string; name: string } | null>(null)
const copied   = ref(false)

const hasSurvey  = computed(() => (props.template?.survey_vars?.length ?? 0) > 0)
const isDeploy   = computed(() => props.template?.type === 'deploy')

const emptyForm = () => ({
  name:             '',
  survey_defaults:  {} as Record<string, string>,
  expires_at:       '',
  default_build_id: '',   // deploy: pinned build_task_id (stored as _build_task_id in survey_defaults)
})
const form = ref(emptyForm())

// ── Load tokens when modal opens ───────────────────────────────────────────
watch(() => props.open, async (open) => {
  if (!open || !props.template) return
  await loadTokens()
  showForm.value = false
  newToken.value = null
  form.value = emptyForm()
})

async function loadTokens() {
  loading.value = true
  try {
    const { data } = await api.get(
      `/projects/${props.projectId}/templates/${props.template!.id}/tokens`
    )
    tokens.value = data
  } finally {
    loading.value = false
  }
}

// ── Create token ───────────────────────────────────────────────────────────
async function createToken() {
  saving.value = true
  try {
    // For deploy templates, store the pinned build_task_id as a special key
    const surveyDefaults = { ...form.value.survey_defaults }
    if (isDeploy.value && form.value.default_build_id) {
      surveyDefaults['_build_task_id'] = form.value.default_build_id
    }
    const payload = {
      name:            form.value.name,
      survey_defaults: JSON.stringify(surveyDefaults),
      expires_at:      form.value.expires_at || null,
    }
    const { data } = await api.post(
      `/projects/${props.projectId}/templates/${props.template!.id}/tokens`,
      payload
    )
    newToken.value = { id: data.id, token: data.token, name: data.name }
    tokens.value.push(data)
    showForm.value = false
    form.value = emptyForm()
  } catch (e: any) {
    alert(e.response?.data?.message || 'Failed to create token')
  } finally {
    saving.value = false
  }
}

// ── Revoke token ───────────────────────────────────────────────────────────
async function revokeToken(id: string) {
  if (!confirm('Revoke this token? This cannot be undone.')) return
  await api.delete(
    `/projects/${props.projectId}/templates/${props.template!.id}/tokens/${id}`
  )
  tokens.value = tokens.value.filter(t => t.id !== id)
  if (newToken.value?.id === id) newToken.value = null
}

// ── Copy helpers ───────────────────────────────────────────────────────────
function executeUrl(token: string): string {
  return `${window.location.origin}/api/execute/${token}`
}

function curlExample(token: string): string {
  const url = executeUrl(token)
  const bodyParts: string[] = []

  if (isDeploy.value) {
    bodyParts.push('"build_task_id": "<task_id_of_build>"')
  }
  if (hasSurvey.value) {
    const vars = props.template?.survey_vars?.map(sv => `"${sv.name}": "value"`).join(', ')
    bodyParts.push(`"survey_answers": {${vars}}`)
  }

  let trigger: string
  if (bodyParts.length === 0) {
    trigger = `curl -X POST "${url}"`
  } else {
    trigger = (
      `curl -X POST "${url}" \\\n` +
      `  -H "Content-Type: application/json" \\\n` +
      `  -d '{${bodyParts.join(', ')}}'`
    )
  }

  const statusUrl = `${url}/<task_id>`
  return (
    `# 1) Trigger task\n` +
    trigger + `\n` +
    `#    → returns { "task_id": "...", "status": "waiting", ... }\n\n` +
    `# 2) Poll status\n` +
    `curl "${statusUrl}"\n` +
    `#    → returns { "status": "running"|"success"|"error", "exit_code": 0, "log_tail": "...", ... }`
  )
}

async function copyToClipboard(text: string) {
  await navigator.clipboard.writeText(text)
  copied.value = true
  setTimeout(() => { copied.value = false }, 2000)
}
</script>

<template>
  <Teleport to="body">
    <div v-if="open && template" class="fixed inset-0 z-50 flex items-center justify-center p-4"
      @click.self="$emit('close')">
      <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" />

      <div class="relative bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col">
        <!-- Header -->
        <div class="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <div class="flex items-center gap-2">
            <Key class="w-4 h-4 text-brand-600" />
            <div>
              <h2 class="font-semibold text-gray-900">Execute Tokens</h2>
              <p class="text-xs text-gray-400">{{ template.name }}</p>
            </div>
          </div>
          <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600">
            <X class="w-5 h-5" />
          </button>
        </div>

        <!-- Body -->
        <div class="overflow-y-auto flex-1 px-6 py-5 space-y-5">

          <!-- New token revealed -->
          <div v-if="newToken" class="bg-green-50 border border-green-200 rounded-xl p-4 space-y-3">
            <p class="text-sm font-semibold text-green-800">
              ✅ Token <strong>{{ newToken.name }}</strong> created — copy it now, it won't be shown again.
            </p>

            <div>
              <label class="block text-xs font-medium text-gray-600 mb-1">Execute URL</label>
              <div class="flex items-center gap-2">
                <code class="flex-1 text-xs bg-white border border-green-200 rounded-lg px-3 py-2 break-all">
                  {{ executeUrl(newToken.token) }}
                </code>
                <button @click="copyToClipboard(executeUrl(newToken.token))"
                  class="shrink-0 p-2 text-green-600 hover:text-green-800 transition-colors" title="Copy URL">
                  <component :is="copied ? Check : Copy" class="w-4 h-4" />
                </button>
              </div>
            </div>

            <div>
              <label class="block text-xs font-medium text-gray-600 mb-1">Raw token (for custom use)</label>
              <div class="flex items-center gap-2">
                <code class="flex-1 text-xs bg-white border border-green-200 rounded-lg px-3 py-2 break-all font-mono">
                  {{ newToken.token }}
                </code>
                <button @click="copyToClipboard(newToken.token)"
                  class="shrink-0 p-2 text-green-600 hover:text-green-800 transition-colors" title="Copy token">
                  <component :is="copied ? Check : Copy" class="w-4 h-4" />
                </button>
              </div>
            </div>

            <div>
              <label class="block text-xs font-medium text-gray-600 mb-1">curl example</label>
              <pre class="text-xs bg-gray-900 text-gray-200 rounded-lg px-3 py-2 overflow-x-auto whitespace-pre-wrap">{{ curlExample(newToken.token) }}</pre>
            </div>
          </div>

          <!-- Info box -->
          <div class="text-xs text-blue-700 bg-blue-50 border border-blue-200 rounded-lg px-4 py-3 space-y-1.5">
            <p>
              <strong>How it works:</strong> Each token allows triggering this template without user authentication.
              The token is the credential — treat it like a password.
            </p>
            <p v-if="isDeploy" class="text-orange-700">
              <strong>🚀 Deploy template:</strong>
              You <em>must</em> pass <code class="bg-orange-100 px-1 rounded">build_task_id</code> in the request body
              — the ID of the successful build task to deploy.
              Optionally pin a default build ID when creating the token (can be overridden per request).
            </p>
            <p v-else>
              Optionally pass <code class="bg-blue-100 px-1 rounded">survey_answers</code> in the request body to
              override the token's defaults.
            </p>
          </div>

          <!-- Token list -->
          <div v-if="loading" class="text-sm text-gray-400 italic text-center py-4">Loading…</div>
          <div v-else-if="tokens.length === 0 && !showForm" class="text-sm text-gray-400 text-center py-4">
            No tokens yet.
          </div>
          <div v-else-if="tokens.length > 0" class="space-y-2">
            <h3 class="text-xs font-semibold text-gray-500 uppercase tracking-wide">Active tokens</h3>
            <div v-for="t in tokens" :key="t.id"
              class="flex items-center justify-between px-4 py-3 bg-gray-50 rounded-xl border border-gray-200">
              <div class="min-w-0">
                <p class="text-sm font-medium text-gray-900">{{ t.name }}</p>
                <div class="flex gap-3 mt-0.5">
                  <span class="text-xs text-gray-400">
                    Created {{ new Date(t.created_at).toLocaleDateString() }}
                  </span>
                  <span v-if="t.expires_at" class="text-xs text-orange-500">
                    Expires {{ new Date(t.expires_at).toLocaleDateString() }}
                  </span>
                  <span v-else class="text-xs text-gray-400">No expiry</span>
                  <span v-if="Object.keys(JSON.parse(t.survey_defaults || '{}')).length"
                    class="text-xs text-yellow-600">
                    {{ Object.keys(JSON.parse(t.survey_defaults || '{}')).length }} survey default(s)
                  </span>
                </div>
              </div>
              <button @click="revokeToken(t.id)"
                class="ml-4 shrink-0 text-gray-300 hover:text-red-500 transition-colors" title="Revoke">
                <Trash2 class="w-4 h-4" />
              </button>
            </div>
          </div>

          <!-- Create form -->
          <div v-if="showForm" class="border border-brand-200 rounded-xl p-4 space-y-4 bg-brand-50">
            <h3 class="text-sm font-semibold text-gray-700">New execute token</h3>
            <form @submit.prevent="createToken" class="space-y-3">
              <div>
                <label class="block text-xs font-medium text-gray-600 mb-1">Name / description *</label>
                <input v-model="form.name" required placeholder="CI pipeline, Monitoring, …"
                  class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
              </div>

              <div>
                <label class="block text-xs font-medium text-gray-600 mb-1">
                  Expiry date <span class="text-gray-400">(optional — leave blank for no expiry)</span>
                </label>
                <input v-model="form.expires_at" type="datetime-local"
                  class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
              </div>

              <!-- Deploy: default build_task_id -->
              <div v-if="isDeploy" class="space-y-1">
                <label class="block text-xs font-medium text-gray-600">
                  Default build task ID
                  <span class="text-gray-400 font-normal">— optional; caller can override per request</span>
                </label>
                <input v-model="form.default_build_id"
                  placeholder="Leave blank — caller must supply build_task_id each time"
                  class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-brand-500" />
                <p class="text-xs text-gray-400">
                  Paste the task ID of the build you want to pin as the default version for this token.
                  You can find it in the task list or task detail page.
                </p>
              </div>

              <!-- Survey variable defaults (only if template has survey vars) -->
              <div v-if="hasSurvey" class="space-y-2">
                <label class="block text-xs font-medium text-gray-600">
                  Survey variable defaults
                  <span class="text-gray-400 font-normal">
                    — pre-filled values; the caller can override them per request
                  </span>
                </label>
                <div v-for="sv in template.survey_vars" :key="sv.name" class="flex items-center gap-3">
                  <span class="text-xs text-gray-500 w-32 shrink-0 truncate" :title="sv.title || sv.name">
                    {{ sv.title || sv.name }}
                    <span v-if="sv.required" class="text-red-400">*</span>
                  </span>
                  <select v-if="sv.type === 'enum'" v-model="form.survey_defaults[sv.name]"
                    class="flex-1 border border-gray-300 rounded-lg px-2 py-1.5 text-sm">
                    <option value="">— caller must provide —</option>
                    <option v-for="opt in parseEnumOptions(sv.values)" :key="opt.value" :value="opt.value">
                      {{ opt.label }}
                    </option>
                  </select>
                  <input v-else v-model="form.survey_defaults[sv.name]"
                    :type="sv.type === 'secret' ? 'password' : sv.type === 'int' ? 'number' : 'text'"
                    :placeholder="sv.default || '— caller must provide —'"
                    class="flex-1 border border-gray-300 rounded-lg px-2 py-1.5 text-sm" />
                </div>
                <p class="text-xs text-gray-400">
                  Empty fields must be supplied by the caller in the request body.
                </p>
              </div>

              <div class="flex gap-3">
                <button type="submit" :disabled="saving"
                  class="bg-brand-600 hover:bg-brand-700 text-white text-sm px-4 py-2 rounded-lg disabled:opacity-60">
                  {{ saving ? 'Generating…' : 'Generate token' }}
                </button>
                <button type="button" @click="showForm = false" class="text-sm text-gray-500">Cancel</button>
              </div>
            </form>
          </div>
        </div>

        <!-- Footer -->
        <div class="flex justify-between items-center px-6 py-4 border-t border-gray-100">
          <button v-if="!showForm" @click="showForm = true; newToken = null"
            class="flex items-center gap-2 text-sm bg-brand-600 hover:bg-brand-700 text-white px-4 py-2 rounded-lg">
            <Plus class="w-4 h-4" /> Generate token
          </button>
          <span v-else />
          <button @click="$emit('close')" class="text-sm text-gray-500 hover:text-gray-700">Close</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
