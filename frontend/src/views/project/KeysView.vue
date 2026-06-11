<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { projectsApi } from '@/api/projects'
import { useProjectsStore } from '@/stores/projects'
import { Key, Plus, Pencil, Trash2, X } from 'lucide-vue-next'
import CredentialsView from './CredentialsView.vue'

const route = useRoute()
const store = useProjectsStore()
const projectId = computed(() => route.params.projectId as string)

const keys   = ref<any[]>([])
const saving = ref(false)
const showForm = ref(false)
const editId   = ref<string | null>(null)   // null = create mode

const emptyForm = () => ({
  name: '', type: 'ssh',
  private_key: '', passphrase: '',
  login: '', password: '',
  vault_password: '',
  become_password: '',
})
const form = ref(emptyForm())

onMounted(async () => {
  const { data } = await projectsApi.listKeys(projectId.value)
  keys.value = data
})

function openCreate() {
  editId.value  = null
  form.value    = emptyForm()
  showForm.value = true
}

function openEdit(k: any) {
  editId.value  = k.id
  // Pre-fill name and type; secret fields are left blank intentionally —
  // leave them empty to keep the existing secret, or fill them to replace it.
  form.value    = { ...emptyForm(), name: k.name, type: k.type }
  showForm.value = true
}

function cancel() {
  showForm.value = false
  editId.value   = null
  form.value     = emptyForm()
}

async function save() {
  saving.value = true
  try {
    if (editId.value) {
      const { data } = await projectsApi.updateKey(projectId.value, editId.value, form.value)
      const idx = keys.value.findIndex(k => k.id === editId.value)
      if (idx !== -1) keys.value[idx] = data
    } else {
      const { data } = await projectsApi.createKey(projectId.value, form.value)
      keys.value.push(data)
    }
    cancel()
  } finally {
    saving.value = false
  }
}

async function deleteKey(id: string) {
  if (!confirm('Delete this key?')) return
  await projectsApi.deleteKey(projectId.value, id)
  keys.value = keys.value.filter(k => k.id !== id)
}

const TYPE_LABELS: Record<string, string> = {
  none:          'None',
  ssh:           'SSH Key',
  ssh_login:     'SSH Key + Username',
  ssh_become:    'SSH Key + Become password',
  login_password:'Login / Password',
  vault:         'Ansible Vault',
}
</script>

