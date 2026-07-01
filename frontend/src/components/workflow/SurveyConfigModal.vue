<script setup lang="ts">
import { reactive } from 'vue'
import { X, ClipboardList } from 'lucide-vue-next'

const props = defineProps<{
  initial?: Record<string, any>
}>()

const emit = defineEmits<{
  confirm: [config: Record<string, any>]
  cancel: []
}>()

const cfg = reactive({
  input_artifact_name: props.initial?.input_artifact_name ?? '',
  output_artifact_name: props.initial?.output_artifact_name ?? '',
})

function confirm() {
  if (!cfg.input_artifact_name.trim() || !cfg.output_artifact_name.trim()) return
  emit('confirm', {
    input_artifact_name: cfg.input_artifact_name.trim(),
    output_artifact_name: cfg.output_artifact_name.trim(),
  })
}
</script>

<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-2">
        <ClipboardList class="w-5 h-5 text-teal-600" />
        <h3 class="font-semibold text-gray-900">Configure Survey</h3>
      </div>
      <button type="button" @click="emit('cancel')" class="text-gray-400 hover:text-gray-600">
        <X class="w-5 h-5" />
      </button>
    </div>

    <div>
      <label class="block text-xs font-medium text-gray-600 mb-1">
        Input artifact name <span class="text-red-500">*</span>
      </label>
      <input
        v-model="cfg.input_artifact_name"
        type="text"
        class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-teal-400"
        placeholder="e.g. survey_schema"
      />
      <p class="text-[11px] text-gray-400 mt-1">
        Name of the JSON artifact uploaded by the preceding task, describing the form to render.
      </p>
    </div>

    <div>
      <label class="block text-xs font-medium text-gray-600 mb-1">
        Output artifact name <span class="text-red-500">*</span>
      </label>
      <input
        v-model="cfg.output_artifact_name"
        type="text"
        class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-teal-400"
        placeholder="e.g. survey_answers"
      />
      <p class="text-[11px] text-gray-400 mt-1">
        Name of the JSON artifact the submitted answers are written to. Downstream tasks can read it from the artifact cache.
      </p>
    </div>

    <div class="bg-gray-50 border border-gray-200 rounded-lg p-3">
      <p class="text-[11px] font-medium text-gray-500 mb-1">Expected input artifact format</p>
      <pre class="text-[10px] text-gray-500 font-mono whitespace-pre-wrap leading-relaxed">{
  "title": "Deployment Details",
  "fields": [
    { "name": "environment", "label": "Environment", "type": "enum",
      "options": [{"value":"dev","label":"Dev"},{"value":"prod","label":"Prod"}] },
    { "name": "region", "label": "Region", "type": "enum",
      "options_by": { "field": "environment",
        "map": { "prod": [{"value":"eu-1","label":"EU-1"}] } },
      "visible_if": [{"field":"environment","op":"eq","value":"prod"}] }
  ]
}</pre>
    </div>

    <div class="flex gap-3 pt-2">
      <button
        type="button"
        @click="confirm"
        :disabled="!cfg.input_artifact_name.trim() || !cfg.output_artifact_name.trim()"
        class="flex-1 bg-teal-600 hover:bg-teal-700 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
      >Save</button>
      <button type="button" @click="emit('cancel')"
        class="text-sm text-gray-500 hover:text-gray-700 px-4 py-2 rounded-lg border border-gray-200 hover:bg-gray-50 transition-colors"
      >Cancel</button>
    </div>
  </div>
</template>
