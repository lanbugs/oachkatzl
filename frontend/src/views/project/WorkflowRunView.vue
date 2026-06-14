<script setup lang="ts">
import { onMounted, onUnmounted, ref, computed } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import { projectsApi } from '@/api/projects'
import { StopCircle, Loader2, ArrowLeft, GitMerge, HelpCircle, CheckCircle, XCircle } from 'lucide-vue-next'
import WorkflowGraph from '@/components/WorkflowGraph.vue'
import type { GraphNode } from '@/components/WorkflowGraph.vue'
import api from '@/api/client'

const route = useRoute()
const router = useRouter()
const projectId = computed(() => route.params.projectId as string)
const runId = computed(() => route.params.runId as string)

const run = ref<any>(null)
const stopping = ref(false)

// Approval state
const approvalInfo = ref<{ node_id: string; title: string; text: string } | null>(null)
const approving = ref(false)
const rejecting = ref(false)

const RUNNING_STATUSES = new Set(['waiting', 'running', 'waiting_approval'])
const RUNNING_NODE_STATUSES = new Set(['pending', 'running', 'waiting_approval'])

let pollTimer: ReturnType<typeof setInterval> | null = null

function isRunning(): boolean {
  return run.value && RUNNING_STATUSES.has(run.value.status)
}

async function poll() {
  try {
    const { data } = await projectsApi.getWorkflowRun(projectId.value, runId.value)
    run.value = data
    if (data.status === 'waiting_approval' && !approvalInfo.value) {
      fetchApprovalInfo()
    } else if (data.status !== 'waiting_approval') {
      approvalInfo.value = null
    }
    if (!isRunning()) stopPoll()
  } catch {
    // keep polling on network error
  }
}

async function fetchApprovalInfo() {
  try {
    const { data } = await api.get(`/projects/${projectId.value}/workflow-runs/${runId.value}/approval`)
    approvalInfo.value = data
  } catch {
    approvalInfo.value = { node_id: '', title: 'Proceed?', text: '' }
  }
}

async function approve() {
  approving.value = true
  try {
    await api.post(`/projects/${projectId.value}/workflow-runs/${runId.value}/approve`)
    approvalInfo.value = null
    await poll()
    if (isRunning()) startPoll()
  } catch (e: any) {
    alert(e.response?.data?.message || 'Failed to approve')
  } finally {
    approving.value = false
  }
}

async function reject() {
  rejecting.value = true
  try {
    await api.post(`/projects/${projectId.value}/workflow-runs/${runId.value}/reject`)
    approvalInfo.value = null
    await poll()
  } catch (e: any) {
    alert(e.response?.data?.message || 'Failed to reject')
  } finally {
    rejecting.value = false
  }
}

function startPoll() {
  if (pollTimer) return
  pollTimer = setInterval(poll, 2000)
}

function stopPoll() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

onMounted(async () => {
  await poll()
  if (isRunning()) startPoll()
})

onUnmounted(stopPoll)

async function stopRun() {
  stopping.value = true
  try {
    await projectsApi.stopWorkflowRun(projectId.value, runId.value)
    await poll()
  } catch (e: any) {
    alert(e.response?.data?.message || 'Failed to stop run')
  } finally {
    stopping.value = false
  }
}

// Status styling
const statusBadgeClass: Record<string, string> = {
  pending:          'bg-gray-100 text-gray-500',
  running:          'bg-blue-100 text-blue-700',
  success:          'bg-green-100 text-green-700',
  error:            'bg-red-100 text-red-700',
  skipped:          'bg-gray-100 text-gray-400',
  stopped:          'bg-orange-100 text-orange-700',
  waiting:          'bg-gray-100 text-gray-500',
  waiting_approval: 'bg-amber-100 text-amber-700',
}

const runStatusColor: Record<string, string> = {
  waiting:          'text-gray-500',
  running:          'text-blue-600',
  success:          'text-green-600',
  error:            'text-red-600',
  stopped:          'text-orange-500',
  waiting_approval: 'text-amber-600',
}

const runStatusLabel: Record<string, string> = {
  waiting:          'Waiting',
  running:          'Running',
  success:          'Success',
  error:            'Failed',
  stopped:          'Stopped',
  waiting_approval: 'Awaiting Approval',
}

function nodeLabel(nr: any): string {
  return nr.label || nr.node_id?.slice(-8) || '?'
}

const graphNodes = computed<GraphNode[]>(() => {
  if (!run.value?.node_runs) return []
  return run.value.node_runs.map((nr: any) => ({
    node_id:       nr.node_id,
    node_type:     nr.node_type || 'task',
    label:         nr.label || '',
    template_name: nr.template_name || '',
    template_id:   nr.template_id || null,
    on_success:    nr.on_success  || [],
    on_failure:    nr.on_failure  || [],
    on_always:     nr.on_always   || [],
    status:        nr.status,
    task_id:       nr.task_id || undefined,
  }))
})
</script>

