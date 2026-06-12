import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'login', component: () => import('@/views/LoginView.vue'), meta: { public: true } },
    {
      path: '/',
      component: () => import('@/layouts/AppLayout.vue'),
      children: [
        { path: '', name: 'dashboard', component: () => import('@/views/DashboardView.vue') },
        { path: 'projects', name: 'projects', component: () => import('@/views/ProjectsView.vue') },
        { path: 'help', name: 'help', component: () => import('@/views/HelpView.vue') },
        { path: 'profile', name: 'profile', component: () => import('@/views/ProfileView.vue') },
        {
          path: 'projects/:projectId',
          component: () => import('@/views/project/ProjectLayout.vue'),
          children: [
            { path: '', name: 'project-templates', component: () => import('@/views/project/TemplatesView.vue') },
            { path: 'templates/new', name: 'template-new', component: () => import('@/views/project/TemplateEditView.vue') },
            { path: 'templates/:templateId/edit', name: 'template-edit', component: () => import('@/views/project/TemplateEditView.vue') },
            { path: 'tasks', name: 'project-tasks', component: () => import('@/views/project/TasksView.vue') },
            { path: 'tasks/:taskId', name: 'task-detail', component: () => import('@/views/project/TaskDetailView.vue') },
            { path: 'keys', name: 'project-keys', component: () => import('@/views/project/KeysView.vue') },
            { path: 'credentials', name: 'project-credentials', component: () => import('@/views/project/CredentialsView.vue') },
            { path: 'repositories', name: 'project-repositories', component: () => import('@/views/project/RepositoriesView.vue') },
            { path: 'inventories', name: 'project-inventories', component: () => import('@/views/project/InventoriesView.vue') },
            { path: 'environments', name: 'project-environments', component: () => import('@/views/project/EnvironmentsView.vue') },
            { path: 'schedules', name: 'project-schedules', component: () => import('@/views/project/SchedulesView.vue') },
            { path: 'notifications', name: 'project-notifications', component: () => import('@/views/project/NotificationsView.vue') },
            { path: 'members', name: 'project-members', component: () => import('@/views/project/MembersView.vue') },
            { path: 'workflows', name: 'project-workflows', component: () => import('@/views/project/WorkflowsView.vue') },
            { path: 'workflows/new', name: 'workflow-new', component: () => import('@/views/project/WorkflowEditView.vue') },
            { path: 'workflows/:workflowId/edit', name: 'workflow-edit', component: () => import('@/views/project/WorkflowEditView.vue') },
            { path: 'workflow-runs/:runId', name: 'workflow-run-detail', component: () => import('@/views/project/WorkflowRunView.vue') },
          ],
        },
        { path: 'admin/users', name: 'admin-users', component: () => import('@/views/admin/UsersView.vue'), meta: { admin: true } },
        { path: 'admin/custom-apps', name: 'admin-custom-apps', component: () => import('@/views/admin/CustomAppsView.vue'), meta: { admin: true } },
        { path: 'admin/credential-types', name: 'admin-credential-types', component: () => import('@/views/admin/CredentialTypesView.vue'), meta: { admin: true } },
        { path: 'admin/smtp', redirect: '/admin/settings' },
        { path: 'admin/settings', name: 'admin-settings', component: () => import('@/views/admin/GlobalSettingsView.vue'), meta: { admin: true } },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()

  if (!to.meta.public && !auth.isAuthenticated) return '/login'

  // If user data isn't loaded yet, fetch it so mustSetupMfa is accurate
  if (auth.isAuthenticated && !auth.user) {
    await auth.fetchMe()
  }

  // MFA enforce: redirect every route except /profile and /login to /profile
  if (auth.mustSetupMfa && to.path !== '/profile' && !to.meta.public) {
    return '/profile'
  }

  if (to.meta.admin && !auth.isAdmin) return '/'
  if (to.path === '/login' && auth.isAuthenticated) return '/'
})

export default router
