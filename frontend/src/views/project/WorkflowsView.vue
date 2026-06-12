<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import { useProjectsStore } from '@/stores/projects'
import { projectsApi } from '@/api/projects'
import { Plus, Play, Pencil, Trash2, GitMerge, ChevronRight } from 'lucide-vue-next'
import RunWorkflowModal from '@/components/RunWorkflowModal.vue'

const route = useRoute()
const router = useRouter()
const store = useProjectsStore()
const projectId = computed(() => route.params.projectId as string)

const workflows = ref<any[]>([])
const lastRuns = ref<Record<string, any>>({})
const loading = ref(false)
const runModalWorkflow = ref<any>(null)

async function load() {
  loading.value = true
  try {
    const { data } = await projectsApi.listWorkflows(projectId.value)
    workflows.value = data.items ?? []
    // Load last run for each workflow
    for (const wf of workflows.value) {
      try {
        const { data: runsData } = await projectsApi.listWorkflowRuns(projectId.value, 1, 1)
        // Filter by workflow_id on the frontend since we don't have a per-workflow filter endpoint
        const allRuns = runsData.items ?? []
        const wfRun = allRuns.find((r: any) => r.workflow_id === wf.id)
        if (wfRun) lastRuns.value[wf.id] = wfRun
      } catch {
        // ignore
      }
    }
    // Better: load all recent runs once and find last run per workflow
    try {
      const { data: runsData } = await projectsApi.listWorkflowRuns(projectId.value, 1, 100)
      const allRuns: any[] = runsData.items ?? []
      for (const wf of workflows.value) {
        const wfRun = allRuns.find((r: any) => r.workflow_id === wf.id)
        if (wfRun) lastRuns.value[wf.id] = wfRun
      }
    } catch {
      // ignore
    }
  } finally {
    loading.value = false
  }
}

onMounted(load)

const statusColors: Record<string, string> = {
  success: 'bg-green-100 text-green-700',
  error: 'bg-red-100 text-red-700',
  running: 'bg-blue-100 text-blue-700',
  waiting: 'bg-gray-100 text-gray-500',
  stopped: 'bg-orange-100 text-orange-700',
}

function startWorkflow(wf: any) {
  runModalWorkflow.value = wf
}

async function doStart(surveyAnswers: string) {
  const wf = runModalWorkflow.value
  if (!wf) return
  runModalWorkflow.value = null
  try {
    const { data } = await projectsApi.startWorkflow(projectId.value, wf.id, {
      survey_answers: surveyAnswers,
    })
    router.push(`/projects/${projectId.value}/workflow-runs/${data.id}`)
  } catch (e: any) {
    alert(e.response?.data?.message || 'Failed to start workflow')
  }
}

async function deleteWorkflow(wf: any) {
  if (!confirm(`Delete workflow "${wf.name}"? This cannot be undone.`)) return
  try {
    await projectsApi.deleteWorkflow(projectId.value, wf.id)
    await load()
  } catch (e: any) {
    alert(e.response?.data?.message || 'Failed to delete workflow')
  }
}
</script>

<template>
  <div>
    <RunWorkflowModal
      :workflow="runModalWorkflow"
      :open="!!runModalWorkflow"
      @close="runModalWorkflow = null"
      @run="doStart"
    />
    <div class="flex justify-between items-center mb-4">
      <h2 class="text-lg font-medium text-gray-900">Workflows</h2>
      <RouterLink
        v-if="store.canManage"
        :to="`/projects/${projectId}/workflows/new`"
        class="flex items-center gap-2 bg-brand-600 hover:bg-brand-700 text-white text-sm px-3 py-1.5 rounded-lg"
      >
        <Plus class="w-4 h-4" /> New workflow
      </RouterLink>
    </div>

    <div class="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
      <div v-if="loading" class="p-8 text-center text-gray-400 text-sm">Loading…</div>
      <div v-else-if="workflows.length === 0" class="p-8 text-center text-gray-400 text-sm">
        No workflows yet.
        <RouterLink
          v-if="store.canManage"
          :to="`/projects/${projectId}/workflows/new`"
          class="text-brand-600 hover:underline"
        >Create one →</RouterLink>
      </div>

      <div
        v-for="wf in workflows"
        :key="wf.id"
        class="flex items-center justify-between px-5 py-4"
      >
        <div class="flex items-center gap-3 min-w-0">
          <div class="p-1.5 rounded bg-gray-100 shrink-0">
            <GitMerge class="w-4 h-4 text-gray-500" />
          </div>
          <div class="min-w-0">
            <div class="flex items-center gap-2 flex-wrap">
              <p class="font-medium text-gray-900 truncate">{{ wf.name }}</p>
              <span class="text-xs bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded shrink-0">
                {{ wf.nodes?.length ?? 0 }} node{{ (wf.nodes?.length ?? 0) !== 1 ? 's' : '' }}
              </span>
              <span
                v-if="lastRuns[wf.id]"
                class="text-xs px-1.5 py-0.5 rounded shrink-0"
                :class="statusColors[lastRuns[wf.id].status] ?? 'bg-gray-100 text-gray-500'"
              >
                {{ lastRuns[wf.id].status }}
              </span>
            </div>
            <p v-if="wf.description" class="text-xs text-gray-400 mt-0.5 truncate italic">
              {{ wf.description }}
            </p>
          </div>
        </div>

        <div class="flex items-center gap-2 ml-4 shrink-0">
          <!-- Last run link -->
          <RouterLink
            v-if="lastRuns[wf.id]"
            :to="`/projects/${projectId}/workflow-runs/${lastRuns[wf.id].id}`"
            class="p-1.5 text-gray-400 hover:text-brand-600 transition-colors"
            title="View last run"
          >
            <ChevronRight class="w-4 h-4" />
          </RouterLink>

          <button
            v-if="store.canRun"
            @click="startWorkflow(wf)"
            class="flex items-center gap-1.5 bg-green-600 hover:bg-green-700 text-white text-xs px-3 py-1.5 rounded-lg transition-colors"
          >
            <Play class="w-3.5 h-3.5" /> Run
          </button>

          <RouterLink
            v-if="store.canManage"
            :to="`/projects/${projectId}/workflows/${wf.id}/edit`"
            class="p-1.5 text-gray-400 hover:text-brand-600 transition-colors"
          >
            <Pencil class="w-4 h-4" />
          </RouterLink>

          <button
            v-if="store.canManage"
            @click="deleteWorkflow(wf)"
            class="p-1.5 text-gray-300 hover:text-red-500 transition-colors"
          >
            <Trash2 class="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
