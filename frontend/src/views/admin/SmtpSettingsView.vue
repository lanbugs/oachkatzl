<script setup lang="ts">
import { onMounted, ref } from 'vue'
import api from '@/api/client'
import { Save, CheckCircle2, XCircle } from 'lucide-vue-next'

const SMTP_KEYS = ['SMTP_HOST', 'SMTP_PORT', 'SMTP_USER', 'SMTP_PASSWORD', 'SMTP_FROM', 'SMTP_TLS']

const form = ref({
  SMTP_HOST: '',
  SMTP_PORT: '587',
  SMTP_USER: '',
  SMTP_PASSWORD: '',
  SMTP_FROM: '',
  SMTP_TLS: 'true',
})

const saving = ref(false)
const saved = ref(false)

onMounted(async () => {
  const { data } = await api.get('/settings')
  for (const opt of data) {
    if (SMTP_KEYS.includes(opt.key)) {
      (form.value as any)[opt.key] = opt.value
    }
  }
})

async function save() {
  saving.value = true
  saved.value = false
  try {
    for (const key of SMTP_KEYS) {
      await api.put('/settings', { key, value: (form.value as any)[key] })
    }
    saved.value = true
    setTimeout(() => { saved.value = false }, 3000)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="max-w-lg">
    <div class="mb-6">
      <h1 class="text-2xl font-semibold text-gray-900">SMTP / E-Mail Settings</h1>
      <p class="text-sm text-gray-400 mt-1">
        Required for e-mail notifications. Leave blank to disable e-mail alerts.
      </p>
    </div>

    <form @submit.prevent="save" class="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
      <div class="grid grid-cols-2 gap-4">
        <div class="col-span-2">
          <label class="block text-xs font-medium text-gray-600 mb-1">SMTP Host</label>
          <input v-model="form.SMTP_HOST" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="smtp.example.com" />
        </div>
        <div>
          <label class="block text-xs font-medium text-gray-600 mb-1">Port</label>
          <input v-model="form.SMTP_PORT" type="number" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="587" />
        </div>
        <div>
          <label class="block text-xs font-medium text-gray-600 mb-1">Use TLS (STARTTLS)</label>
          <select v-model="form.SMTP_TLS" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
            <option value="true">Yes (recommended)</option>
            <option value="false">No</option>
          </select>
        </div>
        <div>
          <label class="block text-xs font-medium text-gray-600 mb-1">Username</label>
          <input v-model="form.SMTP_USER" autocomplete="off" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="user@example.com" />
        </div>
        <div>
          <label class="block text-xs font-medium text-gray-600 mb-1">Password</label>
          <input v-model="form.SMTP_PASSWORD" type="password" autocomplete="new-password" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
        </div>
        <div class="col-span-2">
          <label class="block text-xs font-medium text-gray-600 mb-1">From address</label>
          <input v-model="form.SMTP_FROM" type="email" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="oachkatzl@example.com" />
        </div>
      </div>

      <div class="flex items-center gap-4 pt-2">
        <button type="submit" :disabled="saving"
          class="flex items-center gap-2 bg-brand-600 hover:bg-brand-700 text-white text-sm px-4 py-2 rounded-lg disabled:opacity-60">
          <Save class="w-4 h-4" />
          {{ saving ? 'Saving…' : 'Save settings' }}
        </button>
        <span v-if="saved" class="flex items-center gap-1 text-sm text-green-600">
          <CheckCircle2 class="w-4 h-4" /> Saved
        </span>
      </div>
    </form>
  </div>
</template>
