<script setup lang="ts">
import { ref, computed } from 'vue'
import { Handle, Position } from '@vue-flow/core'
import { Link2, Sheet, FileText, Mail, Upload } from 'lucide-vue-next'

type Condition = 'success' | 'failure' | 'always'

export type ActionNodeType = 'list_generator' | 'pdf_generator' | 'send_mail' | 'transfer_file'

const ACTION_META: Record<ActionNodeType, { label: string; icon: any }> = {
  list_generator: { label: 'List Generator', icon: Sheet },
  pdf_generator:  { label: 'PDF Generator',  icon: FileText },
  send_mail:      { label: 'Send Mail',       icon: Mail },
  transfer_file:  { label: 'Transfer File',   icon: Upload },
}

const props = defineProps<{
  id: string
  data: {
    label?: string
    node_type: ActionNodeType
    action_config?: Record<string, any>
    cache_name?: string
    onAddNode?: (condition: Condition) => void
    onLinkNode?: () => void
    onConfigure?: () => void
  }
  selected?: boolean
}>()

const isHovered = ref(false)

const meta = computed(() => ACTION_META[props.data.node_type] ?? { label: props.data.node_type, icon: Upload })

const displayName = computed(() => {
  const s = props.data.label || meta.value.label
  return s.length > 22 ? s.slice(0, 21) + '…' : s
})

const displaySub = computed(() => {
  const s = meta.value.label
  return props.data.label ? (s.length > 26 ? s.slice(0, 25) + '…' : s) : ''
})
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
      style="background: #94a3b8; border: 2px solid white; width: 10px; height: 10px; left: -5px;"
    />

    <div
      class="w-48 rounded-xl border-2 bg-white shadow-sm transition-all select-none"
      :class="selected
        ? 'border-violet-500 shadow-violet-100 shadow-md'
        : 'border-violet-200 hover:border-violet-300 hover:shadow-md'"
    >
      <!-- Purple header bar -->
      <div class="flex items-center gap-1.5 px-3 py-1.5 rounded-t-xl bg-violet-600">
        <component :is="meta.icon" class="w-3 h-3 text-white/80 shrink-0" />
        <span class="text-[10px] font-semibold text-white/90 uppercase tracking-wide truncate">{{ meta.label }}</span>
      </div>

      <div class="px-4 py-2.5">
        <p class="text-sm font-semibold text-gray-800 truncate leading-tight">{{ displayName }}</p>
        <p v-if="displaySub" class="text-xs text-gray-400 truncate mt-0.5">{{ displaySub }}</p>
        <p v-if="data.cache_name" class="text-[10px] text-violet-400 truncate mt-0.5">{{ data.cache_name }}</p>
      </div>
    </div>

    <Handle
      type="source"
      :position="Position.Right"
      :connectable="false"
      style="background: #94a3b8; border: 2px solid white; width: 10px; height: 10px; right: -5px;"
    />

    <Transition name="toolbar">
      <div
        v-if="isHovered"
        class="absolute left-full top-1/2 -translate-y-1/2 ml-3 flex flex-col gap-1 z-10"
      >
        <button type="button"
          @click.stop.prevent="data.onAddNode?.('success')"
          class="w-7 h-7 rounded-full bg-green-500 hover:bg-green-600 text-white text-xs font-bold shadow flex items-center justify-center transition-colors"
          title="Add on success"
        >✓</button>
        <button type="button"
          @click.stop.prevent="data.onAddNode?.('failure')"
          class="w-7 h-7 rounded-full bg-red-500 hover:bg-red-600 text-white text-xs font-bold shadow flex items-center justify-center transition-colors"
          title="Add on failure"
        >✗</button>
        <button type="button"
          @click.stop.prevent="data.onAddNode?.('always')"
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
