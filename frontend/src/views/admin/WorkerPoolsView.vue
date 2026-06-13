<script setup lang="ts">
import { onMounted, ref } from 'vue'
import api from '@/api/client'
import { Server, Plus, Pencil, Trash2, Check } from 'lucide-vue-next'

const pools = ref<any[]>([])
const showNew = ref(false)
const editTarget = ref<any>(null)

const emptyForm = () => ({ slug: '', name: '', description: '', active: true })
const newForm = ref(emptyForm())
const editForm = ref(emptyForm())

const saving = ref(false)
const error = ref('')

onMounted(async () => {
  const { data } = await api.get('/worker-pools')
  pools.value = data
})

async function createPool() {
  saving.value = true
  error.value = ''
  try {
    const { data } = await api.post('/worker-pools', newForm.value)
    pools.value.push(data)
    showNew.value = false
    newForm.value = emptyForm()
  } catch (e: any) {
    error.value = e.response?.data?.message || 'Failed to create worker pool'
  } finally {
    saving.value = false
  }
}

function startEdit(pool: any) {
  editTarget.value = pool
  editForm.value = { slug: pool.slug, name: pool.name, description: pool.description, active: pool.active }
}

async function saveEdit() {
  if (!editTarget.value) return
  saving.value = true
  error.value = ''
  try {
    const { data } = await api.put(`/worker-pools/${editTarget.value.id}`, editForm.value)
    const idx = pools.value.findIndex(p => p.id === editTarget.value.id)
    if (idx !== -1) pools.value[idx] = data
    editTarget.value = null
  } catch (e: any) {
    error.value = e.response?.data?.message || 'Failed to save'
  } finally {
    saving.value = false
  }
}

async function deletePool(id: string) {
  if (!confirm('Delete this worker pool? Templates and custom apps using it will lose the assignment.')) return
  try {
    await api.delete(`/worker-pools/${id}`)
    pools.value = pools.value.filter(p => p.id !== id)
  } catch (e: any) {
    alert(e.response?.data?.message || 'Failed to delete')
  }
}
</script>

<template>
  <div>
    <div class="flex justify-between items-center mb-6">
      <div>
        <h1 class="text-2xl font-semibold text-gray-900">Worker Pools</h1>
        <p class="text-sm text-gray-500 mt-0.5">
          Named Celery queues for custom worker images. Set
          <code class="bg-gray-100 px-1 rounded">OACHKATZL_WORKER_QUEUES=&lt;slug&gt;</code>
          on your worker container to route tasks to it.
        </p>
      </div>
      <button @click="showNew = true; editTarget = null"
        class="flex items-center gap-2 bg-brand-600 hover:bg-brand-700 text-white text-sm px-3 py-1.5 rounded-lg">
        <Plus class="w-4 h-4" /> New pool
      </button>
    </div>

    <!-- Create form -->
    <div v-if="showNew" class="mb-6 bg-white rounded-xl border border-gray-200 p-5">
      <h3 class="font-medium text-gray-900 mb-3">New worker pool</h3>
      <form @submit.prevent="createPool" class="grid grid-cols-2 gap-3">
        <div>
          <label class="block text-xs font-medium text-gray-600 mb-1">Slug (queue name) *</label>
          <input v-model="newForm.slug" required pattern="[a-z0-9][a-z0-9_-]*"
            class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono"
            placeholder="gpu" />
          <p class="text-xs text-gray-400 mt-1">Lowercase letters, digits, <code>-</code> and <code>_</code>. Used as the Celery queue name.</p>
        </div>
        <div>
          <label class="block text-xs font-medium text-gray-600 mb-1">Name *</label>
          <input v-model="newForm.name" required class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
            placeholder="GPU Worker" />
        </div>
        <div class="col-span-2">
          <label class="block text-xs font-medium text-gray-600 mb-1">Description</label>
          <input v-model="newForm.description" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
            placeholder="Worker with CUDA drivers and GPU support" />
        </div>
        <div class="col-span-2 flex items-center gap-4">
          <button type="submit" :disabled="saving"
            class="bg-brand-600 hover:bg-brand-700 text-white text-sm px-4 py-2 rounded-lg disabled:opacity-60">
            {{ saving ? 'Saving…' : 'Create pool' }}
          </button>
          <button type="button" @click="showNew = false; error = ''"
            class="text-sm text-gray-500">Cancel</button>
          <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
        </div>
      </form>
    </div>

    <!-- List -->
    <div class="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
      <div v-if="pools.length === 0" class="p-6 text-center text-gray-400 text-sm">
        No worker pools defined. The default worker uses the built-in <code>celery</code> queue.
      </div>

      <div v-for="pool in pools" :key="pool.id">
        <!-- Edit form (inline) -->
        <div v-if="editTarget?.id === pool.id" class="px-5 py-4">
          <form @submit.prevent="saveEdit" class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-xs font-medium text-gray-600 mb-1">Slug</label>
              <input :value="pool.slug" disabled
                class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm font-mono bg-gray-50 text-gray-400" />
            </div>
            <div>
              <label class="block text-xs font-medium text-gray-600 mb-1">Name *</label>
              <input v-model="editForm.name" required
                class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
            <div class="col-span-2">
              <label class="block text-xs font-medium text-gray-600 mb-1">Description</label>
              <input v-model="editForm.description"
                class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
            <div class="col-span-2 flex items-center gap-4">
              <label class="flex items-center gap-2 text-sm">
                <input v-model="editForm.active" type="checkbox" class="rounded" />
                Active
              </label>
              <button type="submit" :disabled="saving"
                class="bg-brand-600 hover:bg-brand-700 text-white text-sm px-4 py-1.5 rounded-lg disabled:opacity-60">
                {{ saving ? 'Saving…' : 'Save' }}
              </button>
              <button type="button" @click="editTarget = null; error = ''"
                class="text-sm text-gray-500">Cancel</button>
              <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
            </div>
          </form>
        </div>

        <!-- Row -->
        <div v-else class="flex items-center justify-between px-5 py-4">
          <div class="flex items-center gap-3">
            <div class="p-1.5 rounded bg-gray-100">
              <Server class="w-4 h-4 text-gray-500" />
            </div>
            <div>
              <div class="flex items-center gap-2">
                <p class="text-sm font-medium text-gray-900">{{ pool.name }}</p>
                <code class="text-xs bg-gray-100 px-1.5 py-0.5 rounded text-gray-600">{{ pool.slug }}</code>
                <span v-if="!pool.active"
                  class="text-xs bg-gray-100 text-gray-400 px-1.5 py-0.5 rounded">inactive</span>
              </div>
              <p v-if="pool.description" class="text-xs text-gray-400 mt-0.5">{{ pool.description }}</p>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <button @click="startEdit(pool)" class="text-gray-300 hover:text-brand-500 transition-colors" title="Edit">
              <Pencil class="w-4 h-4" />
            </button>
            <button @click="deletePool(pool.id)" class="text-gray-300 hover:text-red-500 transition-colors" title="Delete">
              <Trash2 class="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
