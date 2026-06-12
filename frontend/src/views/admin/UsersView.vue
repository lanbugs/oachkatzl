<script setup lang="ts">
import { onMounted, ref } from 'vue'
import api from '@/api/client'
import { UserCircle2, Plus, Shield, Pencil, X } from 'lucide-vue-next'

const users = ref<any[]>([])
const showNew = ref(false)
const editTarget = ref<any>(null)
const saving = ref(false)

const newForm = ref({ username: '', email: '', password: '', name: '', is_admin: false })
const editForm = ref({ email: '', name: '', password: '', is_admin: false, active: true })
const newError = ref('')
const editError = ref('')

onMounted(async () => {
  const { data } = await api.get('/users')
  users.value = data
})

async function createUser() {
  newError.value = ''
  saving.value = true
  try {
    const { data } = await api.post('/users', newForm.value)
    users.value.push(data)
    showNew.value = false
    newForm.value = { username: '', email: '', password: '', name: '', is_admin: false }
  } catch (e: any) {
    newError.value = e.response?.data?.detail?.[0]?.message
      ?? e.response?.data?.message
      ?? 'Failed to create user'
  } finally {
    saving.value = false
  }
}

function startEdit(u: any) {
  editTarget.value = u
  editForm.value = { email: u.email, name: u.name, password: '', is_admin: u.is_admin, active: u.active }
}

async function saveEdit() {
  editError.value = ''
  saving.value = true
  try {
    const payload: any = { email: editForm.value.email, name: editForm.value.name, is_admin: editForm.value.is_admin, active: editForm.value.active }
    if (editForm.value.password) payload.password = editForm.value.password
    const { data } = await api.put(`/users/${editTarget.value.id}`, payload)
    const idx = users.value.findIndex(u => u.id === editTarget.value.id)
    if (idx !== -1) users.value[idx] = data
    editTarget.value = null
  } catch (e: any) {
    editError.value = e.response?.data?.detail?.[0]?.message
      ?? e.response?.data?.message
      ?? 'Failed to save changes'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div>
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-2xl font-semibold text-gray-900">Users</h1>
      <button @click="showNew = true; editTarget = null"
        class="flex items-center gap-2 bg-brand-600 hover:bg-brand-700 text-white text-sm px-3 py-1.5 rounded-lg">
        <Plus class="w-4 h-4" /> New user
      </button>
    </div>

    <!-- New user form -->
    <div v-if="showNew" class="mb-6 bg-white rounded-xl border border-brand-200 p-5">
      <h3 class="font-medium text-gray-900 mb-4">New user</h3>
      <form @submit.prevent="createUser" class="grid grid-cols-2 gap-3">
        <div>
          <label class="block text-xs font-medium text-gray-600 mb-1">Username *</label>
          <input v-model="newForm.username" required class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
        </div>
        <div>
          <label class="block text-xs font-medium text-gray-600 mb-1">Email *</label>
          <input v-model="newForm.email" type="email" required class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
        </div>
        <div>
          <label class="block text-xs font-medium text-gray-600 mb-1">Name</label>
          <input v-model="newForm.name" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
        </div>
        <div>
          <label class="block text-xs font-medium text-gray-600 mb-1">Password *</label>
          <input v-model="newForm.password" type="password" required minlength="8"
            class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          <p class="text-xs text-gray-400 mt-1">Minimum 8 characters.</p>
        </div>
        <div class="col-span-2 flex items-center gap-2">
          <input v-model="newForm.is_admin" type="checkbox" id="is_admin_new" class="rounded" />
          <label for="is_admin_new" class="text-sm text-gray-700">Global admin</label>
        </div>
        <div class="col-span-2 flex items-center gap-3">
          <button type="submit" :disabled="saving" class="bg-brand-600 hover:bg-brand-700 text-white text-sm px-4 py-2 rounded-lg disabled:opacity-60">
            {{ saving ? 'Creating…' : 'Create user' }}
          </button>
          <button type="button" @click="showNew = false; newError = ''" class="text-sm text-gray-500">Cancel</button>
          <p v-if="newError" class="text-sm text-red-600">{{ newError }}</p>
        </div>
      </form>
    </div>

    <!-- Edit user form -->
    <div v-if="editTarget" class="mb-6 bg-white rounded-xl border border-brand-200 p-5">
      <div class="flex items-center justify-between mb-4">
        <h3 class="font-medium text-gray-900">Edit user — {{ editTarget.username }}</h3>
        <button @click="editTarget = null" class="text-gray-400 hover:text-gray-600"><X class="w-4 h-4" /></button>
      </div>
      <form @submit.prevent="saveEdit" class="grid grid-cols-2 gap-3">
        <div>
          <label class="block text-xs font-medium text-gray-600 mb-1">Email</label>
          <input v-model="editForm.email" type="email" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
        </div>
        <div>
          <label class="block text-xs font-medium text-gray-600 mb-1">Name</label>
          <input v-model="editForm.name" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
        </div>
        <div class="col-span-2">
          <label class="block text-xs font-medium text-gray-600 mb-1">New password <span class="text-gray-400">(leave blank to keep current)</span></label>
          <input v-model="editForm.password" type="password" autocomplete="new-password" minlength="8"
            class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          <p v-if="editForm.password" class="text-xs text-gray-400 mt-1">Minimum 8 characters.</p>
        </div>
        <div class="col-span-2 flex flex-wrap gap-4">
          <label class="flex items-center gap-2 text-sm">
            <input v-model="editForm.is_admin" type="checkbox" class="rounded" />
            Global admin
          </label>
          <label class="flex items-center gap-2 text-sm">
            <input v-model="editForm.active" type="checkbox" class="rounded" />
            Active
          </label>
        </div>
        <div class="col-span-2 flex items-center gap-3">
          <button type="submit" :disabled="saving" class="bg-brand-600 hover:bg-brand-700 text-white text-sm px-4 py-2 rounded-lg disabled:opacity-60">
            {{ saving ? 'Saving…' : 'Save changes' }}
          </button>
          <button type="button" @click="editTarget = null; editError = ''" class="text-sm text-gray-500">Cancel</button>
          <p v-if="editError" class="text-sm text-red-600">{{ editError }}</p>
        </div>
      </form>
    </div>

    <!-- User list -->
    <div class="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
      <div v-for="u in users" :key="u.id" class="flex items-center justify-between px-5 py-4">
        <div class="flex items-center gap-3">
          <UserCircle2 class="w-8 h-8 text-gray-300" />
          <div>
            <div class="flex items-center gap-2">
              <p class="text-sm font-medium text-gray-900">{{ u.username }}</p>
              <Shield v-if="u.is_admin" class="w-3.5 h-3.5 text-brand-500" title="Admin" />
            </div>
            <p class="text-xs text-gray-400">{{ u.email }}<span v-if="u.name" class="ml-1">· {{ u.name }}</span></p>
          </div>
        </div>
        <div class="flex items-center gap-3">
          <span v-if="!u.active" class="text-xs bg-red-100 text-red-600 px-2 py-0.5 rounded-full">inactive</span>
          <span v-if="u.totp_enabled" class="text-xs bg-green-100 text-green-600 px-2 py-0.5 rounded-full">2FA</span>
          <span class="text-xs text-gray-400">{{ u.auth_provider }}</span>
          <button @click="startEdit(u)" class="p-1 text-gray-400 hover:text-brand-600 transition-colors"><Pencil class="w-4 h-4" /></button>
        </div>
      </div>
    </div>
  </div>
</template>
