<script setup lang="ts">
import { onMounted, ref, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useProjectsStore } from '@/stores/projects'
import { projectsApi } from '@/api/projects'
import { parseEnumOptions } from '@/composables/useEnumOptions'
import { Clock, Plus, Trash2, ToggleLeft, ToggleRight, Pencil, X } from 'lucide-vue-next'

const route = useRoute()
const store = useProjectsStore()
const projectId = computed(() => route.params.projectId as string)

const schedules = ref<any[]>([])
const templates = ref<any[]>([])
const showForm = ref(false)
const editId = ref<string | null>(null)
const saving = ref(false)
const toggling = ref<string | null>(null)
const loadingTemplate = ref(false)
const selectedTemplate = ref<any>(null)
const surveyAnswers = ref<Record<string, string>>({})

const emptyForm = () => ({ template_id: '', cron_format: '0 * * * *', active: true })
const form = ref(emptyForm())

onMounted(async () => {
  const [schedRes, tmplRes] = await Promise.all([
    projectsApi.listSchedules(projectId.value),
    projectsApi.listTemplates(projectId.value),
  ])
  schedules.value = schedRes.data
  templates.value = tmplRes.data?.items ?? tmplRes.data ?? []
})

watch(() => form.value.template_id, async (tid) => {
  if (!tid) { selectedTemplate.value = null; surveyAnswers.value = {}; return }
  loadingTemplate.value = true
  try {
    const { data } = await projectsApi.getTemplate(projectId.value, tid)
    selectedTemplate.value = data
    const current = { ...surveyAnswers.value }
    surveyAnswers.value = {}
    for (const sv of data.survey_vars || []) {
      surveyAnswers.value[sv.name] = current[sv.name] ?? sv.default ?? ''
    }
  } finally {
    loadingTemplate.value = false
  }
})

const hasSurvey = computed(() => (selectedTemplate.value?.survey_vars?.length ?? 0) > 0)

function templateName(id: string) {
  return templates.value.find(t => t.id === id)?.name || id
}

function inputType(type: string) {
  if (type === 'secret') return 'password'
  if (type === 'int') return 'number'
  return 'text'
}

function startEdit(s: any) {
  editId.value = s.id
  form.value = { template_id: s.template_id, cron_format: s.cron_format, active: s.active }
  try { surveyAnswers.value = JSON.parse(s.survey_answers || '{}') } catch { surveyAnswers.value = {} }
  showForm.value = true
}

function cancel() {
  editId.value = null
  showForm.value = false
  form.value = emptyForm()
  selectedTemplate.value = null
  surveyAnswers.value = {}
}

async function save() {
  saving.value = true
  try {
    const payload = { ...form.value, survey_answers: JSON.stringify(surveyAnswers.value) }
    if (editId.value) {
      const { data } = await projectsApi.updateSchedule(projectId.value, editId.value, payload)
      const idx = schedules.value.findIndex(s => s.id === editId.value)
      if (idx !== -1) schedules.value[idx] = data
    } else {
      const { data } = await projectsApi.createSchedule(projectId.value, payload)
      schedules.value.push(data)
    }
    cancel()
  } finally {
    saving.value = false
  }
}

async function toggleActive(s: any) {
  toggling.value = s.id
  try {
    const { data } = await projectsApi.updateSchedule(projectId.value, s.id, {
      template_id: s.template_id, cron_format: s.cron_format,
      active: !s.active, survey_answers: s.survey_answers || '{}',
    })
    const idx = schedules.value.findIndex(x => x.id === s.id)
    if (idx !== -1) schedules.value[idx] = data
  } finally {
    toggling.value = null
  }
}

async function deleteSchedule(id: string) {
  if (!confirm('Delete this schedule?')) return
  await projectsApi.deleteSchedule(projectId.value, id)
  schedules.value = schedules.value.filter(s => s.id !== id)
}

function surveyAnswerCount(s: any): number {
  try { return Object.keys(JSON.parse(s.survey_answers || '{}')).filter(k => k).length } catch { return 0 }
}

const cronExamples = [
  { label: 'Every hour',     value: '0 * * * *' },
  { label: 'Every 6 h',     value: '0 */6 * * *' },
  { label: 'Daily midnight', value: '0 0 * * *' },
  { label: 'Daily 8 AM',    value: '0 8 * * *' },
  { label: 'Mon 9 AM',      value: '0 9 * * 1' },
  { label: 'Every 30 min',  value: '*/30 * * * *' },
]
</script>

