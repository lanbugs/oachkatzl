<script setup lang="ts">
import { onMounted, onUnmounted, ref, computed, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { projectsApi } from '@/api/projects'
import { StopCircle, Loader2 } from 'lucide-vue-next'
import { formatLogLine } from '@/composables/useAnsi'

const route = useRoute()
const projectId = computed(() => route.params.projectId as string)
const taskId = computed(() => route.params.taskId as string)

const task = ref<any>(null)
const logLines = ref<string[]>([])
const stopping = ref(false)
const logEl = ref<HTMLElement | null>(null)

const RUNNING = new Set(['waiting', 'starting', 'running'])
let pollTimer: ReturnType<typeof setInterval> | null = null

function isRunning() {
  return task.value && RUNNING.has(task.value.status)
}

function scrollBottom() {
  nextTick(() => {
    if (logEl.value) logEl.value.scrollTop = logEl.value.scrollHeight
  })
}

async function poll() {
  try {
    const [taskRes, logRes] = await Promise.all([
      projectsApi.getTask(projectId.value, taskId.value),
      projectsApi.getTaskLog(projectId.value, taskId.value),
    ])
    task.value = taskRes.data

    const raw: string = logRes.data.output || ''
    const lines = raw ? raw.split('\n') : []
    const atBottom = logEl.value
      ? logEl.value.scrollTop + logEl.value.clientHeight >= logEl.value.scrollHeight - 40
      : true

    if (lines.length !== logLines.value.length) {
      logLines.value = lines
      if (atBottom) scrollBottom()
    }

    if (!isRunning()) stopPoll()
  } catch {
    // network hiccup — keep polling
  }
}

function startPoll() {
  if (pollTimer) return
  pollTimer = setInterval(poll, 1500)
}

function stopPoll() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

onMounted(async () => {
  await poll()          // immediate first load
  if (isRunning()) startPoll()
})

onUnmounted(stopPoll)

async function stopTask() {
  stopping.value = true
  try {
    await projectsApi.stopTask(projectId.value, taskId.value)
  } finally {
    stopping.value = false
  }
}

const statusColor: Record<string, string> = {
  success: 'text-green-500',
  error:   'text-red-500',
  running: 'text-blue-400',
  starting:'text-blue-400',
  waiting: 'text-gray-400',
  stopped: 'text-orange-400',
}

const statusLabel: Record<string, string> = {
  waiting:  'Waiting in queue',
  starting: 'Starting…',
  running:  'Running',
  success:  'Success',
  error:    'Failed',
  stopped:  'Stopped',
}
</script>

<template>
  <div v-if="task">
    <!-- Header -->
    <div class="flex items-center justify-between mb-4">
      <div>
        <h2 class="text-lg font-medium text-gray-900">
          Task <code class="text-sm bg-gray-100 px-1.5 py-0.5 rounded font-mono">{{ task.id.slice(-8) }}</code>
        </h2>
        <p class="flex items-center gap-1.5 text-sm mt-0.5" :class="statusColor[task.status] ?? 'text-gray-500'">
          <Loader2 v-if="RUNNING.has(task.status)" class="w-3.5 h-3.5 animate-spin" />
          {{ statusLabel[task.status] ?? task.status.toUpperCase() }}
          <span v-if="task.exit_code !== null" class="text-gray-400 ml-1">· exit {{ task.exit_code }}</span>
          <span v-if="task.commit_hash" class="text-gray-400 ml-1 font-mono text-xs">· {{ task.commit_hash.slice(0,8) }}</span>
        </p>
        <div class="flex items-center gap-2 mt-1 flex-wrap">
          <!-- Build version -->
          <span v-if="task.version"
            class="text-xs bg-green-50 text-green-700 border border-green-200 px-2 py-0.5 rounded font-mono font-semibold"
            title="Build version">
            🏗 v{{ task.version }}
          </span>
          <!-- Deploy references a build -->
          <span v-if="task.build_task_id"
            class="text-xs bg-orange-50 text-orange-700 border border-orange-200 px-2 py-0.5 rounded font-medium"
            :title="`Deployed build task: ${task.build_task_id}`">
            🚀 deploy · build <code class="font-mono">{{ task.build_task_id.slice(-8) }}</code>
          </span>
          <!-- Schedule trigger -->
          <span v-if="task.triggered_by === 'schedule'"
            class="text-xs bg-purple-50 text-purple-600 border border-purple-200 px-1.5 py-0.5 rounded font-medium"
            :title="`Cron: ${task.trigger_name}`">
            ⏱ Scheduled <span v-if="task.trigger_name" class="font-mono font-normal">{{ task.trigger_name }}</span>
          </span>
          <!-- Token trigger -->
          <span v-else-if="task.triggered_by === 'token'"
            class="text-xs bg-indigo-50 text-indigo-700 border border-indigo-200 px-1.5 py-0.5 rounded font-medium">
            🔑 Via token: <strong>{{ task.trigger_name || 'unknown' }}</strong>
          </span>
        </div>
      </div>
      <button
        v-if="RUNNING.has(task.status)"
        @click="stopTask"
        :disabled="stopping"
        class="flex items-center gap-2 text-sm bg-red-600 hover:bg-red-700 text-white px-3 py-1.5 rounded-lg disabled:opacity-60"
      >
        <StopCircle class="w-4 h-4" />
        {{ stopping ? 'Stopping…' : 'Stop' }}
      </button>
    </div>

    <!-- Log -->
    <div
      ref="logEl"
      class="bg-gray-950 rounded-xl p-4 font-mono text-xs text-gray-200 overflow-y-auto"
      style="max-height: 70vh; min-height: 200px"
    >
      <div v-if="logLines.length === 0" class="text-gray-500 italic">
        <span v-if="RUNNING.has(task.status)">Waiting for output…</span>
        <span v-else>No output recorded.</span>
      </div>
      <!-- v-html is safe here: ansiToHtml escapes HTML entities before processing ANSI codes -->
      <div v-for="(line, i) in logLines" :key="i"
        class="leading-5 whitespace-pre-wrap break-all"
        v-html="formatLogLine(line)"
      />
    </div>

    <!-- Timestamps -->
    <div class="flex gap-6 mt-3 text-xs text-gray-400">
      <span v-if="task.start">Started: {{ new Date(task.start).toLocaleString() }}</span>
      <span v-if="task.end">Finished: {{ new Date(task.end).toLocaleString() }}</span>
    </div>
  </div>
  <div v-else class="text-center py-12 text-gray-400 text-sm">Loading…</div>
</template>
