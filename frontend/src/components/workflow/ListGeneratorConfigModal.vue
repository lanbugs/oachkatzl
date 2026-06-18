<script setup lang="ts">
import { reactive } from 'vue'
import { X, Sheet } from 'lucide-vue-next'

const props = defineProps<{
  projectId: string
  initial?: Record<string, any>
}>()

const emit = defineEmits<{
  confirm: [config: Record<string, any>]
  cancel: []
}>()

const cfg = reactive({
  source_artifact_tag: props.initial?.source_artifact_tag ?? '',
  format: (props.initial?.format ?? 'xlsx') as 'xlsx' | 'csv',
  output_filename: props.initial?.output_filename ?? '',
})

function confirm() {
  emit('confirm', { ...cfg })
}
</script>

<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-2">
        <Sheet class="w-5 h-5 text-violet-600" />
        <h3 class="font-semibold text-gray-900">Configure List Generator</h3>
      </div>
      <button type="button" @click="emit('cancel')" class="text-gray-400 hover:text-gray-600">
        <X class="w-5 h-5" />
      </button>
    </div>

    <div>
      <label class="block text-xs font-medium text-gray-600 mb-2">Output format</label>
      <div class="flex gap-2">
        <button
          v-for="fmt in (['xlsx', 'csv'] as const)" :key="fmt"
          type="button"
          @click="cfg.format = fmt"
          class="flex-1 py-1.5 rounded-lg text-xs font-medium border transition-colors"
          :class="cfg.format === fmt
            ? 'bg-violet-600 border-violet-600 text-white'
            : 'bg-white border-gray-200 text-gray-500 hover:bg-gray-50'"
        >{{ fmt.toUpperCase() }}</button>
      </div>
    </div>

    <div>
      <label class="block text-xs font-medium text-gray-600 mb-1">Output filename</label>
      <input
        v-model="cfg.output_filename"
        type="text"
        class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-violet-400"
        :placeholder="`e.g. report.${cfg.format}`"
      />
      <p class="text-[11px] text-gray-400 mt-1">Leave blank to use <code class="bg-gray-100 px-1 rounded">output.{{ cfg.format }}</code>.</p>
    </div>

    <div class="flex gap-3 pt-2">
      <button type="button"
        @click="confirm"
        :disabled="false"
        class="flex-1 bg-violet-600 hover:bg-violet-700 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
      >Save</button>
      <button type="button" @click="emit('cancel')"
        class="text-sm text-gray-500 hover:text-gray-700 px-4 py-2 rounded-lg border border-gray-200 hover:bg-gray-50 transition-colors"
      >Cancel</button>
    </div>
  </div>
</template>
