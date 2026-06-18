<script setup lang="ts">
import { ref } from 'vue'
import { Handle, Position } from '@vue-flow/core'
import { Link2, MailCheck } from 'lucide-vue-next'

type Condition = 'success' | 'failure' | 'always'

const props = defineProps<{
  id: string
  data: {
    label?: string
    slug?: string
    emails?: string[]
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
      style="background: #6366f1; border: 2px solid white; width: 10px; height: 10px; left: -5px;"
    />

    <div
      class="w-48 rounded-xl border-2 bg-indigo-50 shadow-sm transition-all select-none"
      :class="selected
        ? 'border-indigo-500 shadow-indigo-100 shadow-md'
        : 'border-indigo-300 hover:border-indigo-400 hover:shadow-md'"
    >
      <div class="px-4 py-3 flex items-center gap-2.5">
        <MailCheck class="w-4 h-4 text-indigo-500 shrink-0" />
        <div class="min-w-0">
          <p class="text-sm font-semibold text-indigo-900 truncate leading-tight">
            {{ data.label || 'Remote Approval' }}
          </p>
          <p class="text-xs text-indigo-400 mt-0.5 font-mono truncate">
            {{ data.emails?.length ? `${data.emails.length} recipient${data.emails.length > 1 ? 's' : ''}` : '— no emails —' }}
          </p>
        </div>
      </div>
    </div>

    <Handle
      type="source"
      :position="Position.Right"
      :connectable="false"
      style="background: #6366f1; border: 2px solid white; width: 10px; height: 10px; right: -5px;"
    />

    <Transition name="toolbar">
      <div
        v-if="isHovered"
        class="absolute left-full top-1/2 -translate-y-1/2 ml-3 flex flex-col gap-1 z-10"
      >
        <button type="button"
          @click.stop.prevent="addNode('success')"
          class="w-7 h-7 rounded-full bg-green-500 hover:bg-green-600 text-white text-xs font-bold shadow flex items-center justify-center transition-colors"
          title="Add on approve (success)"
        >✓</button>
        <button type="button"
          @click.stop.prevent="addNode('failure')"
          class="w-7 h-7 rounded-full bg-red-500 hover:bg-red-600 text-white text-xs font-bold shadow flex items-center justify-center transition-colors"
          title="Add on reject (failure)"
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
