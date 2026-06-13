<script setup lang="ts">
import { onMounted, onUnmounted, ref, computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useProjectsStore } from '@/stores/projects'
import { RouterLink } from 'vue-router'
import { FolderKanban, Server, Cpu, Activity } from 'lucide-vue-next'
import api from '@/api/client'

const auth = useAuthStore()
const projects = useProjectsStore()

// ── Task stats ────────────────────────────────────────────────────────────
interface DayStats { date: string; success: number; error: number }
const stats = ref<DayStats[]>([])

// ── Worker status ─────────────────────────────────────────────────────────
interface PoolStatus {
  queue: string
  name: string
  workers_total: number
  capacity: number
  workers_busy: number
  tasks_active: number
}
const workerPools = ref<PoolStatus[]>([])
const workerLoading = ref(true)
let workerTimer: ReturnType<typeof setInterval> | null = null

async function fetchWorkerStatus() {
  try {
    const { data } = await api.get('/dashboard/worker-status')
    workerPools.value = data.pools
  } catch {
    // keep previous data on transient error
  } finally {
    workerLoading.value = false
  }
}

const totalWorkers  = computed(() => workerPools.value.reduce((s, p) => s + p.workers_total, 0))
const totalCapacity = computed(() => workerPools.value.reduce((s, p) => s + p.capacity,      0))
const totalActive   = computed(() => workerPools.value.reduce((s, p) => s + p.tasks_active,  0))
const totalBusy     = computed(() => workerPools.value.reduce((s, p) => s + p.workers_busy,  0))

onMounted(async () => {
  if (!auth.user) await auth.fetchMe()
  await Promise.all([
    projects.fetchProjects(),
    api.get('/dashboard/task-stats').then(r => { stats.value = r.data }),
    fetchWorkerStatus(),
  ])
  workerTimer = setInterval(fetchWorkerStatus, 15_000)
})

onUnmounted(() => {
  if (workerTimer) clearInterval(workerTimer)
})

// ── Chart layout constants (viewBox units) ────────────────────────────────
const W      = 1000
const H      = 200
const PAD_L  = 42
const PAD_R  = 16
const PAD_T  = 18
const PAD_B  = 48

const plotW = W - PAD_L - PAD_R   // 942
const plotH = H - PAD_T - PAD_B   // 134

// ── Scales ────────────────────────────────────────────────────────────────
const maxCount = computed(() => {
  const m = Math.max(...stats.value.flatMap(d => [d.success, d.error]), 1)
  return Math.ceil(m / 5) * 5
})

const yTicks = computed(() => {
  const mx = maxCount.value
  return [0, Math.round(mx / 2), mx]
})

function px(i: number): number {
  // 7 points: i=0 is leftmost, i=6 rightmost
  return PAD_L + (i / 6) * plotW
}

function py(count: number): number {
  return PAD_T + plotH - (count / maxCount.value) * plotH
}

// ── Polyline point strings ────────────────────────────────────────────────
const successPoints = computed(() =>
  stats.value.map((d, i) => `${px(i)},${py(d.success)}`).join(' ')
)
const errorPoints = computed(() =>
  stats.value.map((d, i) => `${px(i)},${py(d.error)}`).join(' ')
)

// Closed area path: line points + return along baseline
function areaPath(series: 'success' | 'error'): string {
  if (!stats.value.length) return ''
  const pts = stats.value.map((d, i) => `${px(i)},${py(series === 'success' ? d.success : d.error)}`)
  const base = `${px(6)},${PAD_T + plotH} ${px(0)},${PAD_T + plotH}`
  return `M ${pts[0]} L ${pts.slice(1).join(' L ')} L ${base} Z`
}

// ── Y-axis label position ─────────────────────────────────────────────────
function yLabelY(tick: number): number {
  return PAD_T + plotH - (tick / maxCount.value) * plotH
}

// ── X-axis label helpers ──────────────────────────────────────────────────
function weekday(dateStr: string): string {
  return new Date(dateStr + 'T12:00:00Z').toLocaleDateString('en', { weekday: 'short' })
}
function shortDate(dateStr: string): string {
  return new Date(dateStr + 'T12:00:00Z').toLocaleDateString('en', { month: 'short', day: 'numeric' })
}
function isToday(dateStr: string): boolean {
  return dateStr === new Date().toISOString().slice(0, 10)
}

// ── Totals for legend ─────────────────────────────────────────────────────
const totalSuccess = computed(() => stats.value.reduce((s, d) => s + d.success, 0))
const totalError   = computed(() => stats.value.reduce((s, d) => s + d.error,   0))
</script>