<template>
  <div>
    <div class="flex items-center gap-3 mb-6">
      <button @click="router.push(`/projects/${projectId}/workflows`)" class="p-1.5 text-gray-400 hover:text-gray-600">
        <ArrowLeft class="w-5 h-5" />
      </button>
      <div class="flex items-center gap-2">
        <GitMerge class="w-5 h-5 text-gray-400" />
        <h2 class="text-lg font-medium text-gray-900">
          {{ run?.workflow_name || 'Workflow Run' }}
        </h2>
      </div>
    </div>

    <div v-if="!run" class="text-center py-12 text-gray-400 text-sm">Loading…</div>

    <template v-else>
      <!-- Run Header -->
      <div class="bg-white rounded-xl border border-gray-200 p-5 mb-6">
        <div class="flex items-center justify-between">
          <div>
            <div class="flex items-center gap-2">
              <span
                class="text-sm font-medium"
                :class="runStatusColor[run.status] ?? 'text-gray-500'"
              >
                <Loader2
                  v-if="run.status === 'running' || run.status === 'waiting'"
                  class="inline w-4 h-4 mr-1 animate-spin"
                />
                <HelpCircle
                  v-else-if="run.status === 'waiting_approval'"
                  class="inline w-4 h-4 mr-1 text-amber-500"
                />
                {{ runStatusLabel[run.status] ?? run.status }}
              </span>
              <span class="text-xs text-gray-400 font-mono">{{ run.id?.slice(-8) }}</span>
            </div>

            <div class="flex gap-4 mt-2 text-xs text-gray-400">
              <span v-if="run.username">By: {{ run.username }}</span>
              <span v-if="run.start">Started: {{ new Date(run.start).toLocaleString() }}</span>
              <span v-if="run.end">Finished: {{ new Date(run.end).toLocaleString() }}</span>
            </div>
          </div>

          <button
            v-if="isRunning()"
            @click="stopRun"
            :disabled="stopping"
            class="flex items-center gap-2 text-sm bg-red-600 hover:bg-red-700 text-white px-3 py-1.5 rounded-lg disabled:opacity-60"
          >
            <StopCircle class="w-4 h-4" />
            {{ stopping ? 'Stopping…' : 'Stop' }}
          </button>
        </div>
      </div>

      <!-- Approval modal -->
      <Teleport to="body">
        <div
          v-if="run.status === 'waiting_approval' && approvalInfo"
          class="fixed inset-0 z-50 flex items-center justify-center p-4"
        >
          <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" />
          <div class="relative bg-white rounded-2xl shadow-2xl w-full max-w-md p-6">
            <div class="flex items-center gap-3 mb-4">
              <div class="p-2.5 rounded-full bg-amber-100">
                <HelpCircle class="w-5 h-5 text-amber-600" />
              </div>
              <h3 class="text-lg font-semibold text-gray-900">{{ approvalInfo.title || 'Proceed?' }}</h3>
            </div>

            <p v-if="approvalInfo.text" class="text-sm text-gray-600 mb-6 whitespace-pre-wrap">
              {{ approvalInfo.text }}
            </p>
            <p v-else class="text-sm text-gray-400 mb-6 italic">
              Do you want to continue with the workflow execution?
            </p>

            <div class="flex gap-3">
              <button
                @click="approve"
                :disabled="approving || rejecting"
                class="flex-1 flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-60 disabled:cursor-not-allowed text-white font-medium text-sm px-4 py-2.5 rounded-lg transition-colors"
              >
                <Loader2 v-if="approving" class="w-4 h-4 animate-spin" />
                <CheckCircle v-else class="w-4 h-4" />
                Proceed
              </button>
              <button
                @click="reject"
                :disabled="approving || rejecting"
                class="flex-1 flex items-center justify-center gap-2 bg-red-600 hover:bg-red-700 disabled:opacity-60 disabled:cursor-not-allowed text-white font-medium text-sm px-4 py-2.5 rounded-lg transition-colors"
              >
                <Loader2 v-if="rejecting" class="w-4 h-4 animate-spin" />
                <XCircle v-else class="w-4 h-4" />
                Cancel
              </button>
            </div>
          </div>
        </div>
      </Teleport>

      <!-- Graph -->
      <WorkflowGraph :nodes="graphNodes" :project-id="projectId" class="mb-6" />

      <!-- Node detail list -->
      <div class="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
        <div v-if="!run.node_runs?.length" class="p-6 text-center text-gray-400 text-sm">No nodes in this run.</div>
        <div v-for="nr in run.node_runs" :key="nr.node_id"
          class="flex items-center justify-between px-5 py-3">
          <div class="flex items-center gap-3 min-w-0">
            <span class="text-xs px-2 py-0.5 rounded font-medium flex items-center gap-1 shrink-0"
              :class="statusBadgeClass[nr.status] ?? 'bg-gray-100 text-gray-500'">
              <Loader2 v-if="nr.status === 'running'" class="w-3 h-3 animate-spin" />
              {{ nr.status }}
            </span>
            <div class="min-w-0">
              <p class="text-sm font-medium text-gray-900 truncate">{{ nodeLabel(nr) }}</p>
              <p v-if="nr.template_name" class="text-xs text-gray-400 truncate">{{ nr.template_name }}</p>
            </div>
          </div>
          <RouterLink v-if="nr.task_id" :to="`/projects/${projectId}/tasks/${nr.task_id}`"
            class="text-xs text-brand-600 hover:underline font-mono ml-4 shrink-0">
            Task {{ nr.task_id.slice(-8) }} →
          </RouterLink>
          <span v-else class="text-xs text-gray-400 ml-4 shrink-0 italic">
            {{ nr.status === 'pending' ? 'Not started' : nr.status === 'skipped' ? 'Skipped' : '' }}
          </span>
        </div>
      </div>
    </template>
  </div>
</template>
