<script setup lang="ts">
import { computed } from 'vue'

export interface GraphNode {
  node_id: string
  node_type?: string
  label: string
  template_name: string
  template_id?: string | null
  on_success: string[]
  on_failure: string[]
  on_always: string[]
  // run view extras
  status?: string
  task_id?: string
}

const props = defineProps<{
  nodes: GraphNode[]
  projectId?: string
}>()

// ── Layout constants ──────────────────────────────────────────────────────
const NW = 200      // node width
const NH = 72       // node height
const HGAP = 80     // horizontal gap between columns
const VGAP = 36     // vertical gap between nodes in same column
const PAD = 40      // canvas padding
const LEGEND_W = 160 // reserved column on the far right for the legend

// ── Layer assignment (longest-path from roots) ────────────────────────────
const layers = computed(() => {
  const ids = new Set(props.nodes.map(n => n.node_id))
  const edges: [string, string][] = []
  for (const n of props.nodes) {
    for (const t of [...n.on_success, ...n.on_failure, ...n.on_always]) {
      if (ids.has(t)) edges.push([n.node_id, t])
    }
  }
  const map = new Map<string, number>()
  for (const n of props.nodes) map.set(n.node_id, 0)

  // Iterate until stable (handles DAGs; bounded to prevent cycle loops)
  let changed = true
  for (let i = 0; i < props.nodes.length + 1 && changed; i++) {
    changed = false
    for (const [src, tgt] of edges) {
      const next = (map.get(src) ?? 0) + 1
      if (next > (map.get(tgt) ?? 0)) { map.set(tgt, next); changed = true }
    }
  }
  return map
})

// ── Position map ──────────────────────────────────────────────────────────
const layout = computed(() => {
  const byLayer = new Map<number, string[]>()
  for (const n of props.nodes) {
    const l = layers.value.get(n.node_id) ?? 0
    if (!byLayer.has(l)) byLayer.set(l, [])
    byLayer.get(l)!.push(n.node_id)
  }

  const maxLayer = props.nodes.length ? Math.max(...layers.value.values()) : 0
  const maxCount = props.nodes.length
    ? Math.max(...[...byLayer.values()].map(v => v.length))
    : 1

  const nodesAreaW = (maxLayer + 1) * (NW + HGAP) - HGAP + PAD * 2
  const svgW = nodesAreaW + LEGEND_W
  const svgH = maxCount * (NH + VGAP) - VGAP + PAD * 2

  const pos = new Map<string, { x: number; y: number }>()

  for (const [layer, nodeIds] of byLayer) {
    const count = nodeIds.length
    const totalH = count * NH + (count - 1) * VGAP
    const startY = PAD + (svgH - PAD * 2 - totalH) / 2

    nodeIds.forEach((id, i) => {
      pos.set(id, {
        x: PAD + layer * (NW + HGAP),
        y: startY + i * (NH + VGAP),
      })
    })
  }

  return { pos, nodesAreaW, svgW: Math.max(svgW, 260 + LEGEND_W), svgH: Math.max(svgH, NH + PAD * 2) }
})

// ── Edges ─────────────────────────────────────────────────────────────────
interface Edge { src: string; tgt: string; type: 'success' | 'failure' | 'always'; idx: number; total: number }

const edges = computed<Edge[]>(() => {
  const result: Edge[] = []
  for (const n of props.nodes) {
    const pairCount = new Map<string, number>()

    const push = (targets: string[], type: Edge['type']) => {
      for (const t of targets) {
        if (!layout.value.pos.has(t)) continue
        const key = `${n.node_id}→${t}`
        pairCount.set(key, (pairCount.get(key) ?? 0) + 1)
        result.push({ src: n.node_id, tgt: t, type, idx: 0, total: 0 })
      }
    }
    push(n.on_success, 'success')
    push(n.on_failure, 'failure')
    push(n.on_always, 'always')
  }

  // Assign per-pair index for offset separation
  const pairTypes = new Map<string, number>()
  for (const e of result) {
    const key = `${e.src}→${e.tgt}`
    e.idx = pairTypes.get(key) ?? 0
    pairTypes.set(key, e.idx + 1)
  }
  const pairTotal = new Map<string, number>()
  for (const e of result) {
    const key = `${e.src}→${e.tgt}`
    pairTotal.set(key, (pairTotal.get(key) ?? 0) + 1)
  }
  for (const e of result) {
    e.total = pairTotal.get(`${e.src}→${e.tgt}`) ?? 1
  }

  return result
})