<template>
  <div class="space-y-10">
    <div>
    <div class="flex justify-between items-center mb-4">
      <h2 class="text-lg font-medium text-gray-900">Access Keys</h2>
      <button v-if="store.canManage" @click="openCreate"
        class="flex items-center gap-2 bg-brand-600 hover:bg-brand-700 text-white text-sm px-3 py-1.5 rounded-lg">
        <Plus class="w-4 h-4" /> New key
      </button>
    </div>

    <!-- Create / Edit form -->
    <div v-if="showForm" class="mb-4 bg-white rounded-xl border border-brand-200 p-5">
      <div class="flex items-center justify-between mb-4">
        <h3 class="font-medium text-gray-900">{{ editId ? 'Edit key' : 'New key' }}</h3>
        <button @click="cancel" class="text-gray-400 hover:text-gray-600"><X class="w-4 h-4" /></button>
      </div>

      <form @submit.prevent="save" class="space-y-3">
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">Name *</label>
            <input v-model="form.name" required
              class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">Type *</label>
            <select v-model="form.type"
              class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500">
              <option value="none">None</option>
              <option value="ssh">SSH Key</option>
              <option value="ssh_login">SSH Key + Username (ansible_user)</option>
              <option value="ssh_become">SSH Key + Become password (ansible_become_password)</option>
              <option value="login_password">Login / Password</option>
              <option value="vault">Ansible Vault</option>
            </select>
          </div>
        </div>

        <!-- SSH / SSH+Login / SSH+Become: shared private key + passphrase fields -->
        <div v-if="form.type === 'ssh' || form.type === 'ssh_login' || form.type === 'ssh_become'" class="space-y-2">
          <p v-if="editId" class="text-xs text-amber-600 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
            Leave the fields below blank to keep the existing secret. Fill them to replace it.
          </p>
          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">
              Private key{{ editId ? ' (optional — leave blank to keep current)' : '' }}
            </label>
            <textarea v-model="form.private_key" rows="5"
              class="w-full border border-gray-300 rounded-lg px-3 py-2 text-xs font-mono focus:outline-none focus:ring-2 focus:ring-brand-500"
              :placeholder="editId ? '— unchanged —' : '-----BEGIN OPENSSH PRIVATE KEY-----\n…'" />
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">Passphrase (optional)</label>
            <input v-model="form.passphrase" type="password"
              :placeholder="editId ? '— unchanged —' : ''"
              class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
          </div>
          <!-- SSH + Username: extra login field -->
          <div v-if="form.type === 'ssh_login'">
            <label class="block text-xs font-medium text-gray-600 mb-1">
              Username <span class="font-normal text-gray-400">(injected as <code>ansible_user</code>)</span>
            </label>
            <input v-model="form.login"
              :placeholder="editId ? '— unchanged —' : 'e.g. deploy'"
              class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
          </div>
          <!-- SSH + Become: username + become_password fields -->
          <template v-if="form.type === 'ssh_become'">
            <div>
              <label class="block text-xs font-medium text-gray-600 mb-1">
                Username <span class="font-normal text-gray-400">(injected as <code>ansible_user</code>)</span>
              </label>
              <input v-model="form.login"
                :placeholder="editId ? '— unchanged —' : 'e.g. deploy'"
                class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
            </div>
            <div>
              <label class="block text-xs font-medium text-gray-600 mb-1">
                Become password <span class="font-normal text-gray-400">(injected as <code>ansible_become_password</code>)</span>
              </label>
              <input v-model="form.become_password" type="password"
                :placeholder="editId ? '— unchanged —' : ''"
                class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
            </div>
          </template>
        </div>

        <!-- Login / Password -->
        <div v-if="form.type === 'login_password'" class="space-y-2">
          <p v-if="editId" class="text-xs text-amber-600 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
            Leave the fields below blank to keep the existing credentials.
          </p>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-xs font-medium text-gray-600 mb-1">Login</label>
              <input v-model="form.login"
                :placeholder="editId ? '— unchanged —' : ''"
                class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
            </div>
            <div>
              <label class="block text-xs font-medium text-gray-600 mb-1">Password</label>
              <input v-model="form.password" type="password"
                :placeholder="editId ? '— unchanged —' : ''"
                class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
            </div>
          </div>
        </div>

        <!-- Vault -->
        <div v-if="form.type === 'vault'">
          <p v-if="editId" class="text-xs text-amber-600 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 mb-2">
            Leave blank to keep the existing vault password.
          </p>
          <label class="block text-xs font-medium text-gray-600 mb-1">Vault password</label>
          <input v-model="form.vault_password" type="password"
            :placeholder="editId ? '— unchanged —' : ''"
            class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
        </div>

        <div class="flex gap-3 pt-1">
          <button type="submit" :disabled="saving"
            class="bg-brand-600 hover:bg-brand-700 text-white text-sm px-4 py-2 rounded-lg disabled:opacity-60">
            {{ saving ? 'Saving…' : editId ? 'Save changes' : 'Create key' }}
          </button>
          <button type="button" @click="cancel" class="text-sm text-gray-500 hover:text-gray-700">Cancel</button>
        </div>
      </form>
    </div>

    <!-- Key list -->
    <div class="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
      <div v-if="keys.length === 0" class="p-6 text-center text-gray-400 text-sm">No keys yet.</div>
      <div v-for="k in keys" :key="k.id" class="flex items-center justify-between px-5 py-4">
        <div class="flex items-center gap-3 min-w-0">
          <Key class="w-4 h-4 text-gray-400 shrink-0" />
          <div class="min-w-0">
            <p class="text-sm font-medium text-gray-900">{{ k.name }}</p>
            <p class="text-xs text-gray-400">
              {{ TYPE_LABELS[k.type] || k.type }}
              <span class="mx-1">·</span>
              <span :class="k.has_secret ? 'text-green-600' : 'text-gray-300'">
                {{ k.has_secret ? '🔐 secret stored' : 'no secret' }}
              </span>
            </p>
          </div>
        </div>
        <div class="flex items-center gap-2 ml-4 shrink-0">
          <button v-if="store.canManage" @click="openEdit(k)"
            class="p-1.5 text-gray-400 hover:text-brand-600 transition-colors" title="Edit">
            <Pencil class="w-4 h-4" />
          </button>
          <button v-if="store.canManage" @click="deleteKey(k.id)"
            class="p-1.5 text-gray-300 hover:text-red-500 transition-colors" title="Delete">
            <Trash2 class="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
    </div>

    <!-- Divider -->
    <div class="border-t border-gray-200 pt-2">
      <CredentialsView />
    </div>
  </div>
</template>
