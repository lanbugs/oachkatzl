<script setup lang="ts">
import { reactive } from 'vue'
import { X } from 'lucide-vue-next'

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
  output_filename: props.initial?.output_filename ?? '',
})

function confirm() {
  emit('confirm', { ...cfg })
}
</script>

<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <h3 class="font-semibold text-gray-900">Configure PDF Generator</h3>
      <button type="button" @click="emit('cancel')" class="text-gray-400 hover:text-gray-600"><X class="w-5 h-5" /></button>
    </div>

    <p class="text-xs text-gray-500">Source artifact is configured on the node itself. The artifact must be a Markdown (.md) or HTML (.html) file.</p>

    <div>
      <label class="block text-xs font-medium text-gray-600 mb-1">Output Filename</label>
      <input
        v-model="cfg.output_filename"
        type="text"
        class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-violet-400"
        placeholder="e.g. report.pdf"
        autofocus
      />
      <p class="text-[11px] text-gray-400 mt-1">Leave blank to use <code class="bg-gray-100 px-1 rounded">output.pdf</code>.</p>
    </div>

    <div class="flex gap-3 pt-2">
      <button type="button"
        @click="confirm"
        class="flex-1 bg-violet-600 hover:bg-violet-700 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
      >Save</button>
      <button type="button" @click="emit('cancel')"
        class="text-sm text-gray-500 hover:text-gray-700 px-4 py-2 rounded-lg border border-gray-200 hover:bg-gray-50 transition-colors"
      >Cancel</button>
    </div>
  </div>
</template>
