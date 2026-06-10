<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useProjectsStore } from '@/stores/projects'
import { useAuthStore } from '@/stores/auth'
import { Plus, FolderKanban, Trash2 } from 'lucide-vue-next'
import { projectsApi } from '@/api/projects'

const store = useProjectsStore()
const auth  = useAuthStore()
const router = useRouter()
const showNew = ref(false)
const newName = ref('')
const creating = ref(false)

onMounted(() => store.fetchProjects())

async function createProject() {
  if (!newName.value.trim()) return
  creating.value = true
  try {
    const p = await store.createProject(newName.value.trim())
    newName.value = ''
    showNew.value = false
    router.push(`/projects/${p.id}`)
  } finally {
    creating.value = false
  }
}

async function deleteProject(id: string) {
  if (!confirm('Delete this project and all its data?')) return
  await projectsApi.delete(id)
  store.projects = store.projects.filter(p => p.id !== id)
}
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-semibold text-gray-900">Projects</h1>
      <button v-if="auth.isAdmin" @click="showNew = true" class="flex items-center gap-2 bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors">
        <Plus class="w-4 h-4" /> New project
      </button>
    </div>

    <!-- New project form -->
    <div v-if="showNew && auth.isAdmin" class="mb-6 bg-white rounded-xl border border-gray-200 p-5">
      <h2 class="font-medium text-gray-900 mb-3">New project</h2>
      <form @submit.prevent="createProject" class="flex gap-3">
        <input v-model="newName" type="text" placeholder="Project name" required
          class="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
        <button type="submit" :disabled="creating"
          class="bg-brand-600 hover:bg-brand-700 text-white text-sm px-4 py-2 rounded-lg disabled:opacity-60">
          {{ creating ? 'Creating…' : 'Create' }}
        </button>
        <button type="button" @click="showNew = false"
          class="text-sm text-gray-500 hover:text-gray-700 px-3 py-2">Cancel</button>
      </form>
    </div>

    <div class="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
      <div v-if="store.loading" class="p-6 text-center text-gray-400 text-sm">Loading…</div>
      <div v-else-if="store.projects.length === 0" class="p-6 text-center text-gray-400 text-sm">
        No projects. Create one above.
      </div>
      <div v-for="p in store.projects" :key="p.id"
        class="flex items-center justify-between px-5 py-4 hover:bg-gray-50 transition-colors">
        <RouterLink :to="`/projects/${p.id}`" class="flex items-center gap-3 flex-1 min-w-0">
          <FolderKanban class="w-5 h-5 text-brand-500 shrink-0" />
          <span class="font-medium text-gray-900 truncate hover:text-brand-600 transition-colors">{{ p.name }}</span>
        </RouterLink>
        <button @click="deleteProject(p.id)"
          class="ml-4 text-gray-300 hover:text-red-500 transition-colors">
          <Trash2 class="w-4 h-4" />
        </button>
      </div>
    </div>
  </div>
</template>