const EDGE_COLOR = { success: '#22c55e', failure: '#ef4444', always: '#94a3b8' }
const MARKER_ID = { success: 'wg-arrow-success', failure: 'wg-arrow-failure', always: 'wg-arrow-always' }

function edgePath(e: Edge): string {
  const sp = layout.value.pos.get(e.src)
  const tp = layout.value.pos.get(e.tgt)
  if (!sp || !tp) return ''

  // Vertical offset to separate parallel edges
  const spread = 12
  const offset = e.total === 1 ? 0 : (e.idx - (e.total - 1) / 2) * spread

  const sx = sp.x + NW
  const sy = sp.y + NH / 2 + offset
  const tx = tp.x
  const ty = tp.y + NH / 2 + offset
  const cpX = (sx + tx) / 2

  return `M ${sx} ${sy} C ${cpX} ${sy}, ${cpX} ${ty}, ${tx} ${ty}`
}

// ── Node styling ──────────────────────────────────────────────────────────
const STATUS_FILL: Record<string, string> = {
  pending: '#f8fafc', running: '#eff6ff', success: '#f0fdf4',
  error: '#fef2f2', skipped: '#f8fafc', stopped: '#fff7ed',
  waiting_approval: '#fffbeb',
}
const STATUS_STROKE: Record<string, string> = {
  pending: '#cbd5e1', running: '#3b82f6', success: '#22c55e',
  error: '#ef4444', skipped: '#e2e8f0', stopped: '#f97316',
  waiting_approval: '#f59e0b',
}
const STATUS_LABEL: Record<string, string> = {
  pending: 'Pending', running: 'Running', success: 'Success',
  error: 'Error', skipped: 'Skipped', stopped: 'Stopped',
  waiting_approval: 'Approval',
}
const STATUS_TEXT: Record<string, string> = {
  pending: '#94a3b8', running: '#3b82f6', success: '#16a34a',
  error: '#dc2626', skipped: '#94a3b8', stopped: '#ea580c',
  waiting_approval: '#d97706',
}

const ACTION_NODE_TYPES_GRAPH = new Set(['list_generator', 'pdf_generator', 'send_mail', 'transfer_file'])
function isQuestion(n: GraphNode) { return n.node_type === 'question' }
function isRemoteApproval(n: GraphNode) { return n.node_type === 'remote_approval' }
function isAction(n: GraphNode) { return ACTION_NODE_TYPES_GRAPH.has(n.node_type ?? '') }
function nodeFill(n: GraphNode) {
  if (isQuestion(n) && !n.status) return '#fffbeb'
  if (isRemoteApproval(n) && !n.status) return '#eef2ff'
  if (isAction(n) && !n.status) return '#f5f3ff'
  return n.status ? (STATUS_FILL[n.status] ?? '#f8fafc') : '#ffffff'
}
function nodeStroke(n: GraphNode) {
  if (isQuestion(n) && !n.status) return '#f59e0b'
  if (isRemoteApproval(n) && !n.status) return '#6366f1'
  if (isAction(n) && !n.status) return '#7c3aed'
  return n.status ? (STATUS_STROKE[n.status] ?? '#cbd5e1') : '#e2e8f0'
}
function nodeStrokeW(n: GraphNode) {
  return (n.status === 'running' || n.status === 'waiting_approval') ? 2.5 : 1.5
}

function displayName(n: GraphNode): string {
  const s = n.label || n.template_name || 'Unnamed'
  return s.length > 22 ? s.slice(0, 21) + '…' : s
}
function displaySub(n: GraphNode): string {
  if (!n.label || n.label === n.template_name) return ''
  const s = n.template_name || ''
  return s.length > 26 ? s.slice(0, 25) + '…' : s
}

