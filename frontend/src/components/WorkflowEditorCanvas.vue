<script lang="ts">
// Runtime exports must live in a plain <script> block — not in <script setup>
export const ACTION_NODE_TYPES = new Set<string>(['list_generator', 'pdf_generator', 'send_mail', 'transfer_file'])
</script>

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
import QuestionNodeComp from './workflow/QuestionNode.vue'
import RemoteApprovalNodeComp from './workflow/RemoteApprovalNode.vue'
import ActionNodeComp from './workflow/ActionNode.vue'
import ConditionEdgeComp from './workflow/ConditionEdge.vue'
import ListGeneratorConfigModal from './workflow/ListGeneratorConfigModal.vue'
import PdfGeneratorConfigModal from './workflow/PdfGeneratorConfigModal.vue'
import SendMailConfigModal from './workflow/SendMailConfigModal.vue'
import TransferFileConfigModal from './workflow/TransferFileConfigModal.vue'
import RemoteApprovalConfigModal from './workflow/RemoteApprovalConfigModal.vue'
import { X, Trash2, LayoutDashboard, HelpCircle, Play, Zap, Sheet, FileText, Mail, Upload, MailCheck } from 'lucide-vue-next'

// ── Types ─────────────────────────────────────────────────────────────────

export type ActionNodeType = 'list_generator' | 'pdf_generator' | 'send_mail' | 'transfer_file'
export type WNodeType = 'task' | 'question' | 'remote_approval' | ActionNodeType

const ACTION_NODE_META: Record<ActionNodeType, { label: string; icon: any }> = {
  list_generator: { label: 'List Generator', icon: Sheet },
  pdf_generator:  { label: 'PDF Generator',  icon: FileText },
  send_mail:      { label: 'Send Mail',       icon: Mail },
  transfer_file:  { label: 'Transfer File',   icon: Upload },
}

export interface WNode {
  node_id: string
  node_type: WNodeType
  slug: string
  label: string
  template_id: string | null
  action_config: Record<string, any>
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
  projectId: string
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
  question: markRaw(QuestionNodeComp),
  remote_approval: markRaw(RemoteApprovalNodeComp),
  action: markRaw(ActionNodeComp),
} as any
const edgeTypes = { condition: markRaw(ConditionEdgeComp) } as any

// Using any[] avoids fighting VueFlow's internal GraphNode/GraphEdge types
const vfNodes = ref<any[]>([])
const vfEdges = ref<any[]>([])

// ── Add-node modal state ───────────────────────────────────────────────────

const showAddModal = ref(false)
const pendingEdge = ref<{ sourceId: string; condition: Condition } | null>(null)
const modalGroup = ref<'task' | 'question' | 'remote_approval' | 'action'>('task')
const modalActionSubtype = ref<ActionNodeType>('list_generator')
const modalSourceArtifact = ref('')
const modalSlug = ref('')
const modalTemplateId = ref('')
const modalLabel = ref('')

// Action node config modal
const showActionConfigModal = ref(false)
const pendingActionType = ref<ActionNodeType>('list_generator')
const pendingActionNodeId = ref<string | null>(null)
const pendingActionIsNew = ref(false)

