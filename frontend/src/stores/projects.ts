import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { projectsApi } from '@/api/projects'
import { useAuthStore } from '@/stores/auth'

export interface Project {
  id: string
  name: string
  alert: boolean
  max_parallel_tasks: number
  created_at: string
}

export interface SurveyVar {
  name: string
  title: string
  description: string
  type: 'string' | 'int' | 'enum' | 'secret'
  required: boolean
  default: string
  values: string[]
}

export interface Template {
  id: string
  name: string
  description: string
  app: string
  type: string
  playbook: string
  repository_id: string | null
  inventory_id: string | null
  environment_id: string | null
  arguments: string
  allow_override_args: boolean
  allow_parallel: boolean
  suppress_success_alerts: boolean
  survey_vars: SurveyVar[]
  created_at: string
}

export interface Task {
  id: string
  template_id: string
  status: string
  user_id: string | null
  created_at: string
  start: string | null
  end: string | null
  commit_hash: string
  version: string
  build_task_id: string | null
  exit_code: number | null
  username: string | null
  triggered_by: 'manual' | 'schedule' | 'token'
  trigger_name: string
}

export const useProjectsStore = defineStore('projects', () => {
  const auth = useAuthStore()

  const projects = ref<Project[]>([])
  const current = ref<Project | null>(null)
  const templates = ref<Template[]>([])
  const tasks = ref<Task[]>([])
  const loading = ref(false)

  /** Role of the logged-in user in the currently open project.
   *  Admins always get 'owner'. null = not a member (should not happen in practice). */
  const currentRole = ref<'owner' | 'manager' | 'task_runner' | 'guest' | null>(null)

  /** Can create/edit/delete resources (templates, keys, repos, …) */
  const canManage = computed(() =>
    auth.isAdmin || currentRole.value === 'owner' || currentRole.value === 'manager'
  )

  /** Can start/stop tasks */
  const canRun = computed(() =>
    auth.isAdmin ||
    currentRole.value === 'owner' ||
    currentRole.value === 'manager' ||
    currentRole.value === 'task_runner'
  )

  /** Can delete the project itself (owner only) */
  const canDeleteProject = computed(() =>
    auth.isAdmin || currentRole.value === 'owner'
  )

  async function fetchProjects() {
    loading.value = true
    try {
      const { data } = await projectsApi.list()
      projects.value = data
    } finally {
      loading.value = false
    }
  }

  async function fetchProject(id: string) {
    // Ensure auth user is loaded before resolving role
    if (!auth.user) await auth.fetchMe()

    const [projRes, membersRes] = await Promise.all([
      projectsApi.get(id),
      projectsApi.listMembers(id).catch(() => ({ data: [] })),
    ])
    current.value = projRes.data

    // Admins always get owner role; regular users look up their membership
    if (auth.isAdmin) {
      currentRole.value = 'owner'
    } else {
      const me = membersRes.data.find((m: any) => m.user_id === auth.user?.id)
      currentRole.value = (me?.role as typeof currentRole.value) ?? null
    }

    return projRes.data
  }

  function resetProjectRole() {
    // Reset project info but do NOT clear currentRole here.
    // Clearing it causes a brief window where canManage/canRun are false
    // while the next fetchProject is in flight, making buttons flash away.
    // The server enforces RBAC on every request regardless.
    current.value = null
  }

  /** Loads ALL templates (all pages) into store.templates for lookups (e.g. templateTypeMap). */
  async function fetchTemplates(projectId: string) {
    const { data } = await projectsApi.listTemplates(projectId, 1, 500)
    templates.value = [...(data.items ?? data)].sort((a: Template, b: Template) =>
      a.name.localeCompare(b.name)
    )
    return templates.value
  }

  /** Loads one page of tasks into store.tasks. */
  async function fetchTasks(projectId: string, page = 1, perPage = 20) {
    const { data } = await projectsApi.listTasks(projectId, page, perPage)
    tasks.value = data.items ?? data
    return data as { items: Task[]; total: number; page: number; per_page: number }
  }

  async function createProject(name: string) {
    const { data } = await projectsApi.create({ name })
    projects.value.unshift(data)
    return data
  }

  return {
    projects, current, templates, tasks, loading,
    currentRole, canManage, canRun, canDeleteProject,
    fetchProjects, fetchProject, fetchTemplates, fetchTasks, createProject,
    resetProjectRole,
  }
})
