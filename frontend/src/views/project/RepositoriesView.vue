<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useProjectsStore } from '@/stores/projects'
import { projectsApi } from '@/api/projects'
import { GitBranch, Plus, Pencil, Trash2, Check, X } from 'lucide-vue-next'

const route = useRoute()
const store = useProjectsStore()
const projectId = computed(() => route.params.projectId as string)

const repos = ref<any[]>([])
const keys = ref<any[]>([])
const showNew = ref(false)
const editId = ref<string | null>(null)

const emptyForm = () => ({ name: '', git_url: '', git_branch: 'main', ssh_key_id: '' })
const form = ref(emptyForm())
const saving = ref(false)

const sshKeys = computed(() => keys.value.filter(k => k.type === 'ssh'))

onMounted(async () => {
  const [reposRes, keysRes] = await Promise.all([
    projectsApi.listRepos(projectId.value),
    projectsApi.listKeys(projectId.value),
  ])
  repos.value = reposRes.data
  keys.value = keysRes.data
})

function startEdit(r: any) {
  editId.value = r.id
  form.value = { name: r.name, git_url: r.git_url, git_branch: r.git_branch, ssh_key_id: r.ssh_key_id || '' }
}
function cancelEdit() {
  editId.value = null
  showNew.value = false
  form.value = emptyForm()
}

async function save() {
  saving.value = true
  try {
    const payload = { ...form.value, ssh_key_id: form.value.ssh_key_id || null }
    if (editId.value) {
      const { data } = await projectsApi.updateRepo(projectId.value, editId.value, payload)
      const idx = repos.value.findIndex(r => r.id === editId.value)
      if (idx !== -1) repos.value[idx] = data
    } else {
      const { data } = await projectsApi.createRepo(projectId.value, payload)
      repos.value.push(data)
    }
    cancelEdit()
  } finally {
    saving.value = false
  }
}

async function deleteRepo(id: string) {
  if (!confirm('Delete this repository?')) return
  await projectsApi.deleteRepo(projectId.value, id)
  repos.value = repos.value.filter(r => r.id !== id)
}
</script>

<template>
  <div>
    <div class="flex justify-between items-center mb-4">
      <h2 class="text-lg font-medium text-gray-900">Repositories</h2>
      <button v-if="store.canManage" @click="showNew = true; editId = null; form = emptyForm()"
        class="flex items-center gap-2 bg-brand-600 hover:bg-brand-700 text-white text-sm px-3 py-1.5 rounded-lg">
        <Plus class="w-4 h-4" /> New repository
      </button>
    </div>

    <!-- Inline create/edit form -->
    <div v-if="showNew || editId" class="mb-4 bg-white rounded-xl border border-brand-200 p-5">
      <h3 class="font-medium text-gray-900 mb-4">{{ editId ? 'Edit repository' : 'New repository' }}</h3>
      <form @submit.prevent="save" class="space-y-4">
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">Name *</label>
            <input v-model="form.name" required class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">Branch</label>
            <input v-model="form.git_branch" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
          </div>
          <div class="col-span-2">
            <label class="block text-xs font-medium text-gray-600 mb-1">Git URL *</label>
            <input v-model="form.git_url" required class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-brand-500"
              placeholder="git@github.com:org/repo.git  or  https://github.com/org/repo.git" />
          </div>
          <div class="col-span-2">
            <label class="block text-xs font-medium text-gray-600 mb-1">SSH key (for private repos)</label>
            <select v-model="form.ssh_key_id" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500">
              <option value="">— None (public repo / HTTPS) —</option>
              <option v-for="k in sshKeys" :key="k.id" :value="k.id">{{ k.name }}</option>
            </select>
            <p v-if="sshKeys.length === 0" class="text-xs text-gray-400 mt-1">
              No SSH keys found. <RouterLink :to="`/projects/${projectId}/keys`" class="text-brand-600 hover:underline">Add one in Keys →</RouterLink>
            </p>
          </div>
        </div>
        <div class="flex gap-3">
          <button type="submit" :disabled="saving"
            class="bg-brand-600 hover:bg-brand-700 text-white text-sm px-4 py-2 rounded-lg disabled:opacity-60">
            {{ saving ? 'Saving…' : editId ? 'Save changes' : 'Add repository' }}
          </button>
          <button type="button" @click="cancelEdit" class="text-sm text-gray-500 hover:text-gray-700">Cancel</button>
        </div>
      </form>
    </div>

    <div class="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
      <div v-if="repos.length === 0" class="p-6 text-center text-gray-400 text-sm">No repositories yet.</div>
      <div v-for="r in repos" :key="r.id" class="flex items-center justify-between px-5 py-4">
        <div class="flex items-center gap-3 min-w-0">
          <GitBranch class="w-4 h-4 text-gray-400 shrink-0" />
          <div class="min-w-0">
            <p class="text-sm font-medium text-gray-900">{{ r.name }}</p>
            <p class="text-xs text-gray-400 font-mono truncate">{{ r.git_url }} <span class="not-italic text-gray-300 mx-1">@</span> {{ r.git_branch }}</p>
            <p v-if="r.ssh_key_id" class="text-xs text-blue-500 mt-0.5">
              🔑 SSH key linked
            </p>
          </div>
        </div>
        <div class="flex items-center gap-2 ml-4 shrink-0">
          <button v-if="store.canManage" @click="startEdit(r)" class="p-1.5 text-gray-400 hover:text-brand-600 transition-colors" title="Edit">
            <Pencil class="w-4 h-4" />
          </button>
          <button v-if="store.canManage" @click="deleteRepo(r.id)" class="p-1.5 text-gray-300 hover:text-red-500 transition-colors" title="Delete">
            <Trash2 class="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
