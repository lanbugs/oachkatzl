<script setup lang="ts">
import { ref, computed, watch, nextTick, markRaw } from 'vue'
import {
  VueFlow,
  Panel,
  useVueFlow,
  type NodeChange,
  type EdgeChange,
  Position,
} from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import '@vue-flow/core/dist/style.css'

import StartNodeComp from './workflow/StartNode.vue'
import TemplateNodeComp from './workflow/TemplateNode.vue'
import ConditionEdgeComp from './workflow/ConditionEdge.vue'
import { X, Trash2, LayoutDashboard } from 'lucide-vue-next'

// ── Types ─────────────────────────────────────────────────────────────────

export interface WNode {
  node_id: string
  label: string
  template_id: string | null
  on_success: string[]
  on_failure: string[]
  on_always: string[]
  position_x: number
  position_y: number
}

interface Template {
  id: string
  name: string
}

type Condition = 'success' | 'failure' | 'always'

// ── Props / emits ─────────────────────────────────────────────────────────

const props = defineProps<{
  nodes: WNode[]
  templates: Template[]
}>()

const emit = defineEmits<{
  'update:nodes': [nodes: WNode[]]
}>()

// ── VueFlow state (use any[] to avoid VueFlow internal type complexity) ───

// Unique ID per canvas instance so useVueFlow can scope its store
const flowId = 'wf-canvas-' + Math.random().toString(36).slice(2, 8)
const { fitView } = useVueFlow({ id: flowId })

// Cast as any to avoid fighting VueFlow's strict internal NodeComponent / EdgeComponent types
const nodeTypes = {
  start: markRaw(StartNodeComp),
  template: markRaw(TemplateNodeComp),
} as any
const edgeTypes = { condition: markRaw(ConditionEdgeComp) } as any

// Using any[] avoids fighting VueFlow's internal GraphNode/GraphEdge types
const vfNodes = ref<any[]>([])
const vfEdges = ref<any[]>([])

// ── Add-node modal state ───────────────────────────────────────────────────

const showAddModal = ref(false)
const pendingEdge = ref<{ sourceId: string; condition: Condition } | null>(null)
const modalTemplateId = ref('')
const modalLabel = ref('')

// ── Link-nodes modal state ─────────────────────────────────────────────────

const showLinkModal = ref(false)
const linkSourceId = ref('')
const linkCondition = ref<Condition>('success')
const linkTargetId = ref('')

const linkTargetOptions = computed(() =>
  vfNodes.value
    .filter((n: any) => n.id !== '__start__' && n.id !== linkSourceId.value)
    .map((n: any) => ({
      id: n.id as string,
      label: (n.data.label || n.data.template_name || n.id.slice(-8)) as string,
    }))
)

// ── Selection ──────────────────────────────────────────────────────────────

const selectedNodeId = ref<string | null>(null)
const selectedVfNode = ref<any>(null)

function updateSelectedVfNode() {
  selectedVfNode.value = selectedNodeId.value
    ? vfNodes.value.find(n => n.id === selectedNodeId.value) ?? null
    : null
}

// ── Helpers ────────────────────────────────────────────────────────────────

function genId(): string {
  return Date.now().toString(36) + Math.random().toString(36).slice(2)
}

function edgeId(src: string, tgt: string, cond: Condition): string {
  return `${src}__${cond}__${tgt}`
}

function maxOf(arr: number[]): number {
  return arr.reduce((a, b) => (b > a ? b : a), 0)
}

/** Longest-path layer assignment for auto-layout */
function autoLayout(nodes: WNode[]): Map<string, { x: number; y: number }> {
  const NW = 192, NH = 72, HGAP = 128, VGAP = 48, PAD_X = 360, PAD_Y = 60

  const layerMap = new Map<string, number>()
  for (const n of nodes) layerMap.set(n.node_id, 0)

  let changed = true
  for (let i = 0; i < nodes.length + 1 && changed; i++) {
    changed = false
    for (const n of nodes) {
      for (const t of [...n.on_success, ...n.on_failure, ...n.on_always]) {
        const next = (layerMap.get(n.node_id) ?? 0) + 1
        if (next > (layerMap.get(t) ?? 0)) { layerMap.set(t, next); changed = true }
      }
    }
  }

  const byLayer = new Map<number, string[]>()
  for (const n of nodes) {
    const l = layerMap.get(n.node_id) ?? 0
    if (!byLayer.has(l)) byLayer.set(l, [])
    byLayer.get(l)!.push(n.node_id)
  }

  const colCounts = [...byLayer.values()].map(v => v.length)
  const maxCount = colCounts.length ? maxOf(colCounts) : 1
  const totalH = maxCount * (NH + VGAP) - VGAP + PAD_Y * 2

  const pos = new Map<string, { x: number; y: number }>()
  for (const [layer, ids] of byLayer) {
    const count = ids.length
    const colH = count * NH + (count - 1) * VGAP
    const startY = (totalH - colH) / 2
    ids.forEach((id, i) => {
      pos.set(id, { x: PAD_X + layer * (NW + HGAP), y: startY + i * (NH + VGAP) })
    })
  }
  return pos
}

