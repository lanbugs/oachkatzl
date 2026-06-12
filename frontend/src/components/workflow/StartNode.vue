<script setup lang="ts">
import { ref } from 'vue'
import { Handle, Position } from '@vue-flow/core'
import { Plus } from 'lucide-vue-next'

type Condition = 'success' | 'failure' | 'always'

const props = defineProps<{
  id: string
  data: {
    onAddNode?: (condition: Condition) => void
  }
  selected?: boolean
}>()

const isHovered = ref(false)
</script>

<template>
  <div
    class="relative flex items-center"
    @mouseenter="isHovered = true"
    @mouseleave="isHovered = false"
  >
    <!-- Node body -->
    <div class="bg-green-600 text-white text-sm font-bold px-5 py-2.5 rounded-full shadow-md select-none whitespace-nowrap">
      START
    </div>

    <!-- Source handle (visual only) -->
    <Handle
      type="source"
      :position="Position.Right"
      :connectable="false"
      style="background: #16a34a; border: 2px solid white; width: 10px; height: 10px; right: -5px;"
    />

    <!-- Single add button on hover -->
    <Transition name="toolbar">
      <div
        v-if="isHovered"
        class="absolute left-full top-1/2 -translate-y-1/2 ml-3 z-10"
      >
        <button
          type="button"
          @click.stop.prevent="props.data.onAddNode?.('always')"
          class="w-7 h-7 rounded-full bg-green-500 hover:bg-green-600 text-white shadow flex items-center justify-center transition-colors"
          title="Add node"
        >
          <Plus class="w-3.5 h-3.5" />
        </button>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.toolbar-enter-active, .toolbar-leave-active { transition: opacity 0.12s, transform 0.12s; }
.toolbar-enter-from, .toolbar-leave-to { opacity: 0; transform: translateY(-50%) translateX(-4px); }
</style>
