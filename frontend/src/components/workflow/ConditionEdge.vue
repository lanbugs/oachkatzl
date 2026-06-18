<script setup lang="ts">
import { ref, computed } from 'vue'
import { useVueFlow, getBezierPath, EdgeLabelRenderer, BaseEdge } from '@vue-flow/core'
import { X } from 'lucide-vue-next'

const props = defineProps<{
  id: string
  source: string
  target: string
  sourceX: number
  sourceY: number
  targetX: number
  targetY: number
  sourcePosition: any
  targetPosition: any
  data?: Record<string, any>
  selected?: boolean
}>()

const { removeEdges } = useVueFlow()

const COLORS = { success: '#22c55e', failure: '#ef4444', always: '#94a3b8' } as const
const LABELS = { success: '✓', failure: '✗', always: '→' } as const

type Cond = keyof typeof COLORS

const condition = computed<Cond>(() => (props.data?.condition ?? 'always') as Cond)
const color = computed(() => COLORS[condition.value] ?? '#94a3b8')
const label = computed(() => LABELS[condition.value] ?? '→')
const isDeletable = computed(() => props.source !== '__start__')

const pathData = computed(() =>
  getBezierPath({
    sourceX: props.sourceX,
    sourceY: props.sourceY,
    sourcePosition: props.sourcePosition,
    targetX: props.targetX,
    targetY: props.targetY,
    targetPosition: props.targetPosition,
  })
)
const edgePath = computed(() => pathData.value[0])
const labelX = computed(() => pathData.value[1])
const labelY = computed(() => pathData.value[2])

const isHovered = ref(false)

function deleteEdge() {
  removeEdges([props.id])
}
</script>

<template>
  <BaseEdge
    :id="id"
    :path="edgePath"
    :style="{ stroke: color, strokeWidth: 2, opacity: 0.85 }"
  />

  <EdgeLabelRenderer>
    <div
      :style="{
        position: 'absolute',
        transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
        pointerEvents: 'all',
      }"
      class="nodrag nopan"
      @mouseenter="isHovered = true"
      @mouseleave="isHovered = false"
    >
      <div class="flex items-center gap-1">
        <span
          class="text-xs font-bold px-1.5 py-0.5 rounded-full select-none"
          :style="{ backgroundColor: color + '25', color }"
        >{{ label }}</span>
        <button type="button"
          v-if="isHovered && isDeletable"
          @click.stop="deleteEdge"
          class="w-4 h-4 rounded-full flex items-center justify-center text-white shadow-sm"
          :style="{ backgroundColor: color }"
          title="Remove connection"
        >
          <X class="w-2.5 h-2.5" />
        </button>
      </div>
    </div>
  </EdgeLabelRenderer>
</template>
