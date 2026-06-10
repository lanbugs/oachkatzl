<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { X, Play, ChevronDown, Package } from 'lucide-vue-next'
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

interface Template {
  id: string
  name: string
  app: string
  type: string
  allow_override_args: boolean
  arguments: string
  survey_vars: SurveyVar[]
  build_template_id?: string
}

interface Build {
  id: string
  version: string
  commit_hash?: string
  created_at: string
}

const props = defineProps<{
  template: Template | null
  open: boolean
  builds?: Build[]   // only relevant for deploy-type templates
}>()

const emit = defineEmits<{
  close: []
  run: [payload: object]
}>()

// ── Form state ────────────────────────────────────────────────────────────

const surveyAnswers = ref<Record<string, string | boolean>>({})
const argumentsOverride = ref('')
const debug = ref(false)
const dryRun = ref(false)
const diff = ref(false)
const errors = ref<Record<string, string>>({})
const showAdvanced = ref(false)
const selectedBuildTaskId = ref<string>('')

const isDeploy = computed(() => props.template?.type === 'deploy')
// Backend already returns only successful builds with a version
const availableBuilds = computed(() => props.builds ?? [])

// Reset form whenever modal opens
watch(() => props.open, (open) => {
  if (!open) return
  surveyAnswers.value = {}
  errors.value = {}
  debug.value = false
  dryRun.value = false
  diff.value = false
  showAdvanced.value = false
  selectedBuildTaskId.value = availableBuilds.value[0]?.id ?? ''
  argumentsOverride.value = defaultArgs.value

  // Pre-fill defaults
  props.template?.survey_vars?.forEach(sv => {
    if (sv.type === 'separator') return
    if (sv.type === 'bool') {
      surveyAnswers.value[sv.name] = sv.default === 'true'
    } else if (sv.default) {
      surveyAnswers.value[sv.name] = sv.default
    }
  })
})

const defaultArgs = computed(() => {
  if (!props.template) return ''
  try {
    const arr = JSON.parse(props.template.arguments || '[]')
    return Array.isArray(arr) ? arr.join('\n') : ''
  } catch { return '' }
})

const isAnsible = computed(() => props.template?.app === 'ansible')
const hasSurvey = computed(() => (props.template?.survey_vars?.length ?? 0) > 0)
const hasArgOverride = computed(() => props.template?.allow_override_args)

function inputType(sv: SurveyVar): string {
  if (sv.type === 'secret') return 'password'
  if (sv.type === 'int') return 'number'
  return 'text'
}

function validate(): boolean {
  errors.value = {}
  // Deploy type: must select a build version
  if (isDeploy.value && !selectedBuildTaskId.value) {
    errors.value['_build'] = 'Please select a build version to deploy'
  }
  for (const sv of props.template?.survey_vars ?? []) {
    if (sv.type === 'separator') continue
    const val = surveyAnswers.value[sv.name]
    if (sv.type !== 'bool' && sv.required && !val) {
      errors.value[sv.name] = `${sv.title || sv.name} is required`
    }
    if (sv.type === 'int' && val && isNaN(Number(String(val)))) {
      errors.value[sv.name] = `${sv.title || sv.name} must be a number`
    }
  }
  return Object.keys(errors.value).length === 0
}