// Task link for run view
function taskUrl(n: GraphNode): string | null {
  if (!props.projectId || !n.task_id) return null
  return `/projects/${props.projectId}/tasks/${n.task_id}`
}
</script>

<template>
  <div class="overflow-auto rounded-xl bg-slate-50 border border-gray-200 select-none">
    <div v-if="nodes.length === 0" class="flex items-center justify-center py-10 text-gray-400 text-sm">
      No nodes defined yet.
    </div>

    <svg v-else
      :width="layout.svgW"
      :height="layout.svgH"
      class="block"
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <!-- Arrowhead markers per edge type -->
        <marker v-for="type in (['success','failure','always'] as const)" :key="type"
          :id="MARKER_ID[type]"
          viewBox="0 0 10 10" refX="9" refY="5"
          markerWidth="5" markerHeight="5" orient="auto-start-reverse">
          <path d="M 0 1 L 9 5 L 0 9 z" :fill="EDGE_COLOR[type]" />
        </marker>

        <!-- Running pulse animation clip -->
        <style>
          @keyframes wg-dash { to { stroke-dashoffset: -24; } }
          .wg-running { animation: wg-dash 0.8s linear infinite; }
        </style>
      </defs>

      <!-- ── Edges ── -->
      <g>
        <path
          v-for="(e, i) in edges" :key="i"
          :d="edgePath(e)"
          :stroke="EDGE_COLOR[e.type]"
          stroke-width="2"
          fill="none"
          :marker-end="`url(#${MARKER_ID[e.type]})`"
          opacity="0.85"
        />
      </g>

      <!-- ── Nodes ── -->
      <g v-for="n in nodes" :key="n.node_id"
        :transform="`translate(${layout.pos.get(n.node_id)?.x ?? 0}, ${layout.pos.get(n.node_id)?.y ?? 0})`"
        :class="taskUrl(n) ? 'cursor-pointer' : ''"
        @click="taskUrl(n) ? $router.push(taskUrl(n)!) : undefined"
      >
        <!-- Shadow -->
        <rect :width="NW" :height="NH" rx="10" fill="rgba(0,0,0,0.04)" transform="translate(2,3)" />

        <!-- Node background -->
        <rect :width="NW" :height="NH" rx="10"
          :fill="nodeFill(n)"
          :stroke="nodeStroke(n)"
          :stroke-width="nodeStrokeW(n)"
          :stroke-dasharray="n.status === 'running' ? '6 3' : 'none'"
          :class="n.status === 'running' ? 'wg-running' : ''"
        />

        <!-- Status badge (top-right) -->
        <g v-if="n.status">
          <rect x="118" y="6" width="76" height="18" rx="9"
            :fill="STATUS_STROKE[n.status] ?? '#94a3b8'"
            opacity="0.15"
          />
          <text x="156" y="18.5" text-anchor="middle" font-size="10" font-weight="600"
            :fill="STATUS_TEXT[n.status] ?? '#64748b'" font-family="system-ui,sans-serif">
            {{ STATUS_LABEL[n.status] ?? n.status }}
          </text>
        </g>

        <!-- Question node: amber question mark badge -->
        <g v-if="isQuestion(n)">
          <circle cx="20" cy="NH / 2" :cy="NH / 2" r="10"
            fill="#fef3c7" stroke="#f59e0b" stroke-width="1.5" />
          <text x="20" :y="NH / 2 + 4" text-anchor="middle"
            font-size="12" font-weight="700" fill="#d97706"
            font-family="system-ui,sans-serif">?</text>
        </g>

        <!-- Remote approval node: indigo mail badge -->
        <g v-if="isRemoteApproval(n)">
          <circle cx="20" :cy="NH / 2" r="10"
            fill="#eef2ff" stroke="#6366f1" stroke-width="1.5" />
          <text x="20" :y="NH / 2 + 4" text-anchor="middle"
            font-size="11" font-weight="700" fill="#6366f1"
            font-family="system-ui,sans-serif">✉</text>
        </g>

        <!-- Action node: violet lightning badge -->
        <g v-if="isAction(n)">
          <circle cx="20" :cy="NH / 2" r="10"
            fill="#f5f3ff" stroke="#7c3aed" stroke-width="1.5" />
          <text x="20" :y="NH / 2 + 4" text-anchor="middle"
            font-size="11" font-weight="700" fill="#7c3aed"
            font-family="system-ui,sans-serif">⚡</text>
        </g>

        <!-- Node name (main) -->
        <text
          :x="(isQuestion(n) || isRemoteApproval(n) || isAction(n)) ? NW / 2 + 8 : NW / 2" :y="n.status ? 40 : NH / 2 - 4"
          text-anchor="middle" font-size="13" font-weight="600"
          :fill="isQuestion(n) ? '#92400e' : isRemoteApproval(n) ? '#3730a3' : isAction(n) ? '#4c1d95' : '#1e293b'"
          font-family="system-ui,sans-serif">
          {{ displayName(n) }}
        </text>

        <!-- Sub-label for task nodes -->
        <text v-if="!isQuestion(n) && !isRemoteApproval(n) && displaySub(n)"
          :x="NW / 2" :y="n.status ? 55 : NH / 2 + 13"
          text-anchor="middle" font-size="10"
          fill="#94a3b8" font-family="system-ui,sans-serif">
          {{ displaySub(n) }}
        </text>

        <!-- "Awaits approval" sub-label for question nodes -->
        <text v-else-if="isQuestion(n)"
          :x="NW / 2 + 8" :y="n.status ? 55 : NH / 2 + 13"
          text-anchor="middle" font-size="10" font-style="italic"
          fill="#d97706" font-family="system-ui,sans-serif">
          Awaits approval
        </text>

        <!-- "Remote" sub-label for remote_approval nodes -->
        <text v-else-if="isRemoteApproval(n)"
          :x="NW / 2 + 8" :y="n.status ? 55 : NH / 2 + 13"
          text-anchor="middle" font-size="10" font-style="italic"
          fill="#6366f1" font-family="system-ui,sans-serif">
          Remote approval
        </text>

        <!-- "no template" placeholder for task nodes -->
        <text v-else-if="!isQuestion(n) && !isRemoteApproval(n) && !n.template_name && !n.label"
          :x="NW / 2" :y="n.status ? 55 : NH / 2 + 13"
          text-anchor="middle" font-size="10" font-style="italic"
          fill="#cbd5e1" font-family="system-ui,sans-serif">
          no template
        </text>

        <!-- Click hint for run view -->
        <title v-if="taskUrl(n)">Open task log →</title>
      </g>

      <!-- ── Legend — always in the reserved right column ── -->
      <g :transform="`translate(${layout.nodesAreaW + 8}, 12)`">
        <rect width="140" height="62" rx="6" fill="white" stroke="#e2e8f0" stroke-width="1" opacity="0.9"/>
        <text x="8" y="16" font-size="9" font-weight="700" fill="#94a3b8"
          font-family="system-ui,sans-serif" letter-spacing="0.8">EDGE TYPE</text>
        <line v-for="(item, i) in [
          { label: 'on_success', color: '#22c55e' },
          { label: 'on_failure', color: '#ef4444' },
          { label: 'on_always',  color: '#94a3b8' },
        ]" :key="i"
          x1="8" :y1="28 + i * 14" x2="28" :y2="28 + i * 14"
          :stroke="item.color" stroke-width="2.5"
        />
        <text v-for="(item, i) in [
          { label: 'on_success', color: '#22c55e' },
          { label: 'on_failure', color: '#ef4444' },
          { label: 'on_always',  color: '#94a3b8' },
        ]" :key="'t' + i"
          x="34" :y="32 + i * 14" font-size="10" :fill="item.color"
          font-family="system-ui,sans-serif" font-weight="500">
          {{ item.label }}
        </text>
      </g>
    </svg>
  </div>
</template>
