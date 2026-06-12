<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { X, Play } from 'lucide-vue-next'
import { parseEnumOptions } from '@/composables/useEnumOptions'

interface SurveyVar {
  name: string
  title: string
  description: string
  type: 'string' | 'int' | 'enum' | 'secret' | 'bool' | 'separator'
  required: boolean
  default: string
  values: string[]
}

interface Workflow {
  id: string
  name: string
  survey_vars: SurveyVar[]
}

const props = defineProps<{ workflow: Workflow | null; open: boolean }>()
const emit  = defineEmits<{ close: []; run: [surveyAnswers: string] }>()

const answers = ref<Record<string, string | boolean>>({})
const errors  = ref<Record<string, string>>({})

watch(() => props.open, open => {
  if (!open) return
  answers.value = {}
  errors.value  = {}
  for (const sv of props.workflow?.survey_vars ?? []) {
    if (sv.type === 'separator') continue
    if (sv.type === 'bool') answers.value[sv.name] = sv.default === 'true'
    else if (sv.default) answers.value[sv.name] = sv.default
  }
})

const hasSurvey = computed(() => (props.workflow?.survey_vars?.length ?? 0) > 0)

function inputType(sv: SurveyVar) {
  if (sv.type === 'secret') return 'password'
  if (sv.type === 'int')    return 'number'
  return 'text'
}

function validate(): boolean {
  errors.value = {}
  for (const sv of props.workflow?.survey_vars ?? []) {
    if (sv.type === 'separator') continue
    const val = answers.value[sv.name]
    if (sv.type !== 'bool' && sv.required && !val)
      errors.value[sv.name] = `${sv.title || sv.name} is required`
    if (sv.type === 'int' && val && isNaN(Number(String(val))))
      errors.value[sv.name] = `${sv.title || sv.name} must be a number`
  }
  return Object.keys(errors.value).length === 0
}

function submit() {
  if (!validate()) return
  const out: Record<string, any> = {}
  for (const sv of props.workflow?.survey_vars ?? []) {
    if (sv.type === 'separator') continue
    const raw = answers.value[sv.name] ?? sv.default ?? ''
    if (sv.type === 'bool') out[sv.name] = answers.value[sv.name] === true
    else out[sv.name] = sv.type === 'int' ? Number(raw) : raw
  }
  emit('run', JSON.stringify(out))
}
</script>

<template>
  <Teleport to="body">
    <div v-if="open && workflow"
      class="fixed inset-0 z-50 flex items-center justify-center p-4"
      @click.self="$emit('close')">
      <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" />
      <div class="relative bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] flex flex-col">

        <!-- Header -->
        <div class="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <div>
            <h2 class="font-semibold text-gray-900">Run workflow</h2>
            <p class="text-xs text-gray-400 mt-0.5">{{ workflow.name }}</p>
          </div>
          <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600">
            <X class="w-5 h-5" />
          </button>
        </div>

        <!-- Body -->
        <div class="overflow-y-auto flex-1 px-6 py-5 space-y-4">
          <p v-if="!hasSurvey" class="text-sm text-gray-400 italic">
            No survey variables defined. The workflow will start immediately.
          </p>

          <div v-else class="space-y-4">
            <h3 class="text-sm font-medium text-gray-700">Variables</h3>

            <div v-for="sv in workflow.survey_vars" :key="sv.name" class="space-y-1">
              <!-- Separator -->
              <div v-if="sv.type === 'separator'" class="-mx-1 pt-1">
                <div class="flex items-center gap-3">
                  <div class="flex-1 h-px bg-gray-200" />
                  <span v-if="sv.title" class="text-xs font-semibold text-gray-400 uppercase tracking-wider">{{ sv.title }}</span>
                  <div v-if="sv.title" class="flex-1 h-px bg-gray-200" />
                </div>
              </div>

              <template v-else>
                <label class="flex items-center gap-1 text-xs font-medium text-gray-600">
                  {{ sv.title || sv.name }}
                  <span v-if="sv.required" class="text-red-500">*</span>
                </label>
                <p v-if="sv.description" class="text-xs text-gray-400">{{ sv.description }}</p>

                <!-- Bool -->
                <label v-if="sv.type === 'bool'" class="inline-flex items-center gap-2 cursor-pointer mt-1">
                  <input type="checkbox" v-model="answers[sv.name]"
                    class="w-4 h-4 rounded text-brand-600 focus:ring-brand-500" />
                  <span class="text-sm text-gray-700">{{ sv.title || sv.name }}</span>
                </label>

                <!-- Enum -->
                <select v-else-if="sv.type === 'enum'" v-model="answers[sv.name]"
                  class="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                  :class="errors[sv.name] ? 'border-red-400' : 'border-gray-300'">
                  <option value="">— Select —</option>
                  <option v-for="opt in parseEnumOptions(sv.values)" :key="opt.value" :value="opt.value">
                    {{ opt.label }}
                  </option>
                </select>

                <!-- String / int / secret -->
                <input v-else v-model="answers[sv.name]"
                  :type="inputType(sv)"
                  :placeholder="sv.default || ''"
                  class="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                  :class="errors[sv.name] ? 'border-red-400' : 'border-gray-300'" />

                <p v-if="errors[sv.name]" class="text-xs text-red-500">{{ errors[sv.name] }}</p>
              </template>
            </div>
          </div>
        </div>

        <!-- Footer -->
        <div class="flex items-center justify-end gap-3 px-6 py-4 border-t border-gray-100">
          <button @click="$emit('close')" class="text-sm text-gray-500 hover:text-gray-700">Cancel</button>
          <button @click="submit"
            class="flex items-center gap-2 bg-green-600 hover:bg-green-700 text-white text-sm font-medium px-5 py-2 rounded-lg">
            <Play class="w-4 h-4" /> Run
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