<template>
  <div>
    <h1 class="text-2xl font-semibold text-gray-900 mb-1">Dashboard</h1>
    <p class="text-sm text-gray-500 mb-6">Welcome back, {{ auth.user?.name || auth.user?.username }}</p>

    <!-- ── Task line chart ── -->
    <div class="bg-white rounded-xl border border-gray-200 p-5 mb-6">
      <div class="flex items-center justify-between mb-3">
        <h2 class="text-sm font-semibold text-gray-700">Tasks — last 7 days</h2>
        <div class="flex items-center gap-4 text-xs text-gray-500">
          <span class="flex items-center gap-1.5">
            <span class="inline-block w-6 h-0.5 bg-emerald-500 rounded"></span>
            Success <strong class="text-gray-700 ml-1">{{ totalSuccess }}</strong>
          </span>
          <span class="flex items-center gap-1.5">
            <span class="inline-block w-6 h-0.5 bg-red-500 rounded"></span>
            Failed <strong class="text-gray-700 ml-1">{{ totalError }}</strong>
          </span>
        </div>
      </div>

      <svg
        v-if="stats.length"
        :viewBox="`0 0 ${W} ${H}`"
        width="100%"
        aria-label="Task statistics line chart"
      >
        <!-- defs: gradient fills for areas -->
        <defs>
          <linearGradient id="gradSuccess" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%"   stop-color="#10b981" stop-opacity="0.18" />
            <stop offset="100%" stop-color="#10b981" stop-opacity="0.02" />
          </linearGradient>
          <linearGradient id="gradError" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%"   stop-color="#ef4444" stop-opacity="0.15" />
            <stop offset="100%" stop-color="#ef4444" stop-opacity="0.02" />
          </linearGradient>
        </defs>

        <!-- Gridlines + Y-axis labels -->
        <g v-for="tick in yTicks" :key="tick">
          <line
            :x1="PAD_L" :y1="yLabelY(tick)"
            :x2="W - PAD_R" :y2="yLabelY(tick)"
            stroke="#f0f0f0" stroke-width="1"
          />
          <text
            :x="PAD_L - 7" :y="yLabelY(tick)"
            text-anchor="end" dominant-baseline="middle"
            fill="#9ca3af" style="font-size:11px"
          >{{ tick }}</text>
        </g>

        <!-- Today column highlight -->
        <g v-for="(day, i) in stats" :key="day.date + '-bg'">
          <rect
            v-if="isToday(day.date)"
            :x="px(i) - plotW / 12"
            :y="PAD_T"
            :width="plotW / 6"
            :height="plotH"
            fill="#f3f4f6"
            rx="3"
          />
        </g>

        <!-- Filled areas -->
        <path :d="areaPath('success')" fill="url(#gradSuccess)" />
        <path :d="areaPath('error')"   fill="url(#gradError)"   />

        <!-- Lines -->
        <polyline
          :points="successPoints"
          fill="none"
          stroke="#10b981"
          stroke-width="2"
          stroke-linejoin="round"
          stroke-linecap="round"
        />
        <polyline
          :points="errorPoints"
          fill="none"
          stroke="#ef4444"
          stroke-width="2"
          stroke-linejoin="round"
          stroke-linecap="round"
        />

        <!-- Dots + value labels -->
        <g v-for="(day, i) in stats" :key="day.date">
          <!-- Success dot -->
          <circle
            :cx="px(i)" :cy="py(day.success)"
            r="3.5"
            fill="white" stroke="#10b981" stroke-width="2"
          />
          <!-- Value label above dot (only if > 0) -->
          <text
            v-if="day.success > 0"
            :x="px(i)" :y="py(day.success) - 8"
            text-anchor="middle"
            fill="#059669" style="font-size:10px;font-weight:600"
          >{{ day.success }}</text>

          <!-- Error dot -->
          <circle
            :cx="px(i)" :cy="py(day.error)"
            r="3.5"
            fill="white" stroke="#ef4444" stroke-width="2"
          />
          <text
            v-if="day.error > 0"
            :x="px(i)" :y="py(day.error) - 8"
            text-anchor="middle"
            fill="#dc2626" style="font-size:10px;font-weight:600"
          >{{ day.error }}</text>
        </g>

        <!-- X-axis baseline -->
        <line
          :x1="PAD_L" :y1="PAD_T + plotH"
          :x2="W - PAD_R" :y2="PAD_T + plotH"
          stroke="#e5e7eb" stroke-width="1"
        />

        <!-- X-axis labels -->
        <g v-for="(day, i) in stats" :key="day.date + '-label'">
          <text
            :x="px(i)" :y="PAD_T + plotH + 14"
            text-anchor="middle"
            :fill="isToday(day.date) ? '#2563eb' : '#6b7280'"
            :style="{ fontSize: '11px', fontWeight: isToday(day.date) ? '700' : '400' }"
          >{{ weekday(day.date) }}</text>
          <text
            :x="px(i)" :y="PAD_T + plotH + 29"
            text-anchor="middle"
            fill="#9ca3af" style="font-size:10px"
          >{{ shortDate(day.date) }}</text>
        </g>
      </svg>

      <div v-else class="h-24 flex items-center justify-center text-sm text-gray-400">
        Loading…
      </div>
    </div>

    <!-- ── Worker status ── -->
    <div class="bg-white rounded-xl border border-gray-200 p-5 mb-6">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-sm font-semibold text-gray-700">Worker Status</h2>
        <div class="flex items-center gap-4 text-xs text-gray-500">
          <span class="flex items-center gap-1.5">
            <span class="w-2 h-2 rounded-full bg-emerald-400 inline-block"></span>
            {{ totalWorkers }} online
          </span>
          <span class="flex items-center gap-1.5">
            <span class="w-2 h-2 rounded-full bg-blue-400 inline-block"></span>
            {{ totalActive }}&thinsp;/&thinsp;{{ totalCapacity }} slots
          </span>
        </div>
      </div>

      <!-- Loading skeleton -->
      <div v-if="workerLoading" class="flex gap-3">
        <div v-for="n in 2" :key="n"
          class="flex-1 h-20 rounded-lg bg-gray-100 animate-pulse" />
      </div>

      <!-- Pool cards -->
      <div v-else-if="workerPools.length" class="flex flex-wrap gap-3">
        <div
          v-for="pool in workerPools"
          :key="pool.queue"
          class="flex-1 min-w-44 rounded-lg border px-4 py-3 space-y-2"
          :class="pool.workers_total === 0
            ? 'border-gray-200 bg-gray-50'
            : pool.workers_busy > 0
              ? 'border-amber-200 bg-amber-50'
              : 'border-emerald-200 bg-emerald-50'"
        >
          <!-- Pool name + queue badge -->
          <div class="flex items-center justify-between gap-2">
            <div class="flex items-center gap-2 min-w-0">
              <Server class="w-3.5 h-3.5 shrink-0"
                :class="pool.workers_total === 0 ? 'text-gray-400' : 'text-gray-600'" />
              <span class="text-sm font-medium text-gray-800 truncate">{{ pool.name }}</span>
            </div>
            <code class="text-[10px] bg-white border border-gray-200 px-1.5 py-0.5 rounded text-gray-500 shrink-0">
              {{ pool.queue }}
            </code>
          </div>

          <!-- Metrics row -->
          <div class="flex items-center gap-3 text-xs flex-wrap">
            <!-- Online indicator -->
            <span class="flex items-center gap-1"
              :class="pool.workers_total === 0 ? 'text-gray-400' : 'text-emerald-700'">
              <span class="w-1.5 h-1.5 rounded-full inline-block"
                :class="pool.workers_total === 0 ? 'bg-gray-300' : 'bg-emerald-500'" />
              {{ pool.workers_total }}
              {{ pool.workers_total === 1 ? 'worker' : 'workers' }}
            </span>

            <!-- Slot usage: active / capacity -->
            <span class="flex items-center gap-1"
              :class="pool.tasks_active > 0 ? 'text-blue-700' : 'text-gray-400'">
              <Activity class="w-3 h-3" />
              {{ pool.tasks_active }}&thinsp;/&thinsp;{{ pool.capacity }} slots
            </span>
          </div>

          <!-- Capacity bar -->
          <div v-if="pool.capacity > 0" class="mt-2">
            <div class="h-1.5 w-full rounded-full bg-gray-200 overflow-hidden">
              <div
                class="h-full rounded-full transition-all duration-500"
                :class="pool.tasks_active === 0
                  ? 'bg-gray-300'
                  : pool.tasks_active >= pool.capacity
                    ? 'bg-red-500'
                    : pool.tasks_active / pool.capacity > 0.7
                      ? 'bg-amber-400'
                      : 'bg-emerald-500'"
                :style="{ width: `${Math.min((pool.tasks_active / pool.capacity) * 100, 100)}%` }"
              />
            </div>
            <p class="text-[10px] text-gray-400 mt-0.5 text-right">
              {{ pool.capacity - pool.tasks_active }} free
            </p>
          </div>
        </div>
      </div>

      <p v-else class="text-sm text-gray-400 text-center py-4">No worker pools configured.</p>
    </div>

    <!-- ── Projects grid ── -->
    <h2 class="text-sm font-semibold text-gray-700 mb-3">Projects</h2>
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