// Remote approval config modal
const showRemoteApprovalConfigModal = ref(false)
const pendingRemoteApprovalNodeId = ref<string | null>(null)
const pendingRemoteApprovalIsNew = ref(false)

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
      const isQuestion = n.node_type === 'question'
      const isRemoteApproval = n.node_type === 'remote_approval'
      const isAction = ACTION_NODE_TYPES.has(n.node_type)
      let vfType = 'template'
      if (isQuestion) vfType = 'question'
      else if (isRemoteApproval) vfType = 'remote_approval'
      else if (isAction) vfType = 'action'
      return {
        id: nodeId,
        type: vfType,
        position: pos,
        data: {
          label: n.label,
          node_type: n.node_type ?? 'task',
          slug: n.slug ?? '',
          emails: (n.action_config ?? {}).emails ?? [],
          template_id: (isQuestion || isRemoteApproval || isAction) ? null : n.template_id,
          template_name: (isQuestion || isRemoteApproval || isAction) ? '' : (props.templates.find(t => t.id === n.template_id)?.name ?? ''),
          action_config: n.action_config ?? {},
          onAddNode: (cond: Condition) => openAddModal(nodeId, cond),
          onLinkNode: () => openLinkModal(nodeId),
          onConfigure: isAction ? () => openActionConfigModal(nodeId) : (isRemoteApproval ? () => openRemoteApprovalConfigModal(nodeId) : undefined),
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
      node_type: (vn.data.node_type ?? (vn.type === 'question' ? 'question' : vn.type === 'remote_approval' ? 'remote_approval' : 'task')) as WNodeType,
      slug: vn.data.slug ?? '',
      label: vn.data.label ?? '',
      template_id: (vn.type === 'question' || vn.type === 'remote_approval' || vn.type === 'action') ? null : (vn.data.template_id ?? null),
      action_config: vn.data.action_config ?? {},
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
  modalGroup.value = 'task'
  modalActionSubtype.value = 'list_generator'
  modalSourceArtifact.value = ''
  modalSlug.value = ''
  modalTemplateId.value = ''
  modalLabel.value = ''
  showAddModal.value = true
}

function openActionConfigModal(nodeId: string) {
  const vn = vfNodes.value.find((n: any) => n.id === nodeId)
  if (!vn) return
  pendingActionType.value = vn.data.node_type as ActionNodeType
  pendingActionNodeId.value = nodeId
  pendingActionIsNew.value = false
  showActionConfigModal.value = true
}

function openRemoteApprovalConfigModal(nodeId: string) {
  pendingRemoteApprovalNodeId.value = nodeId
  pendingRemoteApprovalIsNew.value = false
  showRemoteApprovalConfigModal.value = true
}

function confirmRemoteApprovalConfig(config: Record<string, any>) {
  showRemoteApprovalConfigModal.value = false
  const nodeId = pendingRemoteApprovalNodeId.value
  if (!nodeId) return
  vfNodes.value = vfNodes.value.map((n: any) =>
    n.id === nodeId
      ? { ...n, data: { ...n.data, slug: config.slug ?? '', emails: config.emails ?? [], action_config: { ...n.data.action_config, slug: config.slug, emails: config.emails } } }
      : n
  )
  updateSelectedVfNode()
  emitUpdate()
  pendingRemoteApprovalNodeId.value = null
  pendingRemoteApprovalIsNew.value = false
}

function cancelRemoteApprovalConfig() {
  showRemoteApprovalConfigModal.value = false
  if (pendingRemoteApprovalIsNew.value && pendingRemoteApprovalNodeId.value) {
    const id = pendingRemoteApprovalNodeId.value
    vfNodes.value = vfNodes.value.filter((n: any) => n.id !== id)
    vfEdges.value = vfEdges.value.filter((e: any) => e.source !== id && e.target !== id)
    emitUpdate()
  }
  pendingRemoteApprovalNodeId.value = null
  pendingRemoteApprovalIsNew.value = false
}

function confirmActionConfig(config: Record<string, any>) {
  showActionConfigModal.value = false
  const nodeId = pendingActionNodeId.value
  if (!nodeId) return
  vfNodes.value = vfNodes.value.map((n: any) =>
    n.id === nodeId ? { ...n, data: { ...n.data, action_config: config } } : n
  )
  updateSelectedVfNode()
  emitUpdate()
  pendingActionNodeId.value = null
  pendingActionIsNew.value = false
}

function cancelActionConfig() {
  showActionConfigModal.value = false
  if (pendingActionIsNew.value && pendingActionNodeId.value) {
    const id = pendingActionNodeId.value
    vfNodes.value = vfNodes.value.filter((n: any) => n.id !== id)
    vfEdges.value = vfEdges.value.filter((e: any) => e.source !== id && e.target !== id)
    rebuildStartEdges()
    selectedNodeId.value = null
    selectedVfNode.value = null
    emitUpdate()
  }
  pendingActionNodeId.value = null
  pendingActionIsNew.value = false
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

  const effectiveNodeType: WNodeType = modalGroup.value === 'action'
    ? modalActionSubtype.value
    : modalGroup.value as WNodeType
  const isAction = ACTION_NODE_TYPES.has(effectiveNodeType)
  const isRemoteApproval = effectiveNodeType === 'remote_approval'

  // Pre-populate source artifact into action_config so config modal inherits it
  let initialActionConfig: Record<string, any> = {}
  if (isAction && modalSourceArtifact.value.trim()) {
    const sourceKey = modalActionSubtype.value === 'send_mail' ? 'attachment_artifact_tag' : 'source_artifact_tag'
    initialActionConfig[sourceKey] = modalSourceArtifact.value.trim()
  }

  updatedWNodes.push({
    node_id: newId,
    node_type: effectiveNodeType,
    slug: effectiveNodeType === 'question' ? modalSlug.value.trim() : '',
    label: modalLabel.value,
    template_id: (effectiveNodeType === 'question' || effectiveNodeType === 'remote_approval' || isAction) ? null : (modalTemplateId.value || null),
    action_config: initialActionConfig,
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

  // Open config modal immediately for action nodes
  if (isAction) {
    pendingActionType.value = modalActionSubtype.value
    pendingActionNodeId.value = newId
    pendingActionIsNew.value = true
    showActionConfigModal.value = true
  }

  // Open remote approval config modal immediately
  if (isRemoteApproval) {
    pendingRemoteApprovalNodeId.value = newId
    pendingRemoteApprovalIsNew.value = true
    showRemoteApprovalConfigModal.value = true
  }
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

function updateSlug(slug: string) {
  if (!selectedNodeId.value) return
  vfNodes.value = vfNodes.value.map((n: any) =>
    n.id === selectedNodeId.value ? { ...n, data: { ...n.data, slug: slug.trim() } } : n
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
        <div class="grid gap-3" :class="(selectedVfNode.type === 'question' || selectedVfNode.type === 'remote_approval' || selectedVfNode.type === 'action') ? 'grid-cols-1' : 'grid-cols-2'">
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
          <div v-if="selectedVfNode.type === 'template'">
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
          <div v-else-if="selectedVfNode.type === 'action'" class="space-y-2">
            <button type="button"
              @click="openActionConfigModal(selectedNodeId!)"
              class="w-full flex items-center justify-center gap-1.5 bg-violet-50 hover:bg-violet-100 border border-violet-200 text-violet-700 text-xs font-medium px-3 py-2 rounded-lg transition-colors"
            >
              <Zap class="w-3.5 h-3.5" /> Configure Action
            </button>
            <p v-if="selectedVfNode.data.action_config?.artifact_cache_id" class="text-[11px] text-violet-500">
              Cache: {{ selectedVfNode.data.action_config.artifact_cache_id?.slice(-8) }}
            </p>
          </div>
          <div v-else-if="selectedVfNode.type === 'remote_approval'" class="space-y-2">
            <button type="button"
              @click="openRemoteApprovalConfigModal(selectedNodeId!)"
              class="w-full flex items-center justify-center gap-1.5 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 text-indigo-700 text-xs font-medium px-3 py-2 rounded-lg transition-colors"
            >
              <MailCheck class="w-3.5 h-3.5" /> Configure Recipients
            </button>
            <p v-if="selectedVfNode.data.emails?.length" class="text-[11px] text-indigo-500">
              {{ selectedVfNode.data.emails.length }} recipient{{ selectedVfNode.data.emails.length > 1 ? 's' : '' }} configured
            </p>
          </div>
          <div v-else class="space-y-2">
            <div>
              <label class="block text-xs font-medium text-gray-600 mb-1">Artifact slug</label>
              <input
                :value="selectedVfNode.data.slug ?? ''"
                @input="updateSlug(($event.target as HTMLInputElement).value)"
                type="text"
                class="w-full border border-gray-300 rounded px-2 py-1.5 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-amber-400"
                placeholder="e.g. deploy-approval"
              />
              <p class="text-[11px] text-gray-400 mt-0.5">Name of the JSON artifact uploaded by the previous task.</p>
            </div>
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

    <!-- Action node config modal -->
    <Teleport to="body">
      <div
        v-if="showActionConfigModal"
        class="fixed inset-0 z-50 flex items-center justify-center p-4"
        @click.self="cancelActionConfig"
      >
        <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" />
        <div class="relative bg-white rounded-2xl shadow-2xl w-full max-w-md p-6 max-h-[90vh] overflow-y-auto">
          <ListGeneratorConfigModal
            v-if="pendingActionType === 'list_generator'"
            :project-id="projectId"
            :initial="pendingActionNodeId ? vfNodes.find((n:any) => n.id === pendingActionNodeId)?.data?.action_config : undefined"
            @confirm="confirmActionConfig"
            @cancel="cancelActionConfig"
          />
          <PdfGeneratorConfigModal
            v-else-if="pendingActionType === 'pdf_generator'"
            :project-id="projectId"
            :initial="pendingActionNodeId ? vfNodes.find((n:any) => n.id === pendingActionNodeId)?.data?.action_config : undefined"
            @confirm="confirmActionConfig"
            @cancel="cancelActionConfig"
          />
          <SendMailConfigModal
            v-else-if="pendingActionType === 'send_mail'"
            :project-id="projectId"
            :initial="pendingActionNodeId ? vfNodes.find((n:any) => n.id === pendingActionNodeId)?.data?.action_config : undefined"
            @confirm="confirmActionConfig"
            @cancel="cancelActionConfig"
          />
          <TransferFileConfigModal
            v-else-if="pendingActionType === 'transfer_file'"
            :project-id="projectId"
            :initial="pendingActionNodeId ? vfNodes.find((n:any) => n.id === pendingActionNodeId)?.data?.action_config : undefined"
            @confirm="confirmActionConfig"
            @cancel="cancelActionConfig"
          />
        </div>
      </div>
    </Teleport>

    <!-- Remote Approval config modal -->
    <Teleport to="body">
      <div
        v-if="showRemoteApprovalConfigModal"
        class="fixed inset-0 z-50 flex items-center justify-center p-4"
        @click.self="cancelRemoteApprovalConfig"
      >
        <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" />
        <div class="relative bg-white rounded-2xl shadow-2xl w-full max-w-sm p-6">
          <RemoteApprovalConfigModal
            :initial="pendingRemoteApprovalNodeId
              ? { slug: vfNodes.find((n:any) => n.id === pendingRemoteApprovalNodeId)?.data?.slug ?? '',
                  emails: vfNodes.find((n:any) => n.id === pendingRemoteApprovalNodeId)?.data?.emails ?? [] }
              : undefined"
            @confirm="confirmRemoteApprovalConfig"
            @cancel="cancelRemoteApprovalConfig"
          />
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

            <!-- Node type: 4 top-level buttons -->
            <div>
              <label class="block text-xs font-medium text-gray-600 mb-2">Node type</label>
              <div class="grid grid-cols-2 gap-2">
                <button type="button" @click="modalGroup = 'task'"
                  class="flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-medium border transition-colors"
                  :class="modalGroup === 'task' ? 'bg-brand-600 border-brand-600 text-white' : 'bg-white border-gray-200 text-gray-500 hover:bg-gray-50'"
                ><Play class="w-3 h-3" /> Task</button>
                <button type="button" @click="modalGroup = 'question'"
                  class="flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-medium border transition-colors"
                  :class="modalGroup === 'question' ? 'bg-amber-500 border-amber-500 text-white' : 'bg-white border-gray-200 text-gray-500 hover:bg-gray-50'"
                ><HelpCircle class="w-3 h-3" /> Approval Gate</button>
                <button type="button" @click="modalGroup = 'remote_approval'"
                  class="flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-medium border transition-colors"
                  :class="modalGroup === 'remote_approval' ? 'bg-indigo-600 border-indigo-600 text-white' : 'bg-white border-gray-200 text-gray-500 hover:bg-gray-50'"
                ><MailCheck class="w-3 h-3" /> Remote Approval</button>
                <button type="button" @click="modalGroup = 'action'"
                  class="flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-medium border transition-colors"
                  :class="modalGroup === 'action' ? 'bg-violet-600 border-violet-600 text-white' : 'bg-white border-gray-200 text-gray-500 hover:bg-gray-50'"
                ><Zap class="w-3 h-3" /> Action</button>
              </div>
            </div>

            <!-- Task: template selector -->
            <div v-if="modalGroup === 'task'">
              <label class="block text-xs font-medium text-gray-600 mb-1">
                Template <span class="text-gray-400 font-normal">(optional)</span>
              </label>
              <select v-model="modalTemplateId"
                class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 bg-white"
              >
                <option value="">— none —</option>
                <option v-for="t in templates" :key="t.id" :value="t.id">{{ t.name }}</option>
              </select>
            </div>

            <!-- Remote Approval: info only (config opens in modal) -->
            <div v-else-if="modalGroup === 'remote_approval'">
              <p class="text-xs text-indigo-600 bg-indigo-50 border border-indigo-100 rounded-lg px-3 py-2">
                After adding, you will configure the recipient emails and optional artifact slug in the next step.
              </p>
            </div>

            <!-- Approval Gate: artifact slug -->
            <div v-else-if="modalGroup === 'question'" class="space-y-3">
              <div>
                <label class="block text-xs font-medium text-gray-600 mb-1">
                  Artifact slug <span class="text-red-500">*</span>
                </label>
                <input v-model="modalSlug" type="text"
                  class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-amber-400"
                  placeholder="e.g. deploy-approval"
                  pattern="[a-z0-9][a-z0-9_-]*"
                />
                <p class="text-[11px] text-gray-400 mt-1">
                  The preceding task uploads a JSON artifact with this name containing
                  <code class="bg-gray-100 px-1 rounded">{"title": "...", "text": "..."}</code>.
                </p>
              </div>
            </div>

            <!-- Action: subtype dropdown + source artifact -->
            <div v-else class="space-y-3">
              <div>
                <label class="block text-xs font-medium text-gray-600 mb-1">Action type</label>
                <select v-model="modalActionSubtype"
                  class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-400 bg-white"
                >
                  <option v-for="(meta, type) in ACTION_NODE_META" :key="type" :value="type">
                    {{ meta.label }}
                  </option>
                </select>
              </div>
              <div>
                <label class="block text-xs font-medium text-gray-600 mb-1">
                  {{ modalActionSubtype === 'send_mail' ? 'Attachment artifact' : 'Source artifact' }}
                  <span v-if="modalActionSubtype !== 'send_mail'" class="text-red-500">*</span>
                  <span v-else class="text-gray-400 font-normal">(optional)</span>
                </label>
                <input v-model="modalSourceArtifact" type="text"
                  class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-violet-400"
                  :placeholder="
                    modalActionSubtype === 'pdf_generator' ? 'e.g. report.md' :
                    modalActionSubtype === 'send_mail'     ? 'e.g. report.pdf' :
                    modalActionSubtype === 'transfer_file' ? 'e.g. report.xlsx' :
                    'e.g. scan-results'
                  "
                />
                <p class="text-[11px] text-gray-400 mt-1">
                  {{
                    modalActionSubtype === 'pdf_generator'  ? 'Markdown or HTML artifact from a previous task.' :
                    modalActionSubtype === 'send_mail'      ? 'Artifact to attach to the email.' :
                    modalActionSubtype === 'transfer_file'  ? 'Artifact to transfer to the remote destination.' :
                    'JSON array artifact from a previous task (array of objects).'
                  }}
                </p>
              </div>
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
