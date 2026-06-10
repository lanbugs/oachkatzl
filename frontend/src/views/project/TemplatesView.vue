<script setup lang="ts">
import { onMounted, computed, ref, watch } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import { useProjectsStore } from '@/stores/projects'
import { projectsApi } from '@/api/projects'
import { Play, Plus, Pencil, Trash2, Terminal, Server, Code2, Puzzle, Key, ChevronLeft, ChevronRight } from 'lucide-vue-next'
import RunTaskModal from '@/components/RunTaskModal.vue'
import TemplateTokensModal from '@/components/TemplateTokensModal.vue'

const route = useRoute()
const router = useRouter()
const store = useProjectsStore()
const projectId = computed(() => route.params.projectId as string)

const runTarget    = ref<any>(null)
const runBuilds    = ref<any[]>([])
const tokenTarget  = ref<any>(null)
const loadingTemplate = ref<string | null>(null)

// ── Pagination state ──────────────────────────────────────────────────────
const PER_PAGE = 20
const page  = ref(1)
const total = ref(0)
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / PER_PAGE)))

async function load() {
  const { data } = await projectsApi.listTemplates(projectId.value, page.value, PER_PAGE)
  // Response is { items, total, page, per_page }
  store.templates = [...(data.items ?? [])].sort((a: any, b: any) => a.name.localeCompare(b.name))
  total.value = data.total ?? store.templates.length
}

onMounted(load)
watch(page, load)

function prevPage() { if (page.value > 1) page.value-- }
function nextPage() { if (page.value < totalPages.value) page.value++ }
// ─────────────────────────────────────────────────────────────────────────

const appIcons: Record<string, any> = { ansible: Server, bash: Terminal, python: Code2 }
const typeColors: Record<string, string> = {
  task: 'bg-blue-50 text-blue-700',
  build: 'bg-green-50 text-green-700',
  deploy: 'bg-orange-50 text-orange-700',
}

async function openRun(templateId: string) {
  loadingTemplate.value = templateId
  runBuilds.value = []
  try {
    const { data } = await projectsApi.getTemplate(projectId.value, templateId)
    runTarget.value = data
    if (data.type === 'deploy' && data.build_template_id) {
      try {
        const { data: builds } = await projectsApi.listBuilds(projectId.value, data.build_template_id)
        runBuilds.value = builds
      } catch { /* modal shows "no builds" */ }
    }
  } finally {
    loadingTemplate.value = null
  }
}

async function handleRun(payload: object) {
  if (!runTarget.value) return
  try {
    const { data } = await projectsApi.startTask(projectId.value, runTarget.value.id, payload)
    runTarget.value = null
    router.push(`/projects/${projectId.value}/tasks/${data.id}`)
  } catch (e: any) {
    alert(e.response?.data?.message || 'Failed to start task')
  }
}

async function deleteTemplate(id: string) {
  if (!confirm('Delete this template?')) return
  await projectsApi.deleteTemplate(projectId.value, id)
  // Stay on current page but reload; go back a page if it's now empty
  if (store.templates.length === 1 && page.value > 1) page.value--
  else await load()
}
</script>

