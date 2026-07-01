<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { Send, ClipboardList, XCircle, Loader2 } from 'lucide-vue-next'

interface FieldOption { value: string; label: string }
interface OptionsBy { field: string; map: Record<string, FieldOption[]>; default?: FieldOption[] }
interface VisibleIfCondition { field: string; op: 'eq' | 'neq' | 'in' | 'not_in'; value: any }

interface SurveyField {
  name: string
  label?: string
  type: 'string' | 'int' | 'bool' | 'enum' | 'multiselect' | 'secret' | 'textarea'
  required?: boolean
  default?: any
  options?: FieldOption[]
  options_by?: OptionsBy
  visible_if?: VisibleIfCondition[]
}

interface SurveySchema {
  title?: string
  description?: string
  fields?: SurveyField[]
}

const props = defineProps<{ schema: SurveySchema | null; open: boolean; submitting?: boolean; cancelling?: boolean }>()
const emit = defineEmits<{ submit: [answers: Record<string, any>]; cancel: [] }>()

const answers = ref<Record<string, any>>({})
const errors = ref<Record<string, string>>({})

const fields = computed(() => props.schema?.fields ?? [])

watch(() => props.open, open => {
  if (!open) return
  errors.value = {}
  const init: Record<string, any> = {}
  for (const f of fields.value) {
    if (f.type === 'bool') init[f.name] = f.default === true || f.default === 'true'
    else if (f.type === 'multiselect') init[f.name] = Array.isArray(f.default) ? [...f.default] : []
    else init[f.name] = f.default ?? ''
  }
  answers.value = init
})

function evalCondition(cond: VisibleIfCondition): boolean {
  const val = answers.value[cond.field]
  if (cond.op === 'eq') return val === cond.value
  if (cond.op === 'neq') return val !== cond.value
  if (cond.op === 'in') return Array.isArray(cond.value) && cond.value.includes(val)
  if (cond.op === 'not_in') return Array.isArray(cond.value) && !cond.value.includes(val)
  return true
}

function isVisible(f: SurveyField): boolean {
  return !f.visible_if?.length || f.visible_if.every(evalCondition)
}

const visibleFields = computed(() => fields.value.filter(isVisible))

function fieldOptions(f: SurveyField): FieldOption[] {
  if (f.options_by) {
    const parentVal = answers.value[f.options_by.field]
    const key = parentVal != null ? String(parentVal) : ''
    return f.options_by.map[key] ?? f.options_by.default ?? f.options ?? []
  }
  return f.options ?? []
}

// Clear answers that are no longer valid once their governing dropdown's options change.
watch(answers, (val) => {
  for (const f of fields.value) {
    if (!f.options_by) continue
    const current = val[f.name]
    const isEmpty = current === '' || current === undefined || current === null || (Array.isArray(current) && current.length === 0)
    if (isEmpty) continue
    const opts = fieldOptions(f)
    if (f.type === 'multiselect') {
      const filtered = (current as string[]).filter(v => opts.some(o => o.value === v))
      if (filtered.length !== current.length) val[f.name] = filtered
    } else if (!opts.some(o => o.value === current)) {
      val[f.name] = ''
    }
  }
}, { deep: true })

function toggleMultiselect(f: SurveyField, value: string) {
  const arr: string[] = Array.isArray(answers.value[f.name]) ? answers.value[f.name] : []
  const idx = arr.indexOf(value)
  if (idx === -1) arr.push(value)
  else arr.splice(idx, 1)
  answers.value[f.name] = [...arr]
}

function inputType(f: SurveyField) {
  if (f.type === 'secret') return 'password'
  if (f.type === 'int') return 'number'
  return 'text'
}

function validate(): boolean {
  errors.value = {}
  for (const f of visibleFields.value) {
    const val = answers.value[f.name]
    if (f.type === 'bool') continue
    if (f.type === 'multiselect') {
      if (f.required && (!Array.isArray(val) || val.length === 0)) {
        errors.value[f.name] = `${f.label || f.name} is required`
      }
      continue
    }
    if (f.required && !val) {
      errors.value[f.name] = `${f.label || f.name} is required`
      continue
    }
    if (f.type === 'int' && val !== '' && val != null && isNaN(Number(String(val)))) {
      errors.value[f.name] = `${f.label || f.name} must be a number`
    }
  }
  return Object.keys(errors.value).length === 0
}