/** Vertical center of all non-start nodes for the START node position */
function startMidY(): number {
  const nonStart = vfNodes.value.filter((n: any) => n.id !== '__start__')
  if (nonStart.length === 0) return 200
  const ys = nonStart.map((n: any) => n.position.y)
  const minY = ys.reduce((a: number, b: number) => (b < a ? b : a), ys[0])
  const maxY = ys.reduce((a: number, b: number) => (b > a ? b : a), ys[0])
  return (minY + maxY) / 2 + 36
}

/** Rebuild synthetic __start__ → root-node edges */
function rebuildStartEdges() {
  // Root nodes = nodes with no incoming edges from non-start sources
  const allIds = new Set(vfNodes.value.filter((n: any) => n.id !== '__start__').map((n: any) => n.id))
  const referenced = new Set<string>()
  for (const e of vfEdges.value) {
    if (e.source !== '__start__') referenced.add(e.target)
  }
  const roots = new Set([...allIds].filter(id => !referenced.has(id)))

  // Only remove start-edges that point to non-roots (stale) — keep valid ones in place
  // so VueFlow doesn't lose track of edges that were just added with the same id.
  vfEdges.value = vfEdges.value.filter((e: any) =>
    e.source !== '__start__' || roots.has(e.target)
  )

  // Add start-edges for roots that don't have one yet
  const covered = new Set(vfEdges.value.filter((e: any) => e.source === '__start__').map((e: any) => e.target))
  for (const rootId of roots) {
    if (!covered.has(rootId)) {
      vfEdges.value = [...vfEdges.value, {
        id: `__start____always__${rootId}`,
        source: '__start__',
        target: rootId,
        type: 'condition',
        data: { condition: 'always' },
        deletable: false,
        updatable: false,
        focusable: false,
      }]
    }
  }

  // Reposition start node to vertical center of graph
  vfNodes.value = vfNodes.value.map((n: any) =>
    n.id === '__start__' ? { ...n, position: { x: 40, y: startMidY() } } : n
  )
}

/** Convert WNode[] to VueFlow nodes + edges */
function toVF(nodes: WNode[]) {
  const needsLayout = nodes.length > 0 && nodes.every(n => n.position_x === 0 && n.position_y === 0)
  const posMap = needsLayout ? autoLayout(nodes) : null

  const referenced = new Set<string>()
  for (const n of nodes) {
    for (const id of [...n.on_success, ...n.on_failure, ...n.on_always]) referenced.add(id)
  }
  const roots = new Set(nodes.filter(n => !referenced.has(n.node_id)).map(n => n.node_id))

  // START Y = vertical center of the entire graph (not just roots)
  const allPositions = nodes.map(n => posMap ? (posMap.get(n.node_id)?.y ?? n.position_y) : n.position_y)
  const startY = allPositions.length > 0
    ? (allPositions.reduce((a, b) => (b < a ? b : a), allPositions[0])
       + allPositions.reduce((a, b) => (b > a ? b : a), allPositions[0])) / 2 + 36
    : 200

  const vfN: any[] = [
    {
      id: '__start__',
      type: 'start',
      position: { x: 40, y: startY },
      // Pass callback via data — more reliable than provide/inject through VueFlow internals
      data: { onAddNode: openAddModal },
      deletable: false,
      selectable: false,
      focusable: false,
    },
    ...nodes.map(n => {
      const pos = posMap ? posMap.get(n.node_id) ?? { x: 400, y: 200 } : { x: n.position_x, y: n.position_y }
      const nodeId = n.node_id
      return {
        id: nodeId,
        type: 'template',
        position: pos,
        data: {
          label: n.label,
          template_id: n.template_id,
          template_name: props.templates.find(t => t.id === n.template_id)?.name ?? '',
          onAddNode: (cond: Condition) => openAddModal(nodeId, cond),
          onLinkNode: () => openLinkModal(nodeId),
        },
        deletable: true,
      }
    }),
  ]

  const vfE: any[] = [
    ...[...roots].map(rootId => ({
      id: `__start____always__${rootId}`,
      source: '__start__',
      target: rootId,
      type: 'condition',
      data: { condition: 'always' },
      deletable: false,
      updatable: false,
      focusable: false,
    })),
    ...nodes.flatMap(n => [
      ...n.on_success.map(t => ({ id: edgeId(n.node_id, t, 'success'), source: n.node_id, target: t, type: 'condition', data: { condition: 'success' }, deletable: true })),
      ...n.on_failure.map(t => ({ id: edgeId(n.node_id, t, 'failure'), source: n.node_id, target: t, type: 'condition', data: { condition: 'failure' }, deletable: true })),
      ...n.on_always.map(t => ({ id: edgeId(n.node_id, t, 'always'),   source: n.node_id, target: t, type: 'condition', data: { condition: 'always'  }, deletable: true })),
    ]),
  ]

  return { nodes: vfN, edges: vfE }
}

