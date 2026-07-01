<script setup lang="ts">
import { ref } from 'vue'
import { Handle, Position } from '@vue-flow/core'
import { Link2, ClipboardList } from 'lucide-vue-next'

type Condition = 'success' | 'failure' | 'always'

const props = defineProps<{
  id: string
  data: {
    label?: string
    action_config?: { input_artifact_name?: string; output_artifact_name?: string }
    onAddNode?: (condition: Condition) => void
    onLinkNode?: () => void
  }
  selected?: boolean
}>()

const isHovered = ref(false)

function addNode(cond: Condition) {
  props.data.onAddNode?.(cond)
}
</script>

<template>
  <div
    class="relative"
    @mouseenter="isHovered = true"
    @mouseleave="isHovered = false"
  >
    <Handle
      type="target"
      :position="Position.Left"
      :connectable="false"
      style="background: #0d9488; border: 2px solid white; width: 10px; height: 10px; left: -5px;"
    />

    <div
      class="w-48 rounded-xl border-2 bg-teal-50 shadow-sm transition-all select-none"
      :class="selected
        ? 'border-teal-500 shadow-teal-100 shadow-md'
        : 'border-teal-300 hover:border-teal-400 hover:shadow-md'"
    >
      <div class="px-4 py-3 flex items-center gap-2.5">
        <ClipboardList class="w-4 h-4 text-teal-500 shrink-0" />
        <div class="min-w-0">
          <p class="text-sm font-semibold text-teal-900 truncate leading-tight">
            {{ data.label || 'Survey' }}
          </p>
          <p class="text-xs text-teal-400 mt-0.5 font-mono truncate">
            {{ data.action_config?.input_artifact_name || '— not configured —' }}
          </p>
        </div>
      </div>
    </div>

    <Handle
      type="source"
      :position="Position.Right"
      :connectable="false"
      style="background: #0d9488; border: 2px solid white; width: 10px; height: 10px; right: -5px;"
    />

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
