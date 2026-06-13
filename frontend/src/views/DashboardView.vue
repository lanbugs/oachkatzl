<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useProjectsStore } from '@/stores/projects'
import { RouterLink } from 'vue-router'
import { FolderKanban } from 'lucide-vue-next'
import api from '@/api/client'

const auth = useAuthStore()
const projects = useProjectsStore()

interface DayStats { date: string; success: number; error: number }
const stats = ref<DayStats[]>([])

onMounted(async () => {
  if (!auth.user) await auth.fetchMe()
  await Promise.all([
    projects.fetchProjects(),
    api.get('/dashboard/task-stats').then(r => { stats.value = r.data }),
  ])
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