<template>
  <div>
    <div class="flex justify-between items-center mb-4">
      <div>
        <h2 class="text-lg font-medium text-gray-900">Schedules</h2>
        <p class="text-xs text-gray-400 mt-0.5">Cron-based automatic task execution via Celery Beat.</p>
      </div>
      <button v-if="store.canManage"
        @click="showForm = true; editId = null; form = emptyForm(); surveyAnswers = {}; selectedTemplate = null"
        class="flex items-center gap-2 bg-brand-600 hover:bg-brand-700 text-white text-sm px-3 py-1.5 rounded-lg">
        <Plus class="w-4 h-4" /> New schedule
      </button>
    </div>

    <!-- Form -->
    <div v-if="showForm" class="mb-4 bg-white rounded-xl border border-brand-200 p-5 space-y-4">
      <div class="flex items-center justify-between">
        <h3 class="font-medium text-gray-900">{{ editId ? 'Edit schedule' : 'New schedule' }}</h3>
        <button @click="cancel" class="text-gray-400 hover:text-gray-600"><X class="w-4 h-4" /></button>
      </div>

      <form @submit.prevent="save" class="space-y-4">
        <!-- Template -->
        <div>
          <label class="block text-xs font-medium text-gray-600 mb-1">Template *</label>
          <select v-model="form.template_id" required class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
            <option value="">— Select template —</option>
            <option v-for="t in templates" :key="t.id" :value="t.id">{{ t.name }}</option>
          </select>
        </div>

        <div v-if="loadingTemplate" class="text-xs text-gray-400 italic py-1">Loading template…</div>

        <!-- Survey variables -->
        <div v-if="hasSurvey" class="border border-gray-200 rounded-xl p-4 space-y-3 bg-gray-50">
          <p class="text-xs font-semibold text-gray-600 uppercase tracking-wide">
            Survey variables
            <span class="normal-case font-normal text-gray-400 ml-1">— pre-filled for every scheduled run</span>
          </p>

          <div v-for="sv in selectedTemplate.survey_vars" :key="sv.name" class="space-y-1">
            <label class="flex items-center gap-1 text-xs font-medium text-gray-600">
              {{ sv.title || sv.name }}
              <span v-if="sv.required" class="text-red-500">*</span>
              <span class="text-gray-400 font-normal">({{ sv.type }})</span>
            </label>
            <p v-if="sv.description" class="text-xs text-gray-400">{{ sv.description }}</p>

            <select v-if="sv.type === 'enum'" v-model="surveyAnswers[sv.name]"
              class="w-full border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500">
              <option value="">— Select —</option>
              <option v-for="opt in parseEnumOptions(sv.values)" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </option>
            </select>

            <input v-else v-model="surveyAnswers[sv.name]"
              :type="inputType(sv.type)"
              :placeholder="sv.default ? `Default: ${sv.default}` : ''"
              class="w-full border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </div>

          <p class="text-xs text-amber-600 bg-amber-50 border border-amber-100 rounded-lg px-3 py-2">
            ⚠ Required vars without a value here fall back to the template default.
            If neither is set the schedule run is skipped with a log error.
          </p>
        </div>

        <!-- Cron -->
        <div>
          <label class="block text-xs font-medium text-gray-600 mb-1">Cron expression *</label>
          <input v-model="form.cron_format" required
            class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono" placeholder="0 * * * *" />
          <div class="flex flex-wrap gap-2 mt-2">
            <button v-for="ex in cronExamples" :key="ex.value" type="button"
              @click="form.cron_format = ex.value"
              class="text-xs bg-gray-100 hover:bg-gray-200 text-gray-600 px-2 py-1 rounded transition-colors">
              {{ ex.label }} <code class="ml-1 text-gray-400">{{ ex.value }}</code>
            </button>
          </div>
          <p class="text-xs text-gray-400 mt-2">
            <code>minute hour day month weekday</code> ·
            <a href="https://crontab.guru" target="_blank" class="text-brand-600 hover:underline">crontab.guru →</a>
          </p>
        </div>

        <label class="flex items-center gap-2 text-sm">
          <input v-model="form.active" type="checkbox" class="rounded" />
          Active (run on schedule)
        </label>

        <div class="flex gap-3">
          <button type="submit" :disabled="saving"
            class="bg-brand-600 hover:bg-brand-700 text-white text-sm px-4 py-2 rounded-lg disabled:opacity-60">
            {{ saving ? 'Saving…' : editId ? 'Save changes' : 'Create schedule' }}
          </button>
          <button type="button" @click="cancel" class="text-sm text-gray-500 hover:text-gray-700">Cancel</button>
        </div>
      </form>
    </div>

    <!-- List -->
    <div class="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
      <div v-if="schedules.length === 0" class="p-6 text-center text-gray-400 text-sm">No schedules yet.</div>
      <div v-for="s in schedules" :key="s.id" class="flex items-center justify-between px-5 py-4">
        <div class="flex items-center gap-3 min-w-0">
          <Clock class="w-4 h-4 text-gray-400 shrink-0" />
          <div class="min-w-0">
            <p class="text-sm font-medium text-gray-900">{{ templateName(s.template_id) }}</p>
            <div class="flex items-center gap-2 mt-0.5">
              <code class="text-xs text-gray-400">{{ s.cron_format }}</code>
              <span v-if="surveyAnswerCount(s) > 0"
                class="text-xs bg-yellow-50 text-yellow-700 px-1.5 py-0.5 rounded">
                {{ surveyAnswerCount(s) }} survey answer{{ surveyAnswerCount(s) !== 1 ? 's' : '' }}
              </span>
            </div>
          </div>
        </div>
        <div class="flex items-center gap-2 ml-4 shrink-0">
          <span class="text-xs px-2 py-0.5 rounded-full font-medium"
            :class="s.active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'">
            {{ s.active ? 'Active' : 'Paused' }}
          </span>
          <button v-if="store.canManage" @click="toggleActive(s)" :disabled="toggling === s.id"
            class="text-gray-400 hover:text-brand-600 transition-colors disabled:opacity-50">
            <component :is="s.active ? ToggleRight : ToggleLeft" class="w-5 h-5" />
          </button>
          <button v-if="store.canManage" @click="startEdit(s)" class="p-1 text-gray-400 hover:text-brand-600 transition-colors">
            <Pencil class="w-4 h-4" />
          </button>
          <button v-if="store.canManage" @click="deleteSchedule(s.id)" class="p-1 text-gray-300 hover:text-red-500 transition-colors">
            <Trash2 class="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
