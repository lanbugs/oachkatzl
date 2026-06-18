<script setup lang="ts">
import { ref, computed } from 'vue'
import { Handle, Position } from '@vue-flow/core'
import { Link2 } from 'lucide-vue-next'

type Condition = 'success' | 'failure' | 'always'

const props = defineProps<{
  id: string
  data: {
    label?: string
    template_id?: string | null
    template_name?: string
    onAddNode?: (condition: Condition) => void
    onLinkNode?: () => void
  }
  selected?: boolean
}>()

const isHovered = ref(false)

function addNode(cond: Condition) {
  props.data.onAddNode?.(cond)
}

const displayName = computed(() => {
  const s = props.data.label || props.data.template_name || 'Unassigned'
  return s.length > 22 ? s.slice(0, 21) + '…' : s
})

const displaySub = computed(() => {
  if (!props.data.label) return ''
  const s = props.data.template_name || ''
  return s.length > 26 ? s.slice(0, 25) + '…' : s
})
</script>

<template>
  <div
    class="relative"
    @mouseenter="isHovered = true"
    @mouseleave="isHovered = false"
  >
    <!-- Target handle -->
    <Handle
      type="target"
      :position="Position.Left"
      :connectable="false"
      style="background: #94a3b8; border: 2px solid white; width: 10px; height: 10px; left: -5px;"
    />

    <!-- Node body -->
    <div
      class="w-48 rounded-xl border-2 bg-white shadow-sm transition-all select-none"
      :class="selected
        ? 'border-brand-500 shadow-brand-100 shadow-md'
        : 'border-gray-200 hover:border-gray-300 hover:shadow-md'"
    >
      <div class="px-4 py-3">
        <p class="text-sm font-semibold text-gray-800 truncate leading-tight">{{ displayName }}</p>
        <p v-if="displaySub" class="text-xs text-gray-400 truncate mt-0.5">{{ displaySub }}</p>
        <p v-else-if="!data.template_name" class="text-xs text-gray-300 italic mt-0.5">no template</p>
      </div>
    </div>

    <!-- Source handle -->
    <Handle
      type="source"
      :position="Position.Right"
      :connectable="false"
      style="background: #94a3b8; border: 2px solid white; width: 10px; height: 10px; right: -5px;"
    />

    <!-- Hover toolbar -->
    <Transition name="toolbar">
      <div
        v-if="isHovered"
        class="absolute left-full top-1/2 -translate-y-1/2 ml-3 flex flex-col gap-1 z-10"
      >
        <button type="button"
          @click.stop.prevent="addNode('success')"
          class="w-7 h-7 rounded-full bg-green-500 hover:bg-green-600 text-white text-xs font-bold shadow flex items-center justify-center transition-colors"
          title="Add on success"
        >✓</button>
        <button type="button"
          @click.stop.prevent="addNode('failure')"
          class="w-7 h-7 rounded-full bg-red-500 hover:bg-red-600 text-white text-xs font-bold shadow flex items-center justify-center transition-colors"
          title="Add on failure"
        >✗</button>
        <button type="button"
          @click.stop.prevent="addNode('always')"
          class="w-7 h-7 rounded-full bg-slate-400 hover:bg-slate-500 text-white text-xs font-bold shadow flex items-center justify-center transition-colors"
          title="Add always"
        >→</button>
        <button type="button"
          @click.stop.prevent="props.data.onLinkNode?.()"
          class="w-7 h-7 rounded-full bg-blue-500 hover:bg-blue-600 text-white shadow flex items-center justify-center transition-colors"
          title="Link to existing node"
        ><Link2 class="w-3.5 h-3.5" /></button>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.toolbar-enter-active, .toolbar-leave-active { transition: opacity 0.12s, transform 0.12s; }
.toolbar-enter-from, .toolbar-leave-to { opacity: 0; transform: translateY(-50%) translateX(-4px); }
</style>
