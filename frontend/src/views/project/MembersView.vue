<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useProjectsStore } from '@/stores/projects'
import { projectsApi } from '@/api/projects'
import api from '@/api/client'
import { UserCircle2, Trash2, Plus, X, GitBranch, UserRoundCog } from 'lucide-vue-next'

const route = useRoute()
const store = useProjectsStore()
const projectId = computed(() => route.params.projectId as string)

const members = ref<any[]>([])
const allUsers = ref<any[]>([])
const ldapMappings = ref<any[]>([])
const showAdd = ref(false)
const addForm = ref({ user_id: '', role: 'task_runner' })
const saving = ref(false)

const ROLES = ['owner', 'manager', 'task_runner', 'guest']

const hasLdapMappings   = computed(() => ldapMappings.value.length > 0)
const hasLdapMembers    = computed(() => members.value.some(m => m.source === 'ldap'))

// Direct LDAP user mappings
const ldapUserMappings  = ref<any[]>([])
const showAddUserMap    = ref(false)
const newUserMap        = ref({ ldap_username: '', role: 'task_runner' })
const savingUserMap     = ref(false)

// Users not already in project
const availableUsers = computed(() => {
  const memberIds = new Set(members.value.map(m => m.user_id))
  return allUsers.value.filter(u => !memberIds.has(u.id))
})

onMounted(async () => {
  const requests: Promise<any>[] = [
    projectsApi.listMembers(projectId.value),
    api.get('/users'),
  ]
  // Only managers/owners can fetch LDAP mappings
  if (store.canManage) {
    requests.push(projectsApi.listLdapMappings(projectId.value))
    requests.push(projectsApi.listLdapUserMappings(projectId.value))
  }

  const [membersRes, usersRes, ldapRes, ldapUserRes] = await Promise.all(requests)
  members.value      = membersRes.data
  allUsers.value     = usersRes.data
  ldapMappings.value     = ldapRes?.data ?? []
  ldapUserMappings.value = ldapUserRes?.data ?? []
})

async function addMember() {
  if (!addForm.value.user_id) return
  saving.value = true
  try {
    const { data } = await projectsApi.addMember(projectId.value, addForm.value)
    members.value.push(data)
    addForm.value = { user_id: '', role: 'task_runner' }
    showAdd.value = false
  } catch (e: any) {
    alert(e.response?.data?.message || 'Failed to add member')
  } finally {
    saving.value = false
  }
}

async function changeRole(m: any, role: string) {
  try {
    const { data } = await projectsApi.updateMember(projectId.value, m.id, {
      user_id: m.user_id, role,
    })
    const idx = members.value.findIndex(x => x.id === m.id)
    if (idx !== -1) members.value[idx] = data
  } catch (e: any) {
    alert(e.response?.data?.message || 'Failed to update role')
  }
}

async function remove(memberId: string) {
  if (!confirm('Remove this member?')) return
  await projectsApi.removeMember(projectId.value, memberId)
  members.value = members.value.filter(m => m.id !== memberId)
}

async function addLdapUserMapping() {
  const username = newUserMap.value.ldap_username.trim()
  if (!username) return
  savingUserMap.value = true
  try {
    const { data } = await projectsApi.createLdapUserMapping(projectId.value, {
      ldap_username: username,
      role: newUserMap.value.role,
    })
    ldapUserMappings.value.push(data)
    newUserMap.value = { ldap_username: '', role: 'task_runner' }
    showAddUserMap.value = false
  } catch (e: any) {
    alert(e.response?.data?.message || 'Failed to add mapping')
  } finally {
    savingUserMap.value = false
  }
}

async function removeLdapUserMapping(id: string) {
  if (!confirm('Remove this user mapping?')) return
  await projectsApi.deleteLdapUserMapping(projectId.value, id)
  ldapUserMappings.value = ldapUserMappings.value.filter(m => m.id !== id)
}

const roleBadge: Record<string, string> = {
  owner:       'bg-purple-100 text-purple-700',
  manager:     'bg-blue-100 text-blue-700',
  task_runner: 'bg-green-100 text-green-700',
  guest:       'bg-gray-100 text-gray-600',
}
</script>