/** Convert current VueFlow state back to WNode[] */
function fromVF(): WNode[] {
  const result: WNode[] = []
  for (const vn of vfNodes.value) {
    if (vn.id === '__start__') continue
    const node: WNode = {
      node_id: vn.id,
      label: vn.data.label ?? '',
      template_id: vn.data.template_id ?? null,
      on_success: [],
      on_failure: [],
      on_always: [],
      position_x: vn.position.x,
      position_y: vn.position.y,
    }
    for (const e of vfEdges.value) {
      if (e.source === '__start__' || e.source !== vn.id) continue
      const cond = (e.data?.condition ?? 'always') as Condition
      if (cond === 'success') node.on_success.push(e.target)
      else if (cond === 'failure') node.on_failure.push(e.target)
      else node.on_always.push(e.target)
    }
    result.push(node)
  }
  return result
}

// ── Reactivity: sync props → VF ───────────────────────────────────────────

let skipNextWatch = false

watch(
  () => props.nodes,
  (nodes) => {
    if (skipNextWatch) { skipNextWatch = false; return }
    const { nodes: vn, edges: ve } = toVF(nodes)
    vfNodes.value = vn
    vfEdges.value = ve
    selectedNodeId.value = null
    selectedVfNode.value = null
  },
  { immediate: true }
)

watch(
  () => props.templates,
  (templates) => {
    vfNodes.value = vfNodes.value.map((vn: any) => {
      if (vn.id === '__start__') return vn
      const tmplName = templates.find(t => t.id === vn.data.template_id)?.name ?? ''
      if (tmplName === vn.data.template_name) return vn
      return { ...vn, data: { ...vn.data, template_name: tmplName } }
    })
  }
)

function emitUpdate() {
  skipNextWatch = true
  emit('update:nodes', fromVF())
}

// ── VueFlow event handlers ─────────────────────────────────────────────────

function onNodesChange(changes: NodeChange[]) {
  // v-model handles the actual state update; we just react to specific events
  const positionEnd = changes.some(c => c.type === 'position' && !(c as any).dragging)
  if (positionEnd) nextTick(() => emitUpdate())
}

function onEdgesChange(changes: EdgeChange[]) {
  const removed = changes.some(c => c.type === 'remove')
  if (removed) {
    nextTick(() => {
      rebuildStartEdges()
      emitUpdate()
    })
  }
}

function onNodeClick(e: any) {
  const nodeId: string = e.node?.id ?? e.id
  if (!nodeId || nodeId === '__start__') return
  selectedNodeId.value = nodeId
  updateSelectedVfNode()
}

function onPaneClick() {
  selectedNodeId.value = null
  selectedVfNode.value = null
}

// ── Toolbar → Modal → Add node ─────────────────────────────────────────────

function openAddModal(sourceId: string, condition: Condition) {
  pendingEdge.value = { sourceId, condition }
  modalTemplateId.value = ''
  modalLabel.value = ''
  showAddModal.value = true
}

