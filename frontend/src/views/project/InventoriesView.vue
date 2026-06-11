<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useProjectsStore } from '@/stores/projects'
import { projectsApi } from '@/api/projects'
import { Server, Plus, Pencil, Trash2 } from 'lucide-vue-next'

const route = useRoute()
const store = useProjectsStore()
const projectId = computed(() => route.params.projectId as string)

const inventories = ref<any[]>([])
const keys = ref<any[]>([])
const showForm = ref(false)
const editId = ref<string | null>(null)
const saving = ref(false)

const emptyForm = () => ({
  name: '',
  type: 'static',
  inventory: '',
  inventory_file: '',
  ssh_key_id: '',
  become_key_id: '',
})
const form = ref(emptyForm())

const sshKeys = computed(() => keys.value.filter(k => ['ssh', 'ssh_login', 'ssh_become', 'login_password'].includes(k.type)))
const loginKeys = computed(() => keys.value.filter(k => ['ssh', 'ssh_login', 'ssh_become', 'login_password'].includes(k.type)))

onMounted(async () => {
  const [invRes, keysRes] = await Promise.all([
    projectsApi.listInventories(projectId.value),
    projectsApi.listKeys(projectId.value),
  ])
  inventories.value = invRes.data
  keys.value = keysRes.data
})

function startEdit(inv: any) {
  editId.value = inv.id
  form.value = {
    name: inv.name,
    type: inv.type,
    inventory: inv.inventory || '',
    inventory_file: inv.inventory_file || '',
    ssh_key_id: inv.ssh_key_id || '',
    become_key_id: inv.become_key_id || '',
  }
  showForm.value = true
}

function cancel() {
  showForm.value = false
  editId.value = null
  form.value = emptyForm()
}

async function save() {
  saving.value = true
  try {
    const payload = {
      ...form.value,
      ssh_key_id: form.value.ssh_key_id || null,
      become_key_id: form.value.become_key_id || null,
    }
    if (editId.value) {
      const { data } = await projectsApi.updateInventory(projectId.value, editId.value, payload)
      const idx = inventories.value.findIndex(i => i.id === editId.value)
      if (idx !== -1) inventories.value[idx] = data
    } else {
      const { data } = await projectsApi.createInventory(projectId.value, payload)
      inventories.value.push(data)
    }
    cancel()
  } finally {
    saving.value = false
  }
}

async function deleteInv(id: string) {
  if (!confirm('Delete this inventory?')) return
  await projectsApi.deleteInventory(projectId.value, id)
  inventories.value = inventories.value.filter(i => i.id !== id)
}

const typeLabels: Record<string, string> = {
  static: 'Static (INI)',
  'static-yaml': 'Static (YAML)',
  file: 'File in repository',
  none: 'None',
}
</script>

<template>
  <div>
    <div class="flex justify-between items-center mb-4">
      <h2 class="text-lg font-medium text-gray-900">Inventories</h2>
      <button v-if="store.canManage" @click="showForm = true; editId = null; form = emptyForm()"
        class="flex items-center gap-2 bg-brand-600 hover:bg-brand-700 text-white text-sm px-3 py-1.5 rounded-lg">
        <Plus class="w-4 h-4" /> New inventory
      </button>
    </div>

    <!-- Form -->
    <div v-if="showForm" class="mb-4 bg-white rounded-xl border border-brand-200 p-5">
      <h3 class="font-medium text-gray-900 mb-4">{{ editId ? 'Edit inventory' : 'New inventory' }}</h3>
      <form @submit.prevent="save" class="space-y-4">
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">Name *</label>
            <input v-model="form.name" required class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">Type *</label>
            <select v-model="form.type" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
              <option value="static">Static — INI format</option>
              <option value="static-yaml">Static — YAML format</option>
              <option value="file">File in repository</option>
              <option value="none">None</option>
            </select>
          </div>
        </div>

        <!-- Static inventory content -->
        <div v-if="form.type === 'static' || form.type === 'static-yaml'">
          <label class="block text-xs font-medium text-gray-600 mb-1">
            Inventory content <span class="text-gray-400">({{ form.type === 'static-yaml' ? 'YAML' : 'INI' }} format)</span>
          </label>
          <textarea v-model="form.inventory" rows="8"
            class="w-full border border-gray-300 rounded-lg px-3 py-2 text-xs font-mono focus:outline-none focus:ring-2 focus:ring-brand-500"
            :placeholder="form.type === 'static-yaml'
              ? 'all:\n  hosts:\n    web1:\n      ansible_host: 10.0.0.1'
              : '[webservers]\nweb1 ansible_host=10.0.0.1\n\n[databases]\ndb1 ansible_host=10.0.0.2'"
          />
        </div>

        <!-- File path -->
        <div v-if="form.type === 'file'">
          <label class="block text-xs font-medium text-gray-600 mb-1">Inventory file path (relative to repo root)</label>
          <input v-model="form.inventory_file" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono" placeholder="inventories/production.yml" />
        </div>

        <!-- Keys -->
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">Login key (SSH key or username/password)</label>
            <select v-model="form.ssh_key_id" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
              <option value="">— None —</option>
              <option v-for="k in sshKeys" :key="k.id" :value="k.id">{{ k.name }} ({{ k.type }})</option>
            </select>
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">Become key (privilege escalation)</label>
            <select v-model="form.become_key_id" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
              <option value="">— None —</option>
              <option v-for="k in loginKeys" :key="k.id" :value="k.id">{{ k.name }} ({{ k.type }})</option>
            </select>
          </div>
        </div>

        <div class="flex gap-3">
          <button type="submit" :disabled="saving"
            class="bg-brand-600 hover:bg-brand-700 text-white text-sm px-4 py-2 rounded-lg disabled:opacity-60">
            {{ saving ? 'Saving…' : editId ? 'Save changes' : 'Add inventory' }}
          </button>
          <button type="button" @click="cancel" class="text-sm text-gray-500 hover:text-gray-700">Cancel</button>
        </div>
      </form>
    </div>

    <!-- List -->
    <div class="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
      <div v-if="inventories.length === 0" class="p-6 text-center text-gray-400 text-sm">No inventories yet.</div>
      <div v-for="inv in inventories" :key="inv.id" class="flex items-center justify-between px-5 py-4">
        <div class="flex items-center gap-3 min-w-0">
          <Server class="w-4 h-4 text-gray-400 shrink-0" />
          <div class="min-w-0">
            <p class="text-sm font-medium text-gray-900">{{ inv.name }}</p>
            <div class="flex flex-wrap gap-2 mt-0.5">
              <span class="text-xs bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">{{ typeLabels[inv.type] || inv.type }}</span>
              <span v-if="inv.ssh_key_id" class="text-xs text-blue-500">🔑 SSH key</span>
              <span v-if="inv.become_key_id" class="text-xs text-purple-500">⬆ become key</span>
              <span v-if="inv.inventory_file" class="text-xs text-gray-400 font-mono">{{ inv.inventory_file }}</span>
            </div>
          </div>
        </div>
        <div class="flex items-center gap-2 ml-4 shrink-0">
          <button v-if="store.canManage" @click="startEdit(inv)" class="p-1.5 text-gray-400 hover:text-brand-600 transition-colors"><Pencil class="w-4 h-4" /></button>
          <button v-if="store.canManage" @click="deleteInv(inv.id)" class="p-1.5 text-gray-300 hover:text-red-500 transition-colors"><Trash2 class="w-4 h-4" /></button>
        </div>
      </div>
    </div>
  </div>
</template>
