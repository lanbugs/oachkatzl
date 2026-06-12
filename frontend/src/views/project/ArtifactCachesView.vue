<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { Plus, Pencil, Trash2, ChevronDown, ChevronRight, Download, FileJson, FileText } from 'lucide-vue-next'
import api from '@/api/client'

const route = useRoute()
const projectId = computed(() => route.params.projectId as string)

interface ArtifactCache { id: string; name: string; description: string; retention_days: number; created_at: string }
interface ArtifactRun { id: string; cache_id: string; task_id: string | null; workflow_run_id: string | null; artifact_count: number; expires_at: string | null; created_at: string }
interface Artifact { id: string; run_id: string; name: string; artifact_type: 'file' | 'json'; content_type: string; size_bytes: number; is_tabular: boolean; created_at: string }

const caches = ref<ArtifactCache[]>([])
const expandedCacheId = ref<string | null>(null)
const runsMap = ref<Record<string, ArtifactRun[]>>({})
const expandedRunId = ref<string | null>(null)
const artifactsMap = ref<Record<string, Artifact[]>>({})

const showForm = ref(false)
const editId = ref<string | null>(null)
const saving = ref(false)
const form = ref({ name: '', description: '', retention_days: 30 })

function emptyForm() { form.value = { name: '', description: '', retention_days: 30 } }

async function loadCaches() {
  const { data } = await api.get(`/projects/${projectId.value}/artifact-caches`)
  caches.value = data
}

onMounted(loadCaches)

async function toggleCache(cacheId: string) {
  if (expandedCacheId.value === cacheId) { expandedCacheId.value = null; return }
  expandedCacheId.value = cacheId
  if (!runsMap.value[cacheId]) {
    const { data } = await api.get(`/projects/${projectId.value}/artifact-caches/${cacheId}/runs`)
    runsMap.value[cacheId] = data.items ?? data
  }
}

async function toggleRun(runId: string, cacheId: string) {
  if (expandedRunId.value === runId) { expandedRunId.value = null; return }
  expandedRunId.value = runId
  if (!artifactsMap.value[runId]) {
    const { data } = await api.get(`/projects/${projectId.value}/artifact-caches/${cacheId}/runs/${runId}/artifacts`)
    artifactsMap.value[runId] = data
  }
}

function startCreate() { emptyForm(); editId.value = null; showForm.value = true }

function startEdit(c: ArtifactCache) {
  form.value = { name: c.name, description: c.description, retention_days: c.retention_days }
  editId.value = c.id
  showForm.value = true
}

function cancelForm() { showForm.value = false; editId.value = null; emptyForm() }

async function save() {
  saving.value = true
  try {
    if (editId.value) {
      await api.patch(`/projects/${projectId.value}/artifact-caches/${editId.value}`, form.value)
    } else {
      await api.post(`/projects/${projectId.value}/artifact-caches`, form.value)
    }
    cancelForm()
    await loadCaches()
  } finally {
    saving.value = false
  }
}

