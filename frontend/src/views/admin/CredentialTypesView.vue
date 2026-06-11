<script setup lang="ts">
import { onMounted, ref } from 'vue'
import api from '@/api/client'
import { ShieldCheck, Plus, Pencil, Trash2, X } from 'lucide-vue-next'

const types = ref<any[]>([])
const showForm = ref(false)
const editId = ref<string | null>(null)
const saving = ref(false)
const jsonError = ref('')

const emptyForm = () => ({
  name: '',
  description: '',
  inputs: `[
  { "id": "username", "label": "Username", "type": "string", "required": true },
  { "id": "password", "label": "Password", "type": "secret", "required": true }
]`,
  injectors: `{
  "env": {
    "MY_USER": "{{ username }}",
    "MY_PASS": "{{ password }}"
  }
}`,
})

const form = ref(emptyForm())

onMounted(async () => {
  const { data } = await api.get('/credential-types')
  types.value = data
})

function openCreate() {
  editId.value = null
  form.value = emptyForm()
  jsonError.value = ''
  showForm.value = true
}

function openEdit(ct: any) {
  editId.value = ct.id
  form.value = {
    name: ct.name,
    description: ct.description,
    inputs: JSON.stringify(JSON.parse(ct.inputs || '[]'), null, 2),
    injectors: JSON.stringify(JSON.parse(ct.injectors || '{}'), null, 2),
  }
  jsonError.value = ''
  showForm.value = true
}

function cancel() {
  showForm.value = false
  editId.value = null
}

function validateJson(): boolean {
  jsonError.value = ''
  try { JSON.parse(form.value.inputs) } catch {
    jsonError.value = 'Inputs schema is not valid JSON'
    return false
  }
  try { JSON.parse(form.value.injectors) } catch {
    jsonError.value = 'Injectors schema is not valid JSON'
    return false
  }
  return true
}

async function save() {
  if (!validateJson()) return
  saving.value = true
  try {
    const payload = {
      name: form.value.name,
      description: form.value.description,
      inputs: form.value.inputs,
      injectors: form.value.injectors,
    }
    if (editId.value) {
      const { data } = await api.put(`/credential-types/${editId.value}`, payload)
      const idx = types.value.findIndex(t => t.id === editId.value)
      if (idx !== -1) types.value[idx] = data
    } else {
      const { data } = await api.post('/credential-types', payload)
      types.value.push(data)
    }
    cancel()
  } finally {
    saving.value = false
  }
}

async function deleteType(id: string) {
  if (!confirm('Delete this credential type? All credentials using it will also be deleted.')) return
  await api.delete(`/credential-types/${id}`)
  types.value = types.value.filter(t => t.id !== id)
}

function inputCount(ct: any): number {
  try { return JSON.parse(ct.inputs || '[]').length } catch { return 0 }
}
</script>

<template>
  <div>
    <div class="flex justify-between items-center mb-6">
      <div>
        <h1 class="text-2xl font-semibold text-gray-900">Credential Types</h1>
        <p class="text-sm text-gray-500 mt-0.5">Define reusable credential schemas with custom input fields and injector rules.</p>
      </div>
      <button @click="openCreate"
        class="flex items-center gap-2 bg-brand-600 hover:bg-brand-700 text-white text-sm px-3 py-1.5 rounded-lg">
        <Plus class="w-4 h-4" /> New type
      </button>
    </div>

    <!-- Form -->
    <div v-if="showForm" class="mb-6 bg-white rounded-xl border border-brand-200 p-5">
      <div class="flex items-center justify-between mb-4">
        <h3 class="font-medium text-gray-900">{{ editId ? 'Edit credential type' : 'New credential type' }}</h3>
        <button @click="cancel" class="text-gray-400 hover:text-gray-600"><X class="w-4 h-4" /></button>
      </div>

      <form @submit.prevent="save" class="space-y-4">
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">Name *</label>
            <input v-model="form.name" required class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" placeholder="HashiCorp Vault Token" />
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">Description</label>
            <input v-model="form.description" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">
              Inputs schema <span class="font-normal text-gray-400">(JSON array)</span>
            </label>
            <p class="text-xs text-gray-400 mb-1">Define the fields shown when creating a credential of this type.</p>
            <textarea v-model="form.inputs" rows="14" spellcheck="false"
              class="w-full border border-gray-300 rounded-lg px-3 py-2 text-xs font-mono focus:outline-none focus:ring-2 focus:ring-brand-500" />
            <p class="text-xs text-gray-400 mt-1">Field types: <code class="bg-gray-100 px-1 rounded">string</code> <code class="bg-gray-100 px-1 rounded">secret</code> <code class="bg-gray-100 px-1 rounded">boolean</code></p>
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">
              Injectors schema <span class="font-normal text-gray-400">(JSON object)</span>
            </label>
            <p class="text-xs text-gray-400 mb-1">Define how field values are injected using <code v-pre class="bg-gray-100 px-1 rounded">{{ field_id }}</code> syntax.</p>
            <textarea v-model="form.injectors" rows="14" spellcheck="false"
              class="w-full border border-gray-300 rounded-lg px-3 py-2 text-xs font-mono focus:outline-none focus:ring-2 focus:ring-brand-500" />
            <p class="text-xs text-gray-400 mt-1">Sections: <code class="bg-gray-100 px-1 rounded">env</code> <code class="bg-gray-100 px-1 rounded">extra_vars</code> <code class="bg-gray-100 px-1 rounded">file</code></p>
          </div>
        </div>

        <p v-if="jsonError" class="text-sm text-red-600">{{ jsonError }}</p>

        <div class="flex gap-3">
          <button type="submit" :disabled="saving"
            class="bg-brand-600 hover:bg-brand-700 text-white text-sm px-4 py-2 rounded-lg disabled:opacity-60">
            {{ saving ? 'Saving…' : editId ? 'Save changes' : 'Create type' }}
          </button>
          <button type="button" @click="cancel" class="text-sm text-gray-500 hover:text-gray-700">Cancel</button>
        </div>
      </form>
    </div>

    <!-- List -->
    <div class="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
      <div v-if="types.length === 0" class="p-6 text-center text-gray-400 text-sm">No credential types yet.</div>
      <div v-for="ct in types" :key="ct.id" class="flex items-center justify-between px-5 py-4">
        <div class="flex items-center gap-3 min-w-0">
          <ShieldCheck class="w-4 h-4 text-brand-500 shrink-0" />
          <div class="min-w-0">
            <p class="text-sm font-medium text-gray-900">{{ ct.name }}</p>
            <p class="text-xs text-gray-400">
              {{ inputCount(ct) }} field{{ inputCount(ct) !== 1 ? 's' : '' }}
              <span v-if="ct.description" class="mx-1">·</span>
              <span v-if="ct.description">{{ ct.description }}</span>
            </p>
          </div>
        </div>
        <div class="flex items-center gap-2 ml-4 shrink-0">
          <button @click="openEdit(ct)" class="p-1.5 text-gray-400 hover:text-brand-600 transition-colors" title="Edit">
            <Pencil class="w-4 h-4" />
          </button>
          <button @click="deleteType(ct.id)" class="p-1.5 text-gray-300 hover:text-red-500 transition-colors" title="Delete">
            <Trash2 class="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