<template>
  <div>
    <div class="flex justify-between items-center mb-4">
      <h2 class="text-lg font-medium text-gray-900">Members</h2>
      <button v-if="store.canManage" @click="showAdd = true"
        class="flex items-center gap-2 bg-brand-600 hover:bg-brand-700 text-white text-sm px-3 py-1.5 rounded-lg">
        <Plus class="w-4 h-4" /> Add member
      </button>
    </div>

    <!-- Add member form -->
    <div v-if="showAdd" class="mb-4 bg-white rounded-xl border border-brand-200 p-5">
      <div class="flex items-center justify-between mb-4">
        <h3 class="font-medium text-gray-900">Add member</h3>
        <button @click="showAdd = false" class="text-gray-400 hover:text-gray-600"><X class="w-4 h-4" /></button>
      </div>
      <form @submit.prevent="addMember" class="grid grid-cols-2 gap-3">
        <div>
          <label class="block text-xs font-medium text-gray-600 mb-1">User *</label>
          <select v-model="addForm.user_id" required class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
            <option value="">— Select user —</option>
            <option v-for="u in availableUsers" :key="u.id" :value="u.id">
              {{ u.username }}<span v-if="u.name"> ({{ u.name }})</span>
            </option>
          </select>
          <p v-if="availableUsers.length === 0" class="text-xs text-gray-400 mt-1">
            All users are already members.
          </p>
        </div>
        <div>
          <label class="block text-xs font-medium text-gray-600 mb-1">Role</label>
          <select v-model="addForm.role" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
            <option value="owner">Owner — full access</option>
            <option value="manager">Manager — manage resources, run tasks</option>
            <option value="task_runner">Task runner — run tasks, read config</option>
            <option value="guest">Guest — read only</option>
          </select>
        </div>
        <div class="col-span-2 flex gap-3">
          <button type="submit" :disabled="saving || !addForm.user_id"
            class="bg-brand-600 hover:bg-brand-700 text-white text-sm px-4 py-2 rounded-lg disabled:opacity-60">
            {{ saving ? 'Adding…' : 'Add member' }}
          </button>
          <button type="button" @click="showAdd = false" class="text-sm text-gray-500">Cancel</button>
        </div>
      </form>
    </div>

    <!-- Member list -->
    <div class="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
      <div v-if="members.length === 0" class="p-6 text-center text-gray-400 text-sm">No members.</div>
      <div v-for="m in members" :key="m.id" class="flex items-center justify-between px-5 py-4">
        <div class="flex items-center gap-3">
          <UserCircle2 class="w-8 h-8 text-gray-300" />
          <div>
            <p class="text-sm font-medium text-gray-900">{{ m.username }}</p>
            <p class="text-xs text-gray-400">{{ m.email }}</p>
          </div>
        </div>
        <div class="flex items-center gap-3">
          <!-- LDAP badge -->
          <span v-if="m.source === 'ldap'"
            class="text-xs bg-indigo-50 text-indigo-600 border border-indigo-200 px-1.5 py-0.5 rounded font-medium"
            title="Role managed by LDAP/AD — changes here may be overwritten on next login">
            LDAP
          </span>

          <!-- Managers/owners: editable role dropdown (read-only for LDAP-managed) -->
          <select v-if="store.canManage"
            :value="m.role"
            @change="changeRole(m, ($event.target as HTMLSelectElement).value)"
            class="text-xs border border-gray-200 rounded-lg px-2 py-1 focus:outline-none focus:ring-2 focus:ring-brand-500"
            :class="roleBadge[m.role]"
            :disabled="m.source === 'ldap'"
            :title="m.source === 'ldap' ? 'Role is managed by LDAP — edit the group mapping in Settings' : ''"
          >
            <option v-for="r in ROLES" :key="r" :value="r">{{ r }}</option>
          </select>
          <!-- Guests/task_runners: read-only role badge -->
          <span v-else class="text-xs font-medium px-2 py-0.5 rounded-full" :class="roleBadge[m.role]">{{ m.role }}</span>
          <button v-if="store.canManage && m.source !== 'ldap'" @click="remove(m.id)" class="text-gray-300 hover:text-red-500 transition-colors">
            <Trash2 class="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>

    <!-- LDAP Group Mappings for this project -->
    <div v-if="store.canManage && (hasLdapMappings || hasLdapMembers)" class="mt-6">
      <div class="flex items-center gap-2 mb-3">
        <GitBranch class="w-4 h-4 text-indigo-500" />
        <h3 class="text-sm font-medium text-gray-700">LDAP / AD Group Mappings</h3>
        <span class="text-xs text-gray-400">— roles assigned automatically on login</span>
      </div>

      <div v-if="hasLdapMappings" class="bg-white rounded-xl border border-indigo-100 divide-y divide-gray-100">
        <div v-for="mapping in ldapMappings" :key="mapping.id"
          class="flex items-center justify-between px-5 py-3">
          <div class="flex items-center gap-3 min-w-0">
            <!-- AD group icon -->
            <div class="w-7 h-7 rounded-lg bg-indigo-50 flex items-center justify-center flex-shrink-0">
              <GitBranch class="w-3.5 h-3.5 text-indigo-500" />
            </div>
            <p class="text-xs font-mono text-gray-600 truncate" :title="mapping.group_dn">
              {{ mapping.group_dn }}
            </p>
          </div>
          <span class="ml-4 flex-shrink-0 text-xs font-medium px-2 py-0.5 rounded-full" :class="roleBadge[mapping.role]">
            {{ mapping.role }}
          </span>
        </div>
      </div>

      <p v-else class="text-sm text-gray-400 italic">
        No group mappings configured for this project yet.
        <RouterLink to="/admin/settings" class="text-indigo-500 hover:underline ml-1">Configure in Settings →</RouterLink>
      </p>
    </div>

    <!-- Direct LDAP User Mappings -->
    <div v-if="store.canManage" class="mt-6">
      <div class="flex items-center justify-between mb-3">
        <div class="flex items-center gap-2">
          <UserRoundCog class="w-4 h-4 text-indigo-500" />
          <h3 class="text-sm font-medium text-gray-700">Direct LDAP User Mappings</h3>
          <span class="text-xs text-gray-400">— assign a specific AD user to a role on login</span>
        </div>
        <button @click="showAddUserMap = !showAddUserMap"
          class="flex items-center gap-1 text-sm text-brand-600 hover:text-brand-700">
          <Plus class="w-3.5 h-3.5" /> Add
        </button>
      </div>

      <!-- Add form -->
      <div v-if="showAddUserMap" class="mb-3 bg-white rounded-xl border border-indigo-100 p-4">
        <div class="grid grid-cols-3 gap-3">
          <div class="col-span-2">
            <label class="block text-xs font-medium text-gray-600 mb-1">LDAP username *</label>
            <input v-model="newUserMap.ldap_username" @keydown.enter.prevent="addLdapUserMapping"
              class="w-full border border-gray-300 rounded-lg px-3 py-1.5 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-brand-500"
              placeholder="jdoe" />
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">Role</label>
            <select v-model="newUserMap.role"
              class="w-full border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500">
              <option value="owner">owner</option>
              <option value="manager">manager</option>
              <option value="task_runner">task_runner</option>
              <option value="guest">guest</option>
            </select>
          </div>
        </div>
        <div class="flex gap-2 mt-3">
          <button @click="addLdapUserMapping" :disabled="savingUserMap || !newUserMap.ldap_username"
            class="bg-brand-600 hover:bg-brand-700 text-white text-sm px-3 py-1.5 rounded-lg disabled:opacity-60">
            {{ savingUserMap ? 'Adding…' : 'Add mapping' }}
          </button>
          <button @click="showAddUserMap = false" class="text-sm text-gray-500">Cancel</button>
        </div>
      </div>

      <div v-if="ldapUserMappings.length > 0"
        class="bg-white rounded-xl border border-indigo-100 divide-y divide-gray-100">
        <div v-for="m in ldapUserMappings" :key="m.id"
          class="flex items-center justify-between px-5 py-3">
          <div class="flex items-center gap-3">
            <div class="w-7 h-7 rounded-lg bg-indigo-50 flex items-center justify-center flex-shrink-0">
              <UserRoundCog class="w-3.5 h-3.5 text-indigo-500" />
            </div>
            <span class="text-sm font-mono text-gray-700">{{ m.ldap_username }}</span>
          </div>
          <div class="flex items-center gap-3">
            <span class="text-xs font-medium px-2 py-0.5 rounded-full" :class="roleBadge[m.role]">
              {{ m.role }}
            </span>
            <button @click="removeLdapUserMapping(m.id)" class="text-gray-300 hover:text-red-500 transition-colors">
              <Trash2 class="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
      <p v-else-if="!showAddUserMap" class="text-sm text-gray-400 italic">No direct user mappings.</p>
    </div>
  </div>
</template>
