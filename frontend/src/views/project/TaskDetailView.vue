<script setup lang="ts">
import { onMounted, onUnmounted, ref, computed, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { projectsApi } from '@/api/projects'
import { StopCircle, Loader2, RotateCcw } from 'lucide-vue-next'
import { formatLogLine } from '@/composables/useAnsi'

const route = useRoute()
const router = useRouter()
const projectId = computed(() => route.params.projectId as string)
const taskId = computed(() => route.params.taskId as string)

const task = ref<any>(null)
const logLines = ref<string[]>([])
const stopping = ref(false)
const replaying = ref(false)
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

async function init() {
  task.value = null
  logLines.value = []
  stopPoll()
  await poll()
  if (isRunning()) startPoll()
}

onMounted(init)
onUnmounted(stopPoll)

watch(taskId, init)

async function stopTask() {
  stopping.value = true
  try {
    await projectsApi.stopTask(projectId.value, taskId.value)
  } finally {
    stopping.value = false
  }
}

async function replayTask() {
  const t = task.value
  const commitHint = t.commit_hash ? ` (Commit ${t.commit_hash.slice(0, 8)})` : ''
  if (!confirm(`Replay diesen Task nochmal mit den gleichen Survey-Antworten, Environment-Einstellungen und der gleichen Git-Revision${commitHint}?`)) return

  replaying.value = true
  try {
    const { data } = await projectsApi.startTask(projectId.value, t.template_id, {
      debug: t.debug,
      dry_run: t.dry_run,
      diff: t.diff,
      survey_answers: t.survey_answers,
      environment_override: t.environment_override,
      arguments_override: t.arguments_override,
      pin_commit: t.commit_hash || '',
    })
    router.push(`/projects/${projectId.value}/tasks/${data.id}`)
  } finally {
    replaying.value = false
  }
}


// ── Run parameters display ────────────────────────────────────────────────

function isSensitiveKey(key: string): boolean {
  const k = key.toLowerCase()
  return k.includes('pass') || k.includes('secret') || k.includes('token')
}

function parseJsonSafe(raw: string): Record<string, any> {
  try { return JSON.parse(raw || '{}') } catch { return {} }
}

const surveyEntries = computed(() => {
  const obj = parseJsonSafe(task.value?.survey_answers)
  return Object.entries(obj)
})

const envEntries = computed(() => {
  const obj = parseJsonSafe(task.value?.environment_override)
  return Object.entries(obj)
})

const hasRunParams = computed(() =>
  surveyEntries.value.length > 0 || envEntries.value.length > 0
)

// ── Status helpers ────────────────────────────────────────────────────────

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
          <span v-if="task.version"
            class="text-xs bg-green-50 text-green-700 border border-green-200 px-2 py-0.5 rounded font-mono font-semibold"
            title="Build version">
            🏗 v{{ task.version }}
          </span>
          <span v-if="task.build_task_id"
            class="text-xs bg-orange-50 text-orange-700 border border-orange-200 px-2 py-0.5 rounded font-medium"
            :title="`Deployed build task: ${task.build_task_id}`">
            🚀 deploy · build <code class="font-mono">{{ task.build_task_id.slice(-8) }}</code>
          </span>
          <span v-if="task.triggered_by === 'schedule'"
            class="text-xs bg-purple-50 text-purple-600 border border-purple-200 px-1.5 py-0.5 rounded font-medium"
            :title="`Cron: ${task.trigger_name}`">
            ⏱ Scheduled <span v-if="task.trigger_name" class="font-mono font-normal">{{ task.trigger_name }}</span>
          </span>
          <span v-else-if="task.triggered_by === 'token'"
            class="text-xs bg-indigo-50 text-indigo-700 border border-indigo-200 px-1.5 py-0.5 rounded font-medium">
            🔑 Via token: <strong>{{ task.trigger_name || 'unknown' }}</strong>
          </span>
          <span v-if="task.debug" class="text-xs bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">verbose</span>
          <span v-if="task.dry_run" class="text-xs bg-yellow-50 text-yellow-700 border border-yellow-200 px-1.5 py-0.5 rounded">--check</span>
          <span v-if="task.diff" class="text-xs bg-yellow-50 text-yellow-700 border border-yellow-200 px-1.5 py-0.5 rounded">--diff</span>
        </div>
      </div>

      <div class="flex items-center gap-2">
        <!-- Replay button — only for finished tasks -->
        <button
          v-if="!RUNNING.has(task.status)"
          @click="replayTask"
          :disabled="replaying"
          class="flex items-center gap-2 text-sm bg-brand-600 hover:bg-brand-700 text-white px-3 py-1.5 rounded-lg disabled:opacity-60"
          title="Re-run with the same survey answers, environment and git revision"
        >
          <RotateCcw class="w-4 h-4" :class="{ 'animate-spin': replaying }" />
          {{ replaying ? 'Starting…' : 'Replay' }}
        </button>

        <!-- Stop button — only while running -->
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
    </div>

    <!-- Run parameters -->
    <div v-if="hasRunParams" class="mb-4 bg-white rounded-xl border border-gray-200 p-5 space-y-4">
      <h3 class="text-sm font-medium text-gray-700">Run parameters</h3>

      <!-- Survey answers -->
      <div v-if="surveyEntries.length > 0">
        <p class="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Survey answers</p>
        <table class="w-full text-xs">
          <tbody>
            <tr v-for="[key, val] in surveyEntries" :key="key" class="border-b border-gray-50 last:border-0">
              <td class="py-1.5 pr-4 font-mono text-gray-500 w-1/3 align-top">{{ key }}</td>
              <td class="py-1.5 font-mono text-gray-800 break-all">
                <span v-if="isSensitiveKey(key)" class="text-gray-300 tracking-widest">••••••••</span>
                <span v-else>{{ val }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Environment override -->
      <div v-if="envEntries.length > 0">
        <p class="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Environment override</p>
        <table class="w-full text-xs">
          <tbody>
            <tr v-for="[key, val] in envEntries" :key="key" class="border-b border-gray-50 last:border-0">
              <td class="py-1.5 pr-4 font-mono text-gray-500 w-1/3 align-top">{{ key }}</td>
              <td class="py-1.5 font-mono text-gray-800 break-all">
                <span v-if="isSensitiveKey(key)" class="text-gray-300 tracking-widest">••••••••</span>
                <span v-else>{{ val }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
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