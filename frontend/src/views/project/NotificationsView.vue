<script setup lang="ts">
import { onMounted, ref, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useProjectsStore } from '@/stores/projects'
import api from '@/api/client'
import { projectsApi } from '@/api/projects'
import { Plus, Trash2, Send, X, CheckCircle2, XCircle, Pencil } from 'lucide-vue-next'

const route = useRoute()
const store = useProjectsStore()
const projectId = computed(() => route.params.projectId as string)

const notifs   = ref<any[]>([])
const members  = ref<any[]>([])
const showForm = ref(false)
const editId   = ref<string | null>(null)   // null = create, string = update
const saving   = ref(false)
const testing  = ref(false)
const testResult = ref<{ ok: boolean; msg: string } | null>(null)

// ── Channel definitions ────────────────────────────────────────────────────
const CHANNELS = [
  { value: 'slack',    label: 'Slack',          icon: '💬' },
  { value: 'email',    label: 'E-Mail',          icon: '✉️'  },
  { value: 'telegram', label: 'Telegram',        icon: '✈️'  },
  { value: 'teams',    label: 'Microsoft Teams', icon: '🟦' },
  { value: 'gotify',   label: 'Gotify',          icon: '🔔' },
]

// Fields for non-email channels
const CHANNEL_FIELDS: Record<string, Array<{ key: string; label: string; type?: string; placeholder?: string }>> = {
  slack:    [{ key: 'webhook_url', label: 'Webhook URL', placeholder: 'https://hooks.slack.com/services/...' }],
  telegram: [{ key: 'bot_token', label: 'Bot token', placeholder: '123456:ABC-...' },
             { key: 'chat_id',   label: 'Chat ID',   placeholder: '-100123456789' }],
  teams:    [{ key: 'webhook_url', label: 'Webhook URL', placeholder: 'https://outlook.office.com/webhook/...' }],
  gotify:   [{ key: 'url',   label: 'Gotify server URL', placeholder: 'https://gotify.example.com' },
             { key: 'token', label: 'App token',          placeholder: 'xxxxx' }],
}

// ── Form state ─────────────────────────────────────────────────────────────
const form = ref({
  channel:    'slack' as string,
  on_success: false,
  on_failure: true,
  config:     {} as Record<string, string>,
})

// E-Mail-specific recipient state (separate from generic config)
const emailRecipients = ref({
  mode:         'extra_only' as 'all_members' | 'specific_members' | 'extra_only',
  member_ids:   [] as string[],
  extra_emails: '',   // newline-separated
})

const isEmail   = computed(() => form.value.channel === 'email')
const fields    = computed(() => CHANNEL_FIELDS[form.value.channel] || [])

watch(() => form.value.channel, () => {
  form.value.config = {}
  testResult.value  = null
})

// ── Load data ─────────────────────────────────────────────────────────────
onMounted(async () => {
  const [notifRes, memberRes] = await Promise.all([
    api.get(`/projects/${projectId.value}/notifications`),
    projectsApi.listMembers(projectId.value).catch(() => ({ data: [] })),
  ])
  notifs.value  = notifRes.data
  members.value = memberRes.data
})

// ── Open form (create or edit) ─────────────────────────────────────────────
function openForm() {
  editId.value  = null
  form.value    = { channel: 'slack', on_success: false, on_failure: true, config: {} }
  emailRecipients.value = { mode: 'extra_only', member_ids: [], extra_emails: '' }
  testResult.value = null
  showForm.value = true
}

function startEdit(n: any) {
  editId.value  = n.id
  testResult.value = null

  form.value = {
    channel:    n.channel,
    on_success: n.on_success,
    on_failure: n.on_failure,
    config:     {},
  }

  try {
    const c = JSON.parse(n.config || '{}')

    if (n.channel === 'email') {
      emailRecipients.value = {
        mode:         c.mode || 'extra_only',
        member_ids:   c.member_ids || [],
        extra_emails: (c.extra_emails || []).join('\n'),
      }
    } else {
      // Restore generic config fields
      form.value.config = { ...c }
    }
  } catch {
    emailRecipients.value = { mode: 'extra_only', member_ids: [], extra_emails: '' }
  }

  showForm.value = true
}

// ── Build config JSON ──────────────────────────────────────────────────────
function buildConfig(): string {
  if (isEmail.value) {
    return JSON.stringify({
      mode:         emailRecipients.value.mode,
      member_ids:   emailRecipients.value.member_ids,
      extra_emails: emailRecipients.value.extra_emails
        .split(/[\n,]+/).map(e => e.trim()).filter(Boolean),
    })
  }
  return JSON.stringify(form.value.config)
}

// ── Save (create or update) ────────────────────────────────────────────────
async function save() {
  saving.value = true
  testResult.value = null
  try {
    const payload = {
      channel:    form.value.channel,
      on_success: form.value.on_success,
      on_failure: form.value.on_failure,
      config:     buildConfig(),
    }
    const base = `/projects/${projectId.value}/notifications`
    if (editId.value) {
      const { data } = await api.put(`${base}/${editId.value}`, payload)
      const idx = notifs.value.findIndex(n => n.id === editId.value)
      if (idx !== -1) notifs.value[idx] = data
    } else {
      const { data } = await api.post(base, payload)
      notifs.value.push(data)
    }
    showForm.value = false
    editId.value   = null
  } catch (e: any) {
    alert(e.response?.data?.message || 'Failed to save')
  } finally {
    saving.value = false
  }
}

// ── Test ───────────────────────────────────────────────────────────────────
async function sendTest() {
  testing.value = true
  testResult.value = null
  try {
    await api.post(`/projects/${projectId.value}/notifications/test`, {
      channel: form.value.channel,
      config:  buildConfig(),
    })
    testResult.value = { ok: true, msg: 'Test notification sent!' }
  } catch (e: any) {
    testResult.value = { ok: false, msg: e.response?.data?.message || 'Test failed' }
  } finally {
    testing.value = false
  }
}

// ── Delete ─────────────────────────────────────────────────────────────────
async function deleteNotif(id: string) {
  if (!confirm('Delete this notification rule?')) return
  await api.delete(`/projects/${projectId.value}/notifications/${id}`)
  notifs.value = notifs.value.filter(n => n.id !== id)
}

// ── Display helpers ────────────────────────────────────────────────────────
function channelLabel(ch: string) { return CHANNELS.find(c => c.value === ch)?.label || ch }
function channelIcon (ch: string) { return CHANNELS.find(c => c.value === ch)?.icon  || '🔔' }

function recipientSummary(n: any): string {
  try {
    const c = JSON.parse(n.config || '{}')
    if (n.channel !== 'email') {
      if (c.webhook_url) return c.webhook_url.replace(/https?:\/\//, '').slice(0, 50) + '…'
      if (c.to)          return c.to
      if (c.chat_id)     return `chat ${c.chat_id}`
      if (c.url)         return c.url
      return '(configured)'
    }
    // email channel
    const mode   = c.mode || 'extra_only'
    const extras = (c.extra_emails || []).filter(Boolean)
    if (mode === 'all_members') {
      return extras.length ? `All members + ${extras.join(', ')}` : 'All project members'
    }
    if (mode === 'specific_members') {
      const count = (c.member_ids || []).length
      return extras.length
        ? `${count} member${count !== 1 ? 's' : ''} + ${extras.join(', ')}`
        : `${count} member${count !== 1 ? 's' : ''} selected`
    }
    return extras.join(', ') || '(no recipients)'
  } catch { return '' }
}

// Helper to toggle member selection
function toggleMember(id: string) {
  const idx = emailRecipients.value.member_ids.indexOf(id)
  if (idx === -1) emailRecipients.value.member_ids.push(id)
  else             emailRecipients.value.member_ids.splice(idx, 1)
}
</script>

<template>
  <div>
    <div class="flex justify-between items-center mb-4">
      <div>
        <h2 class="text-lg font-medium text-gray-900">Notifications</h2>
        <p class="text-xs text-gray-400 mt-0.5">Alert rules triggered when tasks finish.</p>
      </div>
      <button v-if="store.canManage" @click="openForm"
        class="flex items-center gap-2 bg-brand-600 hover:bg-brand-700 text-white text-sm px-3 py-1.5 rounded-lg">
        <Plus class="w-4 h-4" /> Add rule
      </button>
    </div>

    <!-- ── Add form ── -->
    <div v-if="showForm" class="mb-4 bg-white rounded-xl border border-brand-200 p-5 space-y-5">
      <div class="flex items-center justify-between">
        <h3 class="font-medium text-gray-900">{{ editId ? 'Edit notification rule' : 'New notification rule' }}</h3>
        <button @click="showForm = false" class="text-gray-400 hover:text-gray-600"><X class="w-4 h-4" /></button>
      </div>

      <form @submit.prevent="save" class="space-y-5">

        <!-- Channel selector -->
        <div>
          <label class="block text-xs font-medium text-gray-600 mb-2">Channel *</label>
          <div class="grid grid-cols-3 gap-2">
            <label v-for="ch in CHANNELS" :key="ch.value"
              class="flex items-center gap-2 border rounded-lg px-3 py-2 cursor-pointer text-sm transition-colors"
              :class="form.channel === ch.value
                ? 'border-brand-500 bg-brand-50 text-brand-700 font-medium'
                : 'border-gray-200 hover:border-gray-300 text-gray-700'"
            >
              <input type="radio" v-model="form.channel" :value="ch.value" class="sr-only" />
              <span>{{ ch.icon }}</span>{{ ch.label }}
            </label>
          </div>
        </div>

        <!-- Non-email channel fields -->
        <div v-if="!isEmail" class="space-y-3">
          <div v-for="field in fields" :key="field.key">
            <label class="block text-xs font-medium text-gray-600 mb-1">{{ field.label }} *</label>
            <input v-model="form.config[field.key]" :type="field.type || 'text'"
              :placeholder="field.placeholder" required
              class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
          </div>
        </div>

        <!-- ── E-Mail recipient configuration ── -->
        <div v-if="isEmail" class="border border-gray-200 rounded-xl p-4 space-y-4 bg-gray-50">
          <p class="text-xs font-semibold text-gray-600 uppercase tracking-wide">Recipients</p>

          <!-- Mode -->
          <div class="space-y-2">
            <label class="flex items-center gap-3 cursor-pointer group">
              <input type="radio" v-model="emailRecipients.mode" value="all_members" class="accent-brand-600" />
              <div>
                <span class="text-sm font-medium text-gray-800">All project members</span>
                <p class="text-xs text-gray-400">Every member's e-mail address is notified.</p>
              </div>
            </label>

            <label class="flex items-center gap-3 cursor-pointer group">
              <input type="radio" v-model="emailRecipients.mode" value="specific_members" class="accent-brand-600" />
              <div>
                <span class="text-sm font-medium text-gray-800">Specific members</span>
                <p class="text-xs text-gray-400">Choose individual members from the list below.</p>
              </div>
            </label>

            <label class="flex items-center gap-3 cursor-pointer group">
              <input type="radio" v-model="emailRecipients.mode" value="extra_only" class="accent-brand-600" />
              <div>
                <span class="text-sm font-medium text-gray-800">Custom addresses only</span>
                <p class="text-xs text-gray-400">Only the addresses entered below are used.</p>
              </div>
            </label>
          </div>

          <!-- Member checkboxes (specific_members only) -->
          <div v-if="emailRecipients.mode === 'specific_members'" class="space-y-1.5">
            <p class="text-xs font-medium text-gray-600">Select members *</p>
            <div v-if="members.length === 0" class="text-xs text-gray-400 italic">No members found.</div>
            <label v-for="m in members" :key="m.user_id"
              class="flex items-center gap-3 px-3 py-2 rounded-lg border cursor-pointer transition-colors"
              :class="emailRecipients.member_ids.includes(m.user_id)
                ? 'border-brand-300 bg-brand-50'
                : 'border-gray-200 hover:border-gray-300 bg-white'"
            >
              <input type="checkbox"
                :checked="emailRecipients.member_ids.includes(m.user_id)"
                @change="toggleMember(m.user_id)"
                class="accent-brand-600 rounded" />
              <div class="min-w-0">
                <p class="text-sm font-medium text-gray-900">{{ m.username }}</p>
                <p class="text-xs text-gray-400 truncate">{{ m.email }}</p>
              </div>
              <span class="ml-auto text-xs text-gray-400 shrink-0">{{ m.role }}</span>
            </label>
          </div>

          <!-- Extra email addresses (always shown for email channel) -->
          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">
              Extra e-mail addresses
              <span class="text-gray-400 font-normal">
                — always included regardless of mode (one per line or comma-separated)
              </span>
            </label>
            <textarea v-model="emailRecipients.extra_emails" rows="3"
              placeholder="ops@company.com&#10;oncall@company.com"
              class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
          </div>
        </div>

        <!-- Triggers -->
        <div>
          <label class="block text-xs font-medium text-gray-600 mb-2">Trigger on</label>
          <div class="flex gap-6">
            <label class="flex items-center gap-2 text-sm cursor-pointer">
              <input v-model="form.on_failure" type="checkbox" class="rounded accent-red-500" />
              <span class="text-red-600 font-medium">❌ Task failed</span>
            </label>
            <label class="flex items-center gap-2 text-sm cursor-pointer">
              <input v-model="form.on_success" type="checkbox" class="rounded accent-green-500" />
              <span class="text-green-600 font-medium">✅ Task succeeded</span>
            </label>
          </div>
          <p class="text-xs text-gray-400 mt-1">
            Templates with "Suppress success alerts" override the success trigger.
          </p>
        </div>

        <!-- Test result -->
        <div v-if="testResult"
          class="flex items-center gap-2 text-sm px-3 py-2 rounded-lg"
          :class="testResult.ok ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'">
          <component :is="testResult.ok ? CheckCircle2 : XCircle" class="w-4 h-4 shrink-0" />
          {{ testResult.msg }}
        </div>

        <div class="flex gap-3">
          <button type="submit" :disabled="saving"
            class="bg-brand-600 hover:bg-brand-700 text-white text-sm px-4 py-2 rounded-lg disabled:opacity-60">
            {{ saving ? 'Saving…' : editId ? 'Save changes' : 'Save rule' }}
          </button>
          <button type="button" @click="sendTest" :disabled="testing"
            class="flex items-center gap-1.5 text-sm border border-gray-300 hover:border-gray-400 px-4 py-2 rounded-lg disabled:opacity-40 transition-colors">
            <Send class="w-3.5 h-3.5" />
            {{ testing ? 'Sending…' : 'Send test' }}
          </button>
          <button type="button" @click="showForm = false" class="text-sm text-gray-500">Cancel</button>
        </div>
      </form>
    </div>

    <!-- Email SMTP hint -->
    <div v-if="notifs.some(n => n.channel === 'email') || (showForm && isEmail)"
      class="mb-4 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-4 py-3">
      📧 E-Mail notifications require SMTP — configure in
      <strong>Admin → Settings</strong> (SMTP_HOST, SMTP_PORT, …).
    </div>

    <!-- ── Rule list ── -->
    <div class="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
      <div v-if="notifs.length === 0" class="p-6 text-center text-gray-400 text-sm">
        No notification rules yet.
      </div>
      <div v-for="n in notifs" :key="n.id" class="flex items-center justify-between px-5 py-4">
        <div class="flex items-center gap-3 min-w-0">
          <div class="text-xl shrink-0">{{ channelIcon(n.channel) }}</div>
          <div class="min-w-0">
            <p class="text-sm font-medium text-gray-900">{{ channelLabel(n.channel) }}</p>
            <p class="text-xs text-gray-400 truncate">{{ recipientSummary(n) }}</p>
          </div>
        </div>
        <div class="flex items-center gap-3 ml-4 shrink-0">
          <div class="flex gap-1.5">
            <span v-if="n.on_failure"
              class="text-xs bg-red-50 text-red-600 border border-red-200 px-1.5 py-0.5 rounded">
              ❌ fail
            </span>
            <span v-if="n.on_success"
              class="text-xs bg-green-50 text-green-600 border border-green-200 px-1.5 py-0.5 rounded">
              ✅ success
            </span>
          </div>
          <button v-if="store.canManage" @click="startEdit(n)"
            class="p-1 text-gray-400 hover:text-brand-600 transition-colors" title="Edit">
            <Pencil class="w-4 h-4" />
          </button>
          <button v-if="store.canManage" @click="deleteNotif(n.id)"
            class="p-1 text-gray-300 hover:text-red-500 transition-colors" title="Delete">
            <Trash2 class="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
