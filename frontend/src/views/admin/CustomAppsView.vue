<script setup lang="ts">
import { onMounted, ref } from 'vue'
import api from '@/api/client'
import { Puzzle, Plus, Trash2 } from 'lucide-vue-next'

const apps = ref<any[]>([])
const workerPools = ref<any[]>([])
const showNew = ref(false)
const emptyForm = () => ({ slug: '', title: '', executable: '', args_template: '{file} {arguments}', active: true, worker_pool_id: '' })
const form = ref(emptyForm())
const saving = ref(false)

onMounted(async () => {
  const [appsRes, wpRes] = await Promise.all([
    api.get('/custom-apps'),
    api.get('/worker-pools'),
  ])
  apps.value = appsRes.data
  workerPools.value = wpRes.data ?? []
})

async function createApp() {
  saving.value = true
  try {
    const payload = { ...form.value, worker_pool_id: form.value.worker_pool_id || null }
    const { data } = await api.post('/custom-apps', payload)
    apps.value.push(data)
    showNew.value = false
    form.value = emptyForm()
  } finally {
    saving.value = false
  }
}

async function deleteApp(id: string) {
  if (!confirm('Delete this custom app?')) return
  await api.delete(`/custom-apps/${id}`)
  apps.value = apps.value.filter(a => a.id !== id)
}
</script>

<template>
  <div>
    <div class="flex justify-between items-center mb-6">
      <div>
        <h1 class="text-2xl font-semibold text-gray-900">Custom Apps</h1>
        <p class="text-sm text-gray-500 mt-0.5">Register custom executables as additional automation types.</p>
      </div>
      <button @click="showNew = true"
        class="flex items-center gap-2 bg-brand-600 hover:bg-brand-700 text-white text-sm px-3 py-1.5 rounded-lg">
        <Plus class="w-4 h-4" /> New app
      </button>
    </div>

    <div v-if="showNew" class="mb-6 bg-white rounded-xl border border-gray-200 p-5">
      <form @submit.prevent="createApp" class="grid grid-cols-2 gap-3">
        <div>
          <label class="block text-xs font-medium text-gray-600 mb-1">Slug (unique ID)</label>
          <input v-model="form.slug" required pattern="[a-z0-9_-]+" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono" placeholder="mytool" />
        </div>
        <div>
          <label class="block text-xs font-medium text-gray-600 mb-1">Title</label>
          <input v-model="form.title" required class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
        </div>
        <div>
          <label class="block text-xs font-medium text-gray-600 mb-1">Executable (binary on worker)</label>
          <input v-model="form.executable" required class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono" placeholder="/usr/bin/mytool" />
        </div>
        <div>
          <label class="block text-xs font-medium text-gray-600 mb-1">Args template</label>
          <input v-model="form.args_template" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono" />
          <p class="text-xs text-gray-400 mt-1">Placeholders: <code>{file}</code> <code>{arguments}</code></p>
        </div>
        <div class="col-span-2">
          <label class="block text-xs font-medium text-gray-600 mb-1">Worker pool (optional)</label>
          <select v-model="form.worker_pool_id" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
            <option value="">— Default worker —</option>
            <option v-for="wp in workerPools" :key="wp.id" :value="wp.id">{{ wp.name }} ({{ wp.slug }})</option>
          </select>
          <p class="text-xs text-gray-400 mt-1">Default pool for templates using this app type. Can be overridden per template.</p>
        </div>
        <div class="col-span-2 flex gap-3">
          <button type="submit" :disabled="saving"
            class="bg-brand-600 hover:bg-brand-700 text-white text-sm px-4 py-2 rounded-lg disabled:opacity-60">
            {{ saving ? 'Saving…' : 'Register app' }}
          </button>
          <button type="button" @click="showNew = false" class="text-sm text-gray-500">Cancel</button>
        </div>
      </form>
    </div>

    <div class="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
      <div v-if="apps.length === 0" class="p-6 text-center text-gray-400 text-sm">
        No custom apps. Built-in types: <code>ansible</code>, <code>bash</code>, <code>python</code>.
      </div>
      <div v-for="a in apps" :key="a.id" class="flex items-center justify-between px-5 py-4">
        <div class="flex items-center gap-3">
          <div class="p-1.5 rounded bg-gray-100">
            <Puzzle class="w-4 h-4 text-gray-500" />
          </div>
          <div>
            <div class="flex items-center gap-2">
              <p class="text-sm font-medium text-gray-900">{{ a.title }}</p>
              <code class="text-xs bg-gray-100 px-1.5 py-0.5 rounded text-gray-600">{{ a.slug }}</code>
            </div>
            <p class="text-xs text-gray-400 font-mono">{{ a.executable }}</p>
            <p v-if="a.worker_pool_name" class="text-xs text-blue-500 mt-0.5">
              Pool: {{ a.worker_pool_name }}
            </p>
          </div>
        </div>
        <button @click="deleteApp(a.id)" class="text-gray-300 hover:text-red-500 transition-colors">
          <Trash2 class="w-4 h-4" />
        </button>
      </div>
    </div>
  </div>
</template>