function submit() {
  if (!validate()) return
  const out: Record<string, any> = {}
  for (const f of visibleFields.value) {
    const raw = answers.value[f.name]
    if (f.type === 'bool') out[f.name] = raw === true
    else if (f.type === 'int') out[f.name] = raw === '' || raw == null ? null : Number(raw)
    else if (f.type === 'multiselect') out[f.name] = Array.isArray(raw) ? raw : []
    else out[f.name] = raw ?? ''
  }
  emit('submit', out)
}
</script>

<template>
  <Teleport to="body">
    <div v-if="open && schema"
      class="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" />
      <div class="relative bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] flex flex-col">

        <!-- Header -->
        <div class="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <div class="flex items-center gap-2.5">
            <div class="p-2 rounded-full bg-teal-100">
              <ClipboardList class="w-4 h-4 text-teal-600" />
            </div>
            <div>
              <h2 class="font-semibold text-gray-900">{{ schema.title || 'Survey' }}</h2>
              <p v-if="schema.description" class="text-xs text-gray-400 mt-0.5">{{ schema.description }}</p>
            </div>
          </div>
        </div>

        <!-- Body -->
        <div class="overflow-y-auto flex-1 px-6 py-5 space-y-4">
          <p v-if="!visibleFields.length" class="text-sm text-gray-400 italic">
            No fields defined in this survey.
          </p>

          <div v-for="f in visibleFields" :key="f.name" class="space-y-1">
            <label class="flex items-center gap-1 text-xs font-medium text-gray-600">
              {{ f.label || f.name }}
              <span v-if="f.required" class="text-red-500">*</span>
            </label>

            <!-- Bool -->
            <label v-if="f.type === 'bool'" class="inline-flex items-center gap-2 cursor-pointer mt-1">
              <input type="checkbox" v-model="answers[f.name]"
                class="w-4 h-4 rounded text-teal-600 focus:ring-teal-500" />
              <span class="text-sm text-gray-700">{{ f.label || f.name }}</span>
            </label>

            <!-- Enum -->
            <select v-else-if="f.type === 'enum'" v-model="answers[f.name]"
              class="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
              :class="errors[f.name] ? 'border-red-400' : 'border-gray-300'">
              <option value="">— Select —</option>
              <option v-for="opt in fieldOptions(f)" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
            </select>

            <!-- Multiselect -->
            <div v-else-if="f.type === 'multiselect'"
              class="border rounded-lg px-3 py-2 space-y-1.5 max-h-36 overflow-y-auto"
              :class="errors[f.name] ? 'border-red-400' : 'border-gray-300'">
              <p v-if="!fieldOptions(f).length" class="text-xs text-gray-400 italic">No options available</p>
              <label v-for="opt in fieldOptions(f)" :key="opt.value" class="flex items-center gap-2 cursor-pointer">
                <input type="checkbox"
                  :checked="(answers[f.name] ?? []).includes(opt.value)"
                  @change="toggleMultiselect(f, opt.value)"
                  class="w-4 h-4 rounded text-teal-600 focus:ring-teal-500" />
                <span class="text-sm text-gray-700">{{ opt.label }}</span>
              </label>
            </div>

            <!-- Textarea -->
            <textarea v-else-if="f.type === 'textarea'" v-model="answers[f.name]"
              rows="3"
              class="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
              :class="errors[f.name] ? 'border-red-400' : 'border-gray-300'" />

            <!-- String / int / secret -->
            <input v-else v-model="answers[f.name]"
              :type="inputType(f)"
              class="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
              :class="errors[f.name] ? 'border-red-400' : 'border-gray-300'" />

            <p v-if="errors[f.name]" class="text-xs text-red-500">{{ errors[f.name] }}</p>
          </div>
        </div>

        <!-- Footer -->
        <div class="flex items-center justify-end gap-3 px-6 py-4 border-t border-gray-100">
          <button @click="emit('cancel')" :disabled="submitting || cancelling"
            class="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700 disabled:opacity-60 px-4 py-2">
            <Loader2 v-if="cancelling" class="w-4 h-4 animate-spin" />
            <XCircle v-else class="w-4 h-4" />
            Cancel
          </button>
          <button @click="submit" :disabled="submitting || cancelling"
            class="flex items-center gap-2 bg-teal-600 hover:bg-teal-700 disabled:opacity-60 text-white text-sm font-medium px-5 py-2 rounded-lg">
            <Loader2 v-if="submitting" class="w-4 h-4 animate-spin" />
            <Send v-else class="w-4 h-4" />
            Submit
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