function confirmAddNode() {
  if (!pendingEdge.value) return
  const { sourceId, condition } = pendingEdge.value
  const newId = genId()

  showAddModal.value = false
  pendingEdge.value = null

  // Determine new node position relative to source
  const sourceVfNode = vfNodes.value.find((n: any) => n.id === sourceId)
  const srcPos = sourceVfNode?.position ?? { x: 80, y: 200 }
  const existingFromSource = vfEdges.value.filter((e: any) => e.source === sourceId).length
  const newPos = { x: srcPos.x + 320, y: srcPos.y + existingFromSource * 100 }

  // Build the complete updated WNode list with the new edge already wired in.
  // This mirrors the initial-load path (toVF receives both nodes AND their edges
  // at the same time), which is the only way to avoid VueFlow's handle-registration
  // race condition for brand-new nodes.
  const updatedWNodes = fromVF()

  if (sourceId !== '__start__') {
    const src = updatedWNodes.find(n => n.node_id === sourceId)
    if (src) {
      if (condition === 'success') src.on_success.push(newId)
      else if (condition === 'failure') src.on_failure.push(newId)
      else src.on_always.push(newId)
    }
  }
  // When sourceId === '__start__', the new node has no incoming edges → it
  // becomes a root, and toVF() adds the __start__ → newId edge automatically.

  updatedWNodes.push({
    node_id: newId,
    label: modalLabel.value,
    template_id: modalTemplateId.value || null,
    on_success: [],
    on_failure: [],
    on_always: [],
    position_x: newPos.x,
    position_y: newPos.y,
  })

  const { nodes: vfN, edges: vfE } = toVF(updatedWNodes)
  vfNodes.value = vfN
  vfEdges.value = vfE

  selectedNodeId.value = newId
  updateSelectedVfNode()
  emitUpdate()
}

// ── Link existing nodes ────────────────────────────────────────────────────

function openLinkModal(sourceId: string) {
  linkSourceId.value = sourceId
  linkCondition.value = 'success'
  linkTargetId.value = ''
  showLinkModal.value = true
}

function confirmLinkNodes() {
  if (!linkTargetId.value) return
  const updatedWNodes = fromVF()
  const src = updatedWNodes.find(n => n.node_id === linkSourceId.value)
  if (!src) { showLinkModal.value = false; return }

  // Prevent duplicate edge (same source → condition → target)
  const isDuplicate =
    (linkCondition.value === 'success' && src.on_success.includes(linkTargetId.value)) ||
    (linkCondition.value === 'failure' && src.on_failure.includes(linkTargetId.value)) ||
    (linkCondition.value === 'always'  && src.on_always.includes(linkTargetId.value))

  if (!isDuplicate) {
    if (linkCondition.value === 'success') src.on_success.push(linkTargetId.value)
    else if (linkCondition.value === 'failure') src.on_failure.push(linkTargetId.value)
    else src.on_always.push(linkTargetId.value)
  }

  showLinkModal.value = false
  // Atomic rebuild — same pattern as confirmAddNode to avoid VueFlow edge-ID cache issues
  const { nodes: vfN, edges: vfE } = toVF(updatedWNodes)
  vfNodes.value = vfN
  vfEdges.value = vfE
  emitUpdate()
}

// ── Auto-layout ────────────────────────────────────────────────────────────

function applyAutoLayout() {
  const currentNodes = fromVF()
  if (currentNodes.length === 0) return

  const posMap = autoLayout(currentNodes)

  vfNodes.value = vfNodes.value.map((n: any) => {
    if (n.id === '__start__') return n  // repositioned by rebuildStartEdges below
    const newPos = posMap.get(n.id)
    return newPos ? { ...n, position: newPos } : n
  })

  rebuildStartEdges()
  emitUpdate()
  // Wait for Vue to apply the new positions before fitting the viewport
  nextTick(() => fitView({ padding: 0.12 }))
}

// ── Edit panel ─────────────────────────────────────────────────────────────

function updateLabel(label: string) {
  if (!selectedNodeId.value) return
  vfNodes.value = vfNodes.value.map((n: any) =>
    n.id === selectedNodeId.value ? { ...n, data: { ...n.data, label } } : n
  )
  updateSelectedVfNode()
  emitUpdate()
}

