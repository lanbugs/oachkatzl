<script setup lang="ts">
import { onMounted, onUnmounted, ref, computed, watch } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { useProjectsStore } from '@/stores/projects'
import { projectsApi } from '@/api/projects'
import { CheckCircle2, XCircle, Clock, Loader2, StopCircle, ChevronLeft, ChevronRight } from 'lucide-vue-next'

const route = useRoute()
const store = useProjectsStore()
const projectId = computed(() => route.params.projectId as string)

const stopping = ref<string | null>(null)

// Quick lookups: template_id → type / name
const templateTypeMap = computed(() => {
  const m: Record<string, string> = {}
  for (const t of store.templates) m[t.id] = t.type
  return m
})

const templateNameMap = computed(() => {
  const m: Record<string, string> = {}
  for (const t of store.templates) m[t.id] = t.name
  return m
})

// ── Pagination state ──────────────────────────────────────────────────────
const PER_PAGE = 20
const page  = ref(1)
const total = ref(0)
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / PER_PAGE)))

function prevPage() { if (page.value > 1) page.value-- }
function nextPage() { if (page.value < totalPages.value) page.value++ }
// ─────────────────────────────────────────────────────────────────────────

// Poll for status updates while any active task is on the current page
let pollTimer: ReturnType<typeof setInterval> | null = null

const ACTIVE = new Set(['waiting', 'starting', 'running'])

function hasActive() {
  return store.tasks.some(t => ACTIVE.has(t.status))
}

async function refresh() {
  const result = await store.fetchTasks(projectId.value, page.value, PER_PAGE)
  total.value = result.total ?? total.value
  if (!hasActive()) stopPoll()
}

function startPoll() {
  if (pollTimer) return
  pollTimer = setInterval(refresh, 2000)
}

function stopPoll() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

async function load() {
  // Templates must be loaded so we can look up types
  if (store.templates.length === 0) await store.fetchTemplates(projectId.value)
  await refresh()
  if (hasActive()) startPoll()
}

onMounted(load)
onUnmounted(stopPoll)

// Reload when page changes; restart poll if needed
watch(page, async () => {
  stopPoll()
  await refresh()
  if (hasActive()) startPoll()
})

async function stopTask(event: Event, taskId: string) {
  event.preventDefault()
  event.stopPropagation()
  stopping.value = taskId
  try {
    await projectsApi.stopTask(projectId.value, taskId)
    const t = store.tasks.find(x => x.id === taskId)
    if (t) t.status = 'stopped'
  } catch (e: any) {
    alert(e.response?.data?.message || 'Failed to stop task')
  } finally {
    stopping.value = null
  }
}

const statusConfig: Record<string, { label: string; icon: any; color: string }> = {
  waiting:  { label: 'Waiting',  icon: Clock,        color: 'text-gray-400' },
  starting: { label: 'Starting', icon: Loader2,       color: 'text-blue-400 animate-spin' },
  running:  { label: 'Running',  icon: Loader2,       color: 'text-blue-500 animate-spin' },
  success:  { label: 'Success',  icon: CheckCircle2,  color: 'text-green-500' },
  error:    { label: 'Error',    icon: XCircle,       color: 'text-red-500' },
  stopped:  { label: 'Stopped',  icon: StopCircle,    color: 'text-orange-400' },
}