function submit() {
  if (!validate()) return

  // Build survey_answers: cast ints
  const answers: Record<string, any> = {}
  for (const sv of props.template?.survey_vars ?? []) {
    const raw = surveyAnswers.value[sv.name] ?? sv.default ?? ''
    if (sv.type === 'separator') continue
    if (sv.type === 'bool') answers[sv.name] = surveyAnswers.value[sv.name] === true
    else answers[sv.name] = sv.type === 'int' ? Number(raw) : raw
  }

  // Build arguments override
  let argsOverride: string[] = []
  if (hasArgOverride.value && argumentsOverride.value.trim()) {
    argsOverride = argumentsOverride.value.split('\n').map(l => l.trim()).filter(Boolean)
  }

  emit('run', {
    debug: debug.value,
    dry_run: dryRun.value,
    diff: diff.value,
    survey_answers: JSON.stringify(answers),
    arguments_override: JSON.stringify(argsOverride),
    environment_override: '{}',
    build_task_id: isDeploy.value ? (selectedBuildTaskId.value || null) : null,
  })
}
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open && template"
      class="fixed inset-0 z-50 flex items-center justify-center p-4"
      @click.self="$emit('close')"
    >
      <!-- Backdrop -->
      <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" />

      <!-- Modal -->
      <div class="relative bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] flex flex-col">
        <!-- Header -->
        <div class="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <div>
            <h2 class="font-semibold text-gray-900">Run task</h2>
            <p class="text-xs text-gray-400 mt-0.5">{{ template.name }}</p>
          </div>
          <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600 transition-colors">
            <X class="w-5 h-5" />
          </button>
        </div>

        <!-- Body -->
        <div class="overflow-y-auto flex-1 px-6 py-5 space-y-5">

          <!-- Deploy: build version picker -->
          <div v-if="isDeploy" class="space-y-3">
            <div class="flex items-center gap-2">
              <Package class="w-4 h-4 text-orange-500" />
              <h3 class="text-sm font-medium text-gray-700">Select build version to deploy</h3>
            </div>
            <div v-if="availableBuilds.length === 0"
              class="text-sm text-orange-600 bg-orange-50 border border-orange-200 rounded-lg px-3 py-2">
              No successful builds found. Run a build task first.
            </div>
            <template v-else>
              <select
                v-model="selectedBuildTaskId"
                class="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                :class="errors['_build'] ? 'border-red-400' : 'border-gray-300'"
              >
                <option value="">— Select version —</option>
                <option v-for="b in availableBuilds" :key="b.id" :value="b.id">
                  v{{ b.version }}
                  {{ b.commit_hash ? `· ${b.commit_hash.slice(0, 8)}` : '' }}
                  · {{ new Date(b.created_at).toLocaleString() }}
                </option>
              </select>
              <p v-if="errors['_build']" class="text-xs text-red-500">{{ errors['_build'] }}</p>
              <p class="text-xs text-gray-400">
                Only successful builds are shown.
                The version is available in the script as <code class="bg-gray-100 px-1 rounded">$OACHKATZL_BUILD_VERSION</code>.
              </p>
            </template>
          </div>

          <!-- Survey variables -->
          <div v-if="hasSurvey" class="space-y-4">
            <h3 class="text-sm font-medium text-gray-700">Variables</h3>
            <div v-for="sv in template.survey_vars" :key="sv.name" class="space-y-1">
              <template v-if="sv.type !== 'separator' && sv.type !== 'bool'">
                <label class="flex items-center gap-1 text-xs font-medium text-gray-600">
                  {{ sv.title || sv.name }}
                  <span v-if="sv.required" class="text-red-500">*</span>
                </label>
                <p v-if="sv.description" class="text-xs text-gray-400">{{ sv.description }}</p>
              </template>

              <!-- Enum → select -->
              <select
                v-if="sv.type === 'enum'"
                v-model="surveyAnswers[sv.name]"
                class="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                :class="errors[sv.name] ? 'border-red-400' : 'border-gray-300'"
              >
                <option value="">— Select —</option>
                <option
                  v-for="opt in parseEnumOptions(sv.values)"
                  :key="opt.value"
                  :value="opt.value"
                >{{ opt.label }}</option>
              </select>

              <!-- Separator → visual divider -->
              <div v-if="sv.type === 'separator'" class="-mx-1 pt-1">
                <div class="flex items-center gap-3">
                  <div class="flex-1 h-px bg-gray-200"></div>
                  <span v-if="sv.title" class="text-xs font-semibold text-gray-400 uppercase tracking-wider">{{ sv.title }}</span>
                  <div v-if="sv.title" class="flex-1 h-px bg-gray-200"></div>
                </div>
              </div>

              <!-- Bool → toggle (title used as label) -->
              <label
                v-else-if="sv.type === 'bool'"
                class="inline-flex items-center gap-2 cursor-pointer select-none mt-1"
              >
                <input
                  type="checkbox"
                  v-model="surveyAnswers[sv.name]"
                  class="w-4 h-4 rounded text-brand-600 focus:ring-brand-500"
                />
                <span class="text-sm text-gray-700">{{ sv.title || sv.name }}</span>
              </label>

              <!-- Others → input -->
              <input
                v-else
                v-model="surveyAnswers[sv.name]"
                :type="inputType(sv)"
                :placeholder="sv.default || ''"
                class="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                :class="errors[sv.name] ? 'border-red-400' : 'border-gray-300'"
              />
              <p v-if="errors[sv.name]" class="text-xs text-red-500">{{ errors[sv.name] }}</p>
            </div>
          </div>

          <!-- No survey vars info -->
          <p v-else class="text-sm text-gray-400 italic">No survey variables defined for this template.</p>

          <!-- Advanced options toggle -->
          <button
            type="button"
            @click="showAdvanced = !showAdvanced"
            class="flex items-center gap-1.5 text-xs text-gray-400 hover:text-gray-600 transition-colors"
          >
            <ChevronDown class="w-3.5 h-3.5 transition-transform" :class="{ 'rotate-180': showAdvanced }" />
            Advanced options
          </button>

          <div v-if="showAdvanced" class="space-y-4 border-t border-gray-100 pt-4">
            <!-- Run flags -->
            <div class="space-y-2">
              <h3 class="text-xs font-medium text-gray-600">Run flags</h3>
              <label class="flex items-center gap-2 text-sm text-gray-700">
                <input v-model="debug" type="checkbox" class="rounded" />
                Debug mode <span class="text-xs text-gray-400">(verbose output)</span>
              </label>
              <label v-if="isAnsible" class="flex items-center gap-2 text-sm text-gray-700">
                <input v-model="dryRun" type="checkbox" class="rounded" />
                Dry run / Check mode <span class="text-xs text-gray-400">(<code>--check</code>)</span>
              </label>
              <label v-if="isAnsible" class="flex items-center gap-2 text-sm text-gray-700">
                <input v-model="diff" type="checkbox" class="rounded" />
                Show diff <span class="text-xs text-gray-400">(<code>--diff</code>)</span>
              </label>
            </div>

            <!-- Argument override -->
            <div v-if="hasArgOverride" class="space-y-1">
              <label class="block text-xs font-medium text-gray-600">Override arguments (one per line)</label>
              <textarea
                v-model="argumentsOverride"
                rows="3"
                class="w-full border border-gray-300 rounded-lg px-3 py-2 text-xs font-mono focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>
          </div>
        </div>

        <!-- Footer -->
        <div class="flex items-center justify-end gap-3 px-6 py-4 border-t border-gray-100">
          <button @click="$emit('close')" class="text-sm text-gray-500 hover:text-gray-700">Cancel</button>
          <button
            @click="submit"
            class="flex items-center gap-2 bg-green-600 hover:bg-green-700 text-white text-sm font-medium px-5 py-2 rounded-lg transition-colors"
          >
            <Play class="w-4 h-4" /> Run
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