async function deleteCache(c: ArtifactCache) {
  if (!confirm(`Delete cache "${c.name}" and all its artifacts?`)) return
  await api.delete(`/projects/${projectId.value}/artifact-caches/${c.id}`)
  await loadCaches()
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

async function downloadArtifact(art: Artifact, format?: string) {
  const url = `/artifacts/${art.id}/download${format ? `?format=${format}` : ''}`
  const { data, headers } = await api.get(url, { responseType: 'blob' })
  const blob = new Blob([data], { type: headers['content-type'] || 'application/octet-stream' })
  const objectUrl = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = objectUrl
  a.download = format === 'csv'
    ? (art.name.endsWith('.csv') ? art.name : art.name + '.csv')
    : art.name
  a.click()
  URL.revokeObjectURL(objectUrl)
}
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <div>
        <h2 class="text-lg font-semibold text-gray-900">Artifact Caches</h2>
        <p class="text-sm text-gray-500 mt-0.5">Store and share files or JSON between tasks. Tasks get an artifact token via <code class="text-xs bg-gray-100 px-1 rounded">OACHKATZL_ARTIFACT_TOKEN</code>.</p>
      </div>
      <button
        type="button"
        @click="startCreate"
        class="flex items-center gap-1.5 bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium px-3 py-2 rounded-lg transition-colors"
      >
        <Plus class="w-4 h-4" /> New cache
      </button>
    </div>

    <!-- Create / Edit form -->
    <div v-if="showForm" class="bg-white border border-gray-200 rounded-xl p-5 mb-5 space-y-4">
      <h3 class="text-sm font-semibold text-gray-800">{{ editId ? 'Edit cache' : 'New artifact cache' }}</h3>
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-xs font-medium text-gray-600 mb-1">Name</label>
          <input v-model="form.name" type="text" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" placeholder="e.g. build-artifacts" />
        </div>
        <div>
          <label class="block text-xs font-medium text-gray-600 mb-1">Retention (days, 0 = forever)</label>
          <input v-model.number="form.retention_days" type="number" min="0" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
        </div>
        <div class="col-span-2">
          <label class="block text-xs font-medium text-gray-600 mb-1">Description</label>
          <input v-model="form.description" type="text" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" placeholder="Optional" />
        </div>
      </div>
      <div class="flex gap-3">
        <button type="button" @click="save" :disabled="saving || !form.name"
          class="bg-brand-600 hover:bg-brand-700 disabled:opacity-40 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors">
          {{ saving ? 'Saving…' : 'Save' }}
        </button>
        <button type="button" @click="cancelForm" class="text-sm text-gray-500 hover:text-gray-700 px-4 py-2 rounded-lg border border-gray-200 hover:bg-gray-50 transition-colors">Cancel</button>
      </div>
    </div>

    <!-- Cache list -->
    <div v-if="caches.length === 0 && !showForm" class="bg-white rounded-xl border border-gray-200 p-10 text-center text-gray-400 text-sm">
      No artifact caches yet.
    </div>

    <div v-else class="space-y-3">
      <div v-for="cache in caches" :key="cache.id" class="bg-white rounded-xl border border-gray-200">
        <!-- Cache header -->
        <div class="flex items-center justify-between px-5 py-4 cursor-pointer select-none" @click="toggleCache(cache.id)">
          <div class="flex items-center gap-3">
            <component :is="expandedCacheId === cache.id ? ChevronDown : ChevronRight" class="w-4 h-4 text-gray-400" />
            <div>
              <p class="text-sm font-semibold text-gray-900">{{ cache.name }}</p>
              <p v-if="cache.description" class="text-xs text-gray-400">{{ cache.description }}</p>
            </div>
          </div>
          <div class="flex items-center gap-4">
            <span class="text-xs text-gray-400">
              {{ cache.retention_days === 0 ? 'No expiry' : `${cache.retention_days}d retention` }}
            </span>
            <button type="button" @click.stop="startEdit(cache)" class="text-gray-400 hover:text-gray-600 p-1"><Pencil class="w-3.5 h-3.5" /></button>
            <button type="button" @click.stop="deleteCache(cache)" class="text-red-400 hover:text-red-600 p-1"><Trash2 class="w-3.5 h-3.5" /></button>
          </div>
        </div>

        <!-- Runs list (expanded) -->
        <div v-if="expandedCacheId === cache.id" class="border-t border-gray-100">
          <div v-if="!runsMap[cache.id] || runsMap[cache.id].length === 0" class="px-5 py-4 text-sm text-gray-400">
            No runs recorded yet.
          </div>
          <div v-else>
            <div v-for="run in runsMap[cache.id]" :key="run.id" class="border-b border-gray-50 last:border-b-0">
              <!-- Run row -->
              <div class="flex items-center justify-between px-5 py-3 cursor-pointer hover:bg-gray-50" @click="toggleRun(run.id, cache.id)">
                <div class="flex items-center gap-3">
                  <component :is="expandedRunId === run.id ? ChevronDown : ChevronRight" class="w-3.5 h-3.5 text-gray-400" />
                  <div class="text-xs text-gray-600">
                    <span v-if="run.task_id" class="font-mono">Task {{ run.task_id.slice(-8) }}</span>
                    <span v-else-if="run.workflow_run_id" class="font-mono">Workflow run {{ run.workflow_run_id.slice(-8) }}</span>
                    <span v-else class="text-gray-400">Unknown origin</span>
                  </div>
                </div>
                <div class="flex items-center gap-4 text-xs text-gray-400">
                  <span>{{ run.artifact_count }} artifact{{ run.artifact_count !== 1 ? 's' : '' }}</span>
                  <span v-if="run.expires_at">Expires {{ new Date(run.expires_at).toLocaleDateString() }}</span>
                  <span>{{ run.created_at ? new Date(run.created_at).toLocaleString() : '' }}</span>
                </div>
              </div>

              <!-- Artifacts list (expanded run) -->
              <div v-if="expandedRunId === run.id" class="bg-gray-50 px-5 py-2 space-y-1">
                <div v-if="!artifactsMap[run.id] || artifactsMap[run.id].length === 0" class="text-xs text-gray-400 py-2">
                  No artifacts in this run.
                </div>
                <div v-for="art in artifactsMap[run.id]" :key="art.id"
                  class="flex items-center justify-between bg-white rounded-lg border border-gray-100 px-3 py-2">
                  <div class="flex items-center gap-2">
                    <component :is="art.artifact_type === 'json' ? FileJson : FileText" class="w-4 h-4 text-gray-400" />
                    <div>
                      <p class="text-xs font-medium text-gray-800">{{ art.name }}</p>
                      <p class="text-xs text-gray-400">{{ formatBytes(art.size_bytes) }} · {{ art.artifact_type }}</p>
                    </div>
                  </div>
                  <div class="flex items-center gap-1">
                    <button type="button" @click="downloadArtifact(art)"
                      class="flex items-center gap-1 text-xs text-brand-600 hover:text-brand-700 px-2 py-1 rounded hover:bg-brand-50 transition-colors">
                      <Download class="w-3.5 h-3.5" />
                      {{ art.artifact_type === 'file' ? 'Download' : 'JSON' }}
                    </button>
                    <button v-if="art.artifact_type === 'json' && art.is_tabular" type="button" @click="downloadArtifact(art, 'csv')"
                      class="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700 px-2 py-1 rounded hover:bg-gray-100 transition-colors">
                      <Download class="w-3.5 h-3.5" />
                      CSV
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