function duration(task: any): string {
  if (!task.start) return '—'
  const end = task.end ? new Date(task.end) : new Date()
  const s = Math.round((end.getTime() - new Date(task.start).getTime()) / 1000)
  return s < 60 ? `${s}s` : `${Math.floor(s / 60)}m ${s % 60}s`
}
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-4">
      <h2 class="text-lg font-medium text-gray-900">Tasks</h2>
      <p v-if="total > 0" class="text-xs text-gray-400">{{ total }} total</p>
    </div>

    <div class="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
      <div v-if="store.tasks.length === 0" class="p-6 text-center text-gray-400 text-sm">No tasks yet.</div>

      <div
        v-for="t in store.tasks" :key="t.id"
        class="flex items-center gap-4 px-5 py-3 hover:bg-gray-50 transition-colors"
      >
        <!-- Status icon -->
        <component
          :is="statusConfig[t.status]?.icon ?? Clock"
          class="w-5 h-5 shrink-0"
          :class="statusConfig[t.status]?.color"
        />

        <!-- Task info — clickable -->
        <RouterLink
          :to="`/projects/${projectId}/tasks/${t.id}`"
          class="flex-1 min-w-0 flex items-center gap-4"
        >
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 flex-wrap">
              <p class="text-sm font-medium text-gray-900 truncate">
                {{ templateNameMap[t.template_id] ?? '—' }}
              </p>
              <code class="font-mono text-xs text-gray-400">{{ t.id.slice(-8) }}</code>
            </div>
            <div class="flex items-center gap-2 flex-wrap mt-0.5">

              <!-- Template type badge -->
              <span v-if="templateTypeMap[t.template_id] === 'build'"
                class="text-xs bg-green-100 text-green-800 border border-green-300 px-1.5 py-0.5 rounded font-medium"
              >🏗 build</span>
              <span v-else-if="templateTypeMap[t.template_id] === 'deploy'"
                class="text-xs bg-orange-100 text-orange-800 border border-orange-300 px-1.5 py-0.5 rounded font-medium"
              >🚀 deploy</span>
              <span v-else-if="templateTypeMap[t.template_id] === 'task'"
                class="text-xs bg-blue-50 text-blue-700 border border-blue-200 px-1.5 py-0.5 rounded font-medium"
              >▶ task</span>

              <!-- Version (build result) -->
              <span v-if="t.version"
                class="text-xs bg-gray-100 text-gray-700 border border-gray-300 px-1.5 py-0.5 rounded font-mono font-medium"
                title="Build version"
              >v{{ t.version }}</span>

              <!-- Trigger badges -->
              <span v-if="t.triggered_by === 'schedule'"
                class="text-xs bg-purple-50 text-purple-600 border border-purple-200 px-1.5 py-0.5 rounded font-medium"
                :title="`Cron: ${t.trigger_name}`"
              >⏱ Scheduled</span>
              <span v-else-if="t.triggered_by === 'token'"
                class="text-xs bg-indigo-50 text-indigo-700 border border-indigo-200 px-1.5 py-0.5 rounded font-medium"
                :title="`Token: ${t.trigger_name}`"
              >🔑 {{ t.trigger_name || 'Token' }}</span>
              <RouterLink v-else-if="t.triggered_by === 'workflow' && t.trigger_name"
                :to="`/projects/${projectId}/workflow-runs/${t.trigger_name}`"
                class="text-xs bg-teal-50 text-teal-700 border border-teal-200 px-1.5 py-0.5 rounded font-medium hover:bg-teal-100"
                :title="`Part of workflow run ${t.trigger_name.slice(-8)}`"
              >⬡ Workflow</RouterLink>
            </div>
            <p class="text-xs text-gray-400 mt-0.5">
              {{ new Date(t.created_at).toLocaleString() }}
              <span v-if="t.username"> · 👤 {{ t.username }}</span>
            </p>
          </div>
          <div class="text-right shrink-0">
            <span class="text-xs font-medium" :class="statusConfig[t.status]?.color">
              {{ statusConfig[t.status]?.label }}
            </span>
            <p class="text-xs text-gray-400">{{ duration(t) }}</p>
          </div>
        </RouterLink>

        <!-- Stop button -->
        <button
          v-if="ACTIVE.has(t.status) && store.canRun"
          @click="stopTask($event, t.id)"
          :disabled="stopping === t.id"
          class="shrink-0 flex items-center gap-1 text-xs text-red-500 hover:text-red-700 border border-red-200 hover:border-red-400 bg-red-50 hover:bg-red-100 px-2 py-1 rounded-lg transition-colors disabled:opacity-50"
          title="Stop task"
        >
          <StopCircle class="w-3.5 h-3.5" />
          {{ stopping === t.id ? '…' : 'Stop' }}
        </button>
      </div>
    </div>

    <!-- Pagination -->
    <div v-if="total > PER_PAGE" class="flex items-center justify-between mt-4">
      <p class="text-xs text-gray-400">
        {{ (page - 1) * PER_PAGE + 1 }}–{{ Math.min(page * PER_PAGE, total) }} of {{ total }}
      </p>
      <div class="flex items-center gap-1">
        <button @click="prevPage" :disabled="page === 1"
          class="p-1.5 rounded-lg border border-gray-200 text-gray-500 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors">
          <ChevronLeft class="w-4 h-4" />
        </button>
        <template v-for="p in totalPages" :key="p">
          <button
            v-if="totalPages <= 7 || p === 1 || p === totalPages || Math.abs(p - page) <= 1"
            @click="page = p"
            class="min-w-[2rem] h-8 rounded-lg border text-xs font-medium transition-colors"
            :class="p === page
              ? 'bg-brand-600 text-white border-brand-600'
              : 'border-gray-200 text-gray-600 hover:bg-gray-50'"
          >{{ p }}</button>
          <span v-else-if="Math.abs(p - page) === 2" class="px-1 text-gray-400 text-xs">…</span>
        </template>
        <button @click="nextPage" :disabled="page === totalPages"
          class="p-1.5 rounded-lg border border-gray-200 text-gray-500 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors">
          <ChevronRight class="w-4 h-4" />
        </button>
      </div>
    </div>
  </div>
</template>
