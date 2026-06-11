<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { projectsApi } from '@/api/projects'
import { useProjectsStore } from '@/stores/projects'
import api from '@/api/client'
import { ShieldCheck, Plus, Pencil, Trash2, X } from 'lucide-vue-next'

const route = useRoute()
const store = useProjectsStore()
const projectId = computed(() => route.params.projectId as string)

const credentials = ref<any[]>([])
const credTypes   = ref<any[]>([])
const showForm    = ref(false)
const editId      = ref<string | null>(null)
const saving      = ref(false)

interface FieldDef {
  id: string
  label: string
  type: 'string' | 'secret' | 'boolean'
  required?: boolean
  default?: string
  help_text?: string
}

const form = ref({ name: '', credential_type_id: '' })
const fieldValues = ref<Record<string, string>>({})

const selectedType = computed(() =>
  credTypes.value.find(ct => ct.id === form.value.credential_type_id)
)

const inputFields = computed<FieldDef[]>(() => {
  if (!selectedType.value) return []
  try { return JSON.parse(selectedType.value.inputs || '[]') }
  catch { return [] }
})

onMounted(async () => {
  const [credsRes, typesRes] = await Promise.all([
    projectsApi.listCredentials(projectId.value),
    api.get('/credential-types'),
  ])
  credentials.value = credsRes.data
  credTypes.value   = typesRes.data
})

function openCreate() {
  editId.value = null
  form.value = { name: '', credential_type_id: credTypes.value[0]?.id ?? '' }
  fieldValues.value = {}
  showForm.value = true
}

function openEdit(c: any) {
  editId.value = c.id
  form.value = { name: c.name, credential_type_id: c.credential_type_id }
  fieldValues.value = {}   // secret values never pre-filled
  showForm.value = true
}

function cancel() {
  showForm.value = false
  editId.value = null
}

function onTypeChange() {
  fieldValues.value = {}
}

async function save() {
  saving.value = true
  try {
    const payload = {
      name: form.value.name,
      credential_type_id: form.value.credential_type_id,
      inputs: JSON.stringify(fieldValues.value),
    }
    if (editId.value) {
      const { data } = await projectsApi.updateCredential(projectId.value, editId.value, payload)
      const idx = credentials.value.findIndex(c => c.id === editId.value)
      if (idx !== -1) credentials.value[idx] = data
    } else {
      const { data } = await projectsApi.createCredential(projectId.value, payload)
      credentials.value.push(data)
    }
    cancel()
  } finally {
    saving.value = false
  }
}

async function deleteCred(id: string) {
  if (!confirm('Delete this credential?')) return
  await projectsApi.deleteCredential(projectId.value, id)
  credentials.value = credentials.value.filter(c => c.id !== id)
}
</script>

<template>
  <div>
    <div class="flex justify-between items-center mb-4">
      <h2 class="text-lg font-medium text-gray-900">Credentials</h2>
      <button v-if="store.canManage" @click="openCreate"
        class="flex items-center gap-2 bg-brand-600 hover:bg-brand-700 text-white text-sm px-3 py-1.5 rounded-lg">
        <Plus class="w-4 h-4" /> New credential
      </button>
    </div>

    <div v-if="credTypes.length === 0" class="mb-4 bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 text-sm text-amber-800">
      No credential types defined yet. An admin must create at least one type under <strong>Admin → Credential Types</strong>.
    </div>

    <!-- Form -->
    <div v-if="showForm" class="mb-4 bg-white rounded-xl border border-brand-200 p-5">
      <div class="flex items-center justify-between mb-4">
        <h3 class="font-medium text-gray-900">{{ editId ? 'Edit credential' : 'New credential' }}</h3>
        <button @click="cancel" class="text-gray-400 hover:text-gray-600"><X class="w-4 h-4" /></button>
      </div>

      <form @submit.prevent="save" class="space-y-4">
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">Name *</label>
            <input v-model="form.name" required class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" placeholder="Production Vault Token" />
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">Type *</label>
            <select v-model="form.credential_type_id" required @change="onTypeChange"
              class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500">
              <option value="">— Select type —</option>
              <option v-for="ct in credTypes" :key="ct.id" :value="ct.id">{{ ct.name }}</option>
            </select>
          </div>
        </div>

        <!-- Dynamic fields from credential type -->
        <div v-if="inputFields.length > 0" class="border border-gray-100 rounded-xl p-4 space-y-3 bg-gray-50">
          <p class="text-xs font-medium text-gray-500 uppercase tracking-wide">Credential fields</p>
          <p v-if="editId" class="text-xs text-amber-600 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
            Leave fields blank to keep existing values. Fill them to replace.
          </p>

          <div v-for="field in inputFields" :key="field.id" class="space-y-1">
            <label class="block text-xs font-medium text-gray-600">
              {{ field.label || field.id }}
              <span v-if="field.required" class="text-red-500 ml-0.5">*</span>
              <span v-if="editId" class="font-normal text-gray-400 ml-1">(optional — leave blank to keep current)</span>
            </label>

            <template v-if="field.type === 'boolean'">
              <label class="inline-flex items-center gap-2 text-sm">
                <input type="checkbox"
                  :checked="fieldValues[field.id] === 'true'"
                  @change="(e) => fieldValues[field.id] = (e.target as HTMLInputElement).checked ? 'true' : 'false'"
                  class="rounded" />
                {{ field.label || field.id }}
              </label>
            </template>
            <template v-else>
              <input
                v-model="fieldValues[field.id]"
                :type="field.type === 'secret' ? 'password' : 'text'"
                :placeholder="editId ? '— unchanged —' : (field.default || '')"
                :required="field.required && !editId"
                class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </template>
            <p v-if="field.help_text" class="text-xs text-gray-400">{{ field.help_text }}</p>
          </div>
        </div>

        <div class="flex gap-3">
          <button type="submit" :disabled="saving"
            class="bg-brand-600 hover:bg-brand-700 text-white text-sm px-4 py-2 rounded-lg disabled:opacity-60">
            {{ saving ? 'Saving…' : editId ? 'Save changes' : 'Create credential' }}
          </button>
          <button type="button" @click="cancel" class="text-sm text-gray-500 hover:text-gray-700">Cancel</button>
        </div>
      </form>
    </div>

    <!-- List -->
    <div class="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
      <div v-if="credentials.length === 0" class="p-6 text-center text-gray-400 text-sm">No credentials yet.</div>
      <div v-for="c in credentials" :key="c.id" class="flex items-center justify-between px-5 py-4">
        <div class="flex items-center gap-3 min-w-0">
          <ShieldCheck class="w-4 h-4 text-brand-500 shrink-0" />
          <div class="min-w-0">
            <p class="text-sm font-medium text-gray-900">{{ c.name }}</p>
            <p class="text-xs text-gray-400">
              {{ c.credential_type_name }}
              <span v-if="c.filled_fields?.length" class="mx-1">·</span>
              <span v-if="c.filled_fields?.length" class="text-green-600">
                {{ c.filled_fields.length }} field{{ c.filled_fields.length !== 1 ? 's' : '' }} stored
              </span>
            </p>
          </div>
        </div>
        <div class="flex items-center gap-2 ml-4 shrink-0">
          <button v-if="store.canManage" @click="openEdit(c)" class="p-1.5 text-gray-400 hover:text-brand-600 transition-colors" title="Edit">
            <Pencil class="w-4 h-4" />
          </button>
          <button v-if="store.canManage" @click="deleteCred(c.id)" class="p-1.5 text-gray-300 hover:text-red-500 transition-colors" title="Delete">
            <Trash2 class="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