<template>
  <div>
    <div class="flex justify-between items-center mb-4">
      <h2 class="text-lg font-medium text-gray-900">Templates</h2>
      <RouterLink v-if="store.canManage" :to="`/projects/${projectId}/templates/new`"
        class="flex items-center gap-2 bg-brand-600 hover:bg-brand-700 text-white text-sm px-3 py-1.5 rounded-lg">
        <Plus class="w-4 h-4" /> New template
      </RouterLink>
    </div>

    <div class="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
      <div v-if="store.templates.length === 0" class="p-8 text-center text-gray-400 text-sm">
        No templates yet.
        <RouterLink :to="`/projects/${projectId}/templates/new`" class="text-brand-600 hover:underline">Create one →</RouterLink>
      </div>
      <div v-for="t in store.templates" :key="t.id" class="flex items-center justify-between px-5 py-4">
        <div class="flex items-center gap-3 min-w-0">
          <div class="p-1.5 rounded bg-gray-100 shrink-0">
            <component :is="appIcons[t.app] || Puzzle" class="w-4 h-4 text-gray-500" />
          </div>
          <div class="min-w-0">
            <div class="flex items-center gap-2 flex-wrap">
              <p class="font-medium text-gray-900 truncate">{{ t.name }}</p>
              <span class="text-xs px-1.5 py-0.5 rounded font-medium shrink-0"
                :class="typeColors[t.type] || 'bg-gray-100 text-gray-600'">{{ t.type }}</span>
              <span v-if="t.survey_vars?.length"
                class="text-xs bg-yellow-50 text-yellow-700 px-1.5 py-0.5 rounded shrink-0">
                {{ t.survey_vars.length }} survey var{{ t.survey_vars.length !== 1 ? 's' : '' }}
              </span>
            </div>
            <p class="text-xs text-gray-400 mt-0.5 truncate">
              {{ t.app }}<span v-if="t.playbook"> · {{ t.playbook }}</span>
              <span v-if="t.description" class="italic"> · {{ t.description }}</span>
            </p>
          </div>
        </div>
        <div class="flex items-center gap-2 ml-4 shrink-0">
          <button v-if="store.canRun" @click="openRun(t.id)" :disabled="loadingTemplate === t.id"
            class="flex items-center gap-1.5 bg-green-600 hover:bg-green-700 text-white text-xs px-3 py-1.5 rounded-lg disabled:opacity-60 transition-colors">
            <Play class="w-3.5 h-3.5" />{{ loadingTemplate === t.id ? '…' : 'Run' }}
          </button>
          <button v-if="store.canManage" @click="tokenTarget = t"
            class="p-1.5 text-gray-400 hover:text-brand-600 transition-colors" title="Execute tokens">
            <Key class="w-4 h-4" />
          </button>
          <RouterLink v-if="store.canManage" :to="`/projects/${projectId}/templates/${t.id}/edit`"
            class="p-1.5 text-gray-400 hover:text-brand-600 transition-colors">
            <Pencil class="w-4 h-4" />
          </RouterLink>
          <button v-if="store.canManage" @click="deleteTemplate(t.id)"
            class="p-1.5 text-gray-300 hover:text-red-500 transition-colors">
            <Trash2 class="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>

    <!-- Pagination -->
    <div v-if="total > PER_PAGE" class="flex items-center justify-between mt-4">
      <p class="text-xs text-gray-400">
        {{ (page - 1) * PER_PAGE + 1 }}–{{ Math.min(page * PER_PAGE, total) }} of {{ total }}
      </p>
      <div class="flex items-center gap-1">
        <button @click="prevPage" :disabled="page === 1"
          class="p-1.5 rounded-lg border border-gray-200 text-gray-500 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors">
          <ChevronLeft class="w-4 h-4" />
        </button>
        <template v-for="p in totalPages" :key="p">
          <button
            v-if="totalPages <= 7 || p === 1 || p === totalPages || Math.abs(p - page) <= 1"
            @click="page = p"
            class="min-w-[2rem] h-8 rounded-lg border text-xs font-medium transition-colors"
            :class="p === page
              ? 'bg-brand-600 text-white border-brand-600'
              : 'border-gray-200 text-gray-600 hover:bg-gray-50'"
          >{{ p }}</button>
          <span v-else-if="Math.abs(p - page) === 2" class="px-1 text-gray-400 text-xs">…</span>
        </template>
        <button @click="nextPage" :disabled="page === totalPages"
          class="p-1.5 rounded-lg border border-gray-200 text-gray-500 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors">
          <ChevronRight class="w-4 h-4" />
        </button>
      </div>
    </div>

    <RunTaskModal :template="runTarget" :open="!!runTarget" :builds="runBuilds" @close="runTarget = null" @run="handleRun" />

    <TemplateTokensModal
      :open="!!tokenTarget"
      :project-id="projectId"
      :template="tokenTarget"
      @close="tokenTarget = null"
    />
  </div>
</template>
