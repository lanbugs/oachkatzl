<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useProjectsStore } from '@/stores/projects'
import { RouterLink } from 'vue-router'
import { FolderKanban, PlayCircle } from 'lucide-vue-next'

const auth = useAuthStore()
const projects = useProjectsStore()

onMounted(async () => {
  if (!auth.user) await auth.fetchMe()
  await projects.fetchProjects()
})
</script>

<template>
  <div>
    <h1 class="text-2xl font-semibold text-gray-900 mb-1">Dashboard</h1>
    <p class="text-sm text-gray-500 mb-6">Welcome back, {{ auth.user?.name || auth.user?.username }}</p>

    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      <RouterLink
        v-for="p in projects.projects"
        :key="p.id"
        :to="`/projects/${p.id}`"
        class="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md transition-shadow group"
      >
        <div class="flex items-start gap-3">
          <div class="p-2 bg-brand-50 rounded-lg">
            <FolderKanban class="w-5 h-5 text-brand-600" />
          </div>
          <div class="flex-1 min-w-0">
            <p class="font-medium text-gray-900 truncate group-hover:text-brand-600 transition-colors">{{ p.name }}</p>
            <p class="text-xs text-gray-400 mt-0.5">{{ new Date(p.created_at).toLocaleDateString() }}</p>
          </div>
        </div>
      </RouterLink>

      <div v-if="projects.projects.length === 0 && !projects.loading"
        class="col-span-full text-center py-12 text-gray-400 text-sm">
        No projects yet. <RouterLink to="/projects" class="text-brand-600 hover:underline">Create one →</RouterLink>
      </div>
    </div>
  </div>
</template>
