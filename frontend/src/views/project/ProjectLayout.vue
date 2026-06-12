<script setup lang="ts">
import { onMounted, computed } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'
import { useProjectsStore } from '@/stores/projects'
import { useAuthStore } from '@/stores/auth'
import { LayoutTemplate, ListChecks, Key, GitBranch, Users, Server, Variable, Clock, Bell, GitMerge } from 'lucide-vue-next'

const route = useRoute()
const store = useProjectsStore()
const auth  = useAuthStore()
const projectId = computed(() => route.params.projectId as string)

onMounted(() => store.fetchProject(projectId.value))

// Role rank: higher = more permissions
const RANK: Record<string, number> = { guest: 1, task_runner: 2, manager: 3, owner: 4 }

type Role = 'guest' | 'task_runner' | 'manager' | 'owner'

const allTabs = computed(() => [
  // visible to everyone (guest+)
  { name: 'Templates',     to: `/projects/${projectId.value}`,               icon: LayoutTemplate, exact: true,  minRole: 'guest'       as Role },
  { name: 'Tasks',         to: `/projects/${projectId.value}/tasks`,          icon: ListChecks,                   minRole: 'guest'       as Role },
  { name: 'Workflows',     to: `/projects/${projectId.value}/workflows`,      icon: GitMerge,                     minRole: 'task_runner' as Role },
  // resource tabs — manager+ only
  { name: 'Keys & Credentials', to: `/projects/${projectId.value}/keys`,     icon: Key,                          minRole: 'manager'     as Role },
  { name: 'Repositories',  to: `/projects/${projectId.value}/repositories`,   icon: GitBranch,                    minRole: 'manager'     as Role },
  { name: 'Inventories',   to: `/projects/${projectId.value}/inventories`,    icon: Server,                       minRole: 'manager'     as Role },
  { name: 'Environments',  to: `/projects/${projectId.value}/environments`,   icon: Variable,                     minRole: 'manager'     as Role },
  { name: 'Schedules',     to: `/projects/${projectId.value}/schedules`,      icon: Clock,                        minRole: 'manager'     as Role },
  { name: 'Notifications', to: `/projects/${projectId.value}/notifications`,  icon: Bell,                         minRole: 'manager'     as Role },
  // admin tabs — owner only
  { name: 'Members',       to: `/projects/${projectId.value}/members`,        icon: Users,                        minRole: 'owner'       as Role },
])

const tabs = computed(() => {
  const role = store.currentRole ?? 'guest'
  const userRank = auth.isAdmin ? 99 : (RANK[role] ?? 0)
  return allTabs.value.filter(t => userRank >= RANK[t.minRole])
})

function isActive(tab: { to: string; exact?: boolean }) {
  if (tab.exact) return route.path === tab.to
  return route.path.startsWith(tab.to)
}
</script>

<template>
  <div>
    <div class="mb-1">
      <RouterLink to="/projects" class="text-xs text-gray-400 hover:text-gray-600">Projects</RouterLink>
      <span class="text-xs text-gray-300 mx-1">/</span>
      <span class="text-xs text-gray-600 font-medium">{{ store.current?.name }}</span>
    </div>
    <h1 class="text-2xl font-semibold text-gray-900 mb-4">{{ store.current?.name }}</h1>

    <div class="flex flex-wrap gap-0.5 border-b border-gray-200 mb-6">
      <RouterLink
        v-for="tab in tabs" :key="tab.name" :to="tab.to"
        class="flex items-center gap-1.5 px-3 py-2 text-sm font-medium border-b-2 -mb-px transition-colors whitespace-nowrap"
        :class="isActive(tab)
          ? 'border-brand-600 text-brand-600'
          : 'border-transparent text-gray-500 hover:text-gray-700'"
      >
        <component :is="tab.icon" class="w-4 h-4" />
        {{ tab.name }}
      </RouterLink>
    </div>

    <RouterView />
  </div>
</template>
