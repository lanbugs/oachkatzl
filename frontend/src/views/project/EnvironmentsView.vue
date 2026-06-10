<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useProjectsStore } from '@/stores/projects'
import { projectsApi } from '@/api/projects'
import { Variable, Plus, Pencil, Trash2, Eye, EyeOff } from 'lucide-vue-next'

const route = useRoute()
const store = useProjectsStore()
const projectId = computed(() => route.params.projectId as string)

const environments = ref<any[]>([])
const showForm = ref(false)
const editId = ref<string | null>(null)
const saving = ref(false)
const jsonError = ref('')
const envError = ref('')

const emptyForm = () => ({ name: '', json: '{}', env: '{}' })
const form = ref(emptyForm())

onMounted(async () => {
  const { data } = await projectsApi.listEnvironments(projectId.value)
  environments.value = data
})

function validateJSON(str: string): boolean {
  try { JSON.parse(str); return true } catch { return false }
}

function startEdit(e: any) {
  editId.value = e.id
  form.value = { name: e.name, json: formatJSON(e.json), env: formatJSON(e.env) }
  showForm.value = true
  jsonError.value = ''
  envError.value = ''
}

function cancel() {
  showForm.value = false
  editId.value = null
  form.value = emptyForm()
  jsonError.value = ''
  envError.value = ''
}

function formatJSON(raw: string): string {
  try { return JSON.stringify(JSON.parse(raw || '{}'), null, 2) } catch { return raw || '{}' }
}

async function save() {
  jsonError.value = ''
  envError.value = ''
  if (!validateJSON(form.value.json)) { jsonError.value = 'Invalid JSON'; return }
  if (!validateJSON(form.value.env)) { envError.value = 'Invalid JSON'; return }

  saving.value = true
  try {
    const payload = {
      name: form.value.name,
      json: form.value.json,
      env: form.value.env,
    }
    if (editId.value) {
      const { data } = await projectsApi.updateEnvironment(projectId.value, editId.value, payload)
      const idx = environments.value.findIndex(e => e.id === editId.value)
      if (idx !== -1) environments.value[idx] = data
    } else {
      const { data } = await projectsApi.createEnvironment(projectId.value, payload)
      environments.value.push(data)
    }
    cancel()
  } finally {
    saving.value = false
  }
}

async function deleteEnv(id: string) {
  if (!confirm('Delete this environment?')) return
  await projectsApi.deleteEnvironment(projectId.value, id)
  environments.value = environments.value.filter(e => e.id !== id)
}

function countKeys(json: string): number {
  try { return Object.keys(JSON.parse(json || '{}')).length } catch { return 0 }
}
</script>

<template>
  <div>
    <div class="flex justify-between items-center mb-4">
      <div>
        <h2 class="text-lg font-medium text-gray-900">Environments / Variables</h2>
        <p class="text-xs text-gray-400 mt-0.5">Extra variables and environment variables passed to every task run.</p>
      </div>
      <button v-if="store.canManage" @click="showForm = true; editId = null; form = emptyForm()"
        class="flex items-center gap-2 bg-brand-600 hover:bg-brand-700 text-white text-sm px-3 py-1.5 rounded-lg">
        <Plus class="w-4 h-4" /> New environment
      </button>
    </div>

    <!-- Form -->
    <div v-if="showForm" class="mb-4 bg-white rounded-xl border border-brand-200 p-5">
      <h3 class="font-medium text-gray-900 mb-4">{{ editId ? 'Edit environment' : 'New environment' }}</h3>
      <form @submit.prevent="save" class="space-y-4">
        <div>
          <label class="block text-xs font-medium text-gray-600 mb-1">Name *</label>
          <input v-model="form.name" required class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="Production variables" />
        </div>

        <div>
          <label class="block text-xs font-medium text-gray-600 mb-1">
            Extra variables — <code class="text-gray-400">--extra-vars</code> for Ansible, injected as env for bash/python
          </label>
          <textarea v-model="form.json" rows="6"
            class="w-full border border-gray-300 rounded-lg px-3 py-2 text-xs font-mono focus:outline-none focus:ring-2 focus:ring-brand-500"
            :class="{ 'border-red-400': jsonError }"
            placeholder='{\n  "deploy_env": "production",\n  "app_version": "1.0.0"\n}' />
          <p v-if="jsonError" class="text-xs text-red-500 mt-1">{{ jsonError }}</p>
          <p class="text-xs text-gray-400 mt-1">JSON object — keys become Ansible extra-vars or environment variables.</p>
        </div>

        <div>
          <label class="block text-xs font-medium text-gray-600 mb-1">
            Process environment variables — set in the worker process before executing
          </label>
          <textarea v-model="form.env" rows="4"
            class="w-full border border-gray-300 rounded-lg px-3 py-2 text-xs font-mono focus:outline-none focus:ring-2 focus:ring-brand-500"
            :class="{ 'border-red-400': envError }"
            placeholder='{\n  "AWS_REGION": "eu-west-1",\n  "KUBECONFIG": "/etc/kube/config"\n}' />
          <p v-if="envError" class="text-xs text-red-500 mt-1">{{ envError }}</p>
          <p class="text-xs text-gray-400 mt-1">JSON object — keys are exported as shell environment variables (e.g. <code>AWS_REGION</code>).</p>
        </div>

        <div class="flex gap-3">
          <button type="submit" :disabled="saving"
            class="bg-brand-600 hover:bg-brand-700 text-white text-sm px-4 py-2 rounded-lg disabled:opacity-60">
            {{ saving ? 'Saving…' : editId ? 'Save changes' : 'Add environment' }}
          </button>
          <button type="button" @click="cancel" class="text-sm text-gray-500 hover:text-gray-700">Cancel</button>
        </div>
      </form>
    </div>

    <!-- List -->
    <div class="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
      <div v-if="environments.length === 0" class="p-6 text-center text-gray-400 text-sm">No environments yet.</div>
      <div v-for="e in environments" :key="e.id" class="flex items-center justify-between px-5 py-4">
        <div class="flex items-center gap-3 min-w-0">
          <Variable class="w-4 h-4 text-gray-400 shrink-0" />
          <div class="min-w-0">
            <p class="text-sm font-medium text-gray-900">{{ e.name }}</p>
            <div class="flex gap-3 mt-0.5">
              <span class="text-xs text-gray-400">
                <span class="font-medium text-gray-600">{{ countKeys(e.json) }}</span> extra vars
              </span>
              <span class="text-xs text-gray-400">
                <span class="font-medium text-gray-600">{{ countKeys(e.env) }}</span> env vars
              </span>
            </div>
          </div>
        </div>
        <div class="flex items-center gap-2 ml-4 shrink-0">
          <button v-if="store.canManage" @click="startEdit(e)" class="p-1.5 text-gray-400 hover:text-brand-600 transition-colors"><Pencil class="w-4 h-4" /></button>
          <button v-if="store.canManage" @click="deleteEnv(e.id)" class="p-1.5 text-gray-300 hover:text-red-500 transition-colors"><Trash2 class="w-4 h-4" /></button>
        </div>
      </div>
    </div>
  </div>
</template>