function updateTemplate(templateId: string) {
  if (!selectedNodeId.value) return
  const tmplName = props.templates.find(t => t.id === templateId)?.name ?? ''
  vfNodes.value = vfNodes.value.map((n: any) =>
    n.id === selectedNodeId.value
      ? { ...n, data: { ...n.data, template_id: templateId || null, template_name: tmplName } }
      : n
  )
  updateSelectedVfNode()
  emitUpdate()
}

function deleteSelectedNode() {
  if (!selectedNodeId.value) return
  const id = selectedNodeId.value
  vfNodes.value = vfNodes.value.filter((n: any) => n.id !== id)
  vfEdges.value = vfEdges.value.filter((e: any) => e.source !== id && e.target !== id)
  rebuildStartEdges()
  selectedNodeId.value = null
  selectedVfNode.value = null
  emitUpdate()
}
</script>

<template>
  <div>
    <!-- Canvas -->
    <div
      class="w-full rounded-xl border border-gray-200 bg-slate-50 overflow-hidden"
      style="height: 500px"
    >
      <VueFlow
        :id="flowId"
        v-model:nodes="vfNodes"
        v-model:edges="vfEdges"
        :node-types="nodeTypes"
        :edge-types="edgeTypes"
        :nodes-connectable="false"
        :fit-view-on-init="true"
        :min-zoom="0.2"
        :max-zoom="2"
        :default-viewport="{ zoom: 1, x: 0, y: 0 }"
        @nodes-change="onNodesChange"
        @edges-change="onEdgesChange"
        @node-click="onNodeClick"
        @pane-click="onPaneClick"
        class="h-full"
      >
        <Background pattern-color="#e2e8f0" :gap="24" />

        <Panel position="top-right">
          <button
            type="button"
            @click="applyAutoLayout"
            class="flex items-center gap-1.5 bg-white hover:bg-gray-50 border border-gray-200 text-gray-600 hover:text-gray-800 text-xs font-medium px-2.5 py-1.5 rounded-lg shadow-sm transition-colors"
            title="Auto-arrange nodes"
          >
            <LayoutDashboard class="w-3.5 h-3.5" />
            Auto-layout
          </button>
        </Panel>
      </VueFlow>
    </div>

    <!-- Edit panel for selected node -->
    <Transition name="panel">
      <div v-if="selectedVfNode" class="mt-3 bg-white rounded-xl border border-gray-200 p-4">
        <div class="flex items-center justify-between mb-3">
          <h4 class="text-sm font-semibold text-gray-700">
            Edit Node
            <span class="ml-1 text-xs font-mono text-gray-400">{{ selectedNodeId?.slice(-8) }}</span>
          </h4>
          <button type="button"
            @click="deleteSelectedNode"
            class="flex items-center gap-1 text-xs text-red-500 hover:text-red-700 transition-colors"
          >
            <Trash2 class="w-3.5 h-3.5" /> Delete node
          </button>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">Label</label>
            <input
              :value="selectedVfNode.data.label"
              @input="updateLabel(($event.target as HTMLInputElement).value)"
              type="text"
              class="w-full border border-gray-300 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              placeholder="Optional label"
            />
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">Template</label>
            <select
              :value="selectedVfNode.data.template_id ?? ''"
              @change="updateTemplate(($event.target as HTMLSelectElement).value)"
              class="w-full border border-gray-300 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 bg-white"
            >
              <option value="">— none —</option>
              <option v-for="t in templates" :key="t.id" :value="t.id">{{ t.name }}</option>
            </select>
          </div>
        </div>
      </div>
    </Transition>

    <!-- Link nodes modal -->
    <Teleport to="body">
      <div
        v-if="showLinkModal"
        class="fixed inset-0 z-50 flex items-center justify-center p-4"
        @click.self="showLinkModal = false"
      >
        <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" />
        <div class="relative bg-white rounded-2xl shadow-2xl w-full max-w-sm p-6">
          <div class="flex items-center justify-between mb-4">
            <h3 class="font-semibold text-gray-900">Link to existing node</h3>
            <button type="button" @click="showLinkModal = false" class="text-gray-400 hover:text-gray-600">
              <X class="w-5 h-5" />
            </button>
          </div>

          <div class="space-y-4">
            <div>
              <label class="block text-xs font-medium text-gray-600 mb-1">Target node</label>
              <select
                v-model="linkTargetId"
                class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 bg-white"
              >
                <option value="">— select node —</option>
                <option v-for="opt in linkTargetOptions" :key="opt.id" :value="opt.id">{{ opt.label }}</option>
              </select>
            </div>

            <div>
              <label class="block text-xs font-medium text-gray-600 mb-2">Condition</label>
              <div class="flex gap-2">
                <button
                  v-for="cond in (['success', 'failure', 'always'] as const)"
                  :key="cond"
                  type="button"
                  @click="linkCondition = cond"
                  class="flex-1 py-1.5 rounded-lg text-xs font-medium border transition-colors"
                  :class="{
                    'bg-green-500 border-green-500 text-white': cond === 'success' && linkCondition === cond,
                    'bg-red-500 border-red-500 text-white':     cond === 'failure' && linkCondition === cond,
                    'bg-slate-400 border-slate-400 text-white': cond === 'always'  && linkCondition === cond,
                    'bg-white border-gray-200 text-gray-500 hover:bg-gray-50': linkCondition !== cond,
                  }"
                >
                  {{ cond === 'success' ? '✓ Success' : cond === 'failure' ? '✗ Failure' : '→ Always' }}
                </button>
              </div>
            </div>
          </div>

          <div class="flex gap-3 mt-6">
            <button type="button"
              @click="confirmLinkNodes"
              :disabled="!linkTargetId"
              class="flex-1 bg-brand-600 hover:bg-brand-700 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
            >
              Link nodes
            </button>
            <button type="button"
              @click="showLinkModal = false"
              class="text-sm text-gray-500 hover:text-gray-700 px-4 py-2 rounded-lg border border-gray-200 hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Add node modal -->
    <Teleport to="body">
      <div
        v-if="showAddModal"
        class="fixed inset-0 z-50 flex items-center justify-center p-4"
        @click.self="showAddModal = false"
      >
        <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" />
        <div class="relative bg-white rounded-2xl shadow-2xl w-full max-w-sm p-6">
          <div class="flex items-center justify-between mb-4">
            <h3 class="font-semibold text-gray-900">Add node</h3>
            <button type="button" @click="showAddModal = false" class="text-gray-400 hover:text-gray-600">
              <X class="w-5 h-5" />
            </button>
          </div>

          <div class="space-y-4">
            <div class="flex items-center gap-2 text-sm">
              <span class="text-gray-500">Condition:</span>
              <span
                class="px-2 py-0.5 rounded font-medium text-xs"
                :class="{
                  'bg-green-100 text-green-700': pendingEdge?.condition === 'success',
                  'bg-red-100 text-red-700':     pendingEdge?.condition === 'failure',
                  'bg-slate-100 text-slate-600': pendingEdge?.condition === 'always',
                }"
              >
                {{
                  pendingEdge?.condition === 'success' ? '✓ On Success' :
                  pendingEdge?.condition === 'failure' ? '✗ On Failure' :
                  '→ Always'
                }}
              </span>
            </div>

            <div>
              <label class="block text-xs font-medium text-gray-600 mb-1">
                Template <span class="text-gray-400 font-normal">(optional)</span>
              </label>
              <select
                v-model="modalTemplateId"
                class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 bg-white"
              >
                <option value="">— none —</option>
                <option v-for="t in templates" :key="t.id" :value="t.id">{{ t.name }}</option>
              </select>
            </div>

            <div>
              <label class="block text-xs font-medium text-gray-600 mb-1">
                Label <span class="text-gray-400 font-normal">(optional)</span>
              </label>
              <input
                v-model="modalLabel"
                type="text"
                class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                placeholder="Custom node label"
                @keydown.enter="confirmAddNode"
              />
            </div>
          </div>

          <div class="flex gap-3 mt-6">
            <button type="button"
              @click="confirmAddNode"
              class="flex-1 bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
            >
              Add node
            </button>
            <button type="button"
              @click="showAddModal = false"
              class="text-sm text-gray-500 hover:text-gray-700 px-4 py-2 rounded-lg border border-gray-200 hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style>
/* Override VueFlow default node styling */
.vue-flow__node {
  background: transparent !important;
  border: none !important;
  padding: 0 !important;
  border-radius: 0 !important;
  box-shadow: none !important;
}
</style>

<style scoped>
.panel-enter-active, .panel-leave-active { transition: opacity 0.15s, transform 0.15s; }
.panel-enter-from, .panel-leave-to { opacity: 0; transform: translateY(-4px); }
</style>
