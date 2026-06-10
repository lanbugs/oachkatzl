<script setup lang="ts">
import { onMounted, ref } from 'vue'
import api from '@/api/client'
import { ldapApi } from '@/api/ldap'
import { Save, CheckCircle2, Info, Trash2, Plus, Wifi, ShieldAlert, X } from 'lucide-vue-next'

// ── Keys ──────────────────────────────────────────────────────────────────
const HISTORY_KEY = 'TASK_HISTORY_DAYS'
const SMTP_KEYS   = ['SMTP_HOST', 'SMTP_PORT', 'SMTP_USER', 'SMTP_PASSWORD', 'SMTP_FROM', 'SMTP_TLS']
const MFA_KEY     = 'mfa_required'

// ── MFA enforce state ─────────────────────────────────────────────────────
const mfaRequired   = ref(false)
const savingMfa     = ref(false)
const savedMfa      = ref(false)

// ── Task history state ────────────────────────────────────────────────────
const historyDays   = ref('0')
const savingHistory = ref(false)
const savedHistory  = ref(false)
const errorHistory  = ref('')

const presets = [
  { label: 'Disabled', value: '0'   },
  { label: '7 days',   value: '7'   },
  { label: '30 days',  value: '30'  },
  { label: '90 days',  value: '90'  },
  { label: '1 year',   value: '365' },
]

// ── SMTP state ────────────────────────────────────────────────────────────
const smtp = ref({
  SMTP_HOST: '', SMTP_PORT: '587', SMTP_USER: '', SMTP_PASSWORD: '', SMTP_FROM: '', SMTP_TLS: 'true',
})
const savingSmtp = ref(false)
const savedSmtp  = ref(false)
const errorSmtp  = ref('')

// ── LDAP state ────────────────────────────────────────────────────────────
const ldap = ref({
  enabled: false, server_url: '', use_tls: false, use_ssl: false,
  bind_dn: '', bind_password: '', bind_password_set: false,
  base_dn: '', user_search_filter: '(sAMAccountName={username})',
  group_membership_attr: 'memberOf', follow_nested_groups: false,
  attr_email: 'mail', attr_display_name: 'displayName', attr_uid: 'objectGUID',
  admin_groups: [] as string[],
})
const savingLdap  = ref(false)
const savedLdap   = ref(false)
const errorLdap   = ref('')
const testingLdap = ref(false)
const testResult  = ref<{ ok: boolean; message: string } | null>(null)

const newAdminGroup = ref('')
function addAdminGroup() {
  const dn = newAdminGroup.value.trim()
  if (!dn) return
  if (!ldap.value.admin_groups.includes(dn.toLowerCase())) {
    ldap.value.admin_groups.push(dn.toLowerCase())
  }
  newAdminGroup.value = ''
}
function removeAdminGroup(i: number) {
  ldap.value.admin_groups.splice(i, 1)
}

// Mappings
interface Mapping { id: string; group_dn: string; project_id: string; project_name: string; role: string }
const mappings  = ref<Mapping[]>([])
const projects  = ref<{ id: string; name: string }[]>([])
const newMap    = ref({ group_dn: '', project_id: '', role: 'task_runner' })
const addingMap = ref(false)
const ROLES     = ['owner', 'manager', 'task_runner', 'guest']

// ── Load ──────────────────────────────────────────────────────────────────
onMounted(async () => {
  const [settingsRes, ldapCfgRes, mapsRes, projRes] = await Promise.all([
    api.get('/settings'),
    ldapApi.getConfig().catch(() => null),
    ldapApi.getMappings().catch(() => ({ data: [] })),
    api.get('/projects').catch(() => ({ data: [] })),
  ])
  for (const opt of settingsRes.data) {
    if (opt.key === HISTORY_KEY) historyDays.value = opt.value
    if (SMTP_KEYS.includes(opt.key)) (smtp.value as any)[opt.key] = opt.value
    if (opt.key === MFA_KEY) mfaRequired.value = opt.value === true || opt.value === 'true'
  }
  if (ldapCfgRes) {
    const d = ldapCfgRes.data
    ldap.value = { ...ldap.value, ...d, bind_password: '' }
  }
  mappings.value = mapsRes.data
  projects.value = projRes.data
})

// ── Save: MFA enforce ────────────────────────────────────────────────────
async function saveMfa() {
  savingMfa.value = true; savedMfa.value = false
  try {
    await api.put('/settings', { key: MFA_KEY, value: String(mfaRequired.value) })
    savedMfa.value = true
    setTimeout(() => { savedMfa.value = false }, 3000)
  } finally { savingMfa.value = false }
}

// ── Save: task history ────────────────────────────────────────────────────
async function saveHistory() {
  const days = parseInt(historyDays.value, 10)
  if (isNaN(days) || days < 0) { errorHistory.value = 'Enter 0 (disabled) or a positive number.'; return }
  errorHistory.value = ''
  savingHistory.value = true; savedHistory.value = false
  try {
    await api.put('/settings', { key: HISTORY_KEY, value: String(days) })
    savedHistory.value = true
    setTimeout(() => { savedHistory.value = false }, 3000)
  } catch (e: any) { errorHistory.value = e.response?.data?.message || 'Failed to save'
  } finally { savingHistory.value = false }
}

// ── Save: SMTP ────────────────────────────────────────────────────────────
async function saveSmtp() {
  errorSmtp.value = ''; savingSmtp.value = true; savedSmtp.value = false
  try {
    for (const key of SMTP_KEYS) await api.put('/settings', { key, value: (smtp.value as any)[key] })
    savedSmtp.value = true
    setTimeout(() => { savedSmtp.value = false }, 3000)
  } catch (e: any) { errorSmtp.value = e.response?.data?.message || 'Failed to save'
  } finally { savingSmtp.value = false }
}

// ── Save: LDAP ────────────────────────────────────────────────────────────
async function saveLdap() {
  errorLdap.value = ''; savingLdap.value = true; savedLdap.value = false
  try {
    const payload: any = { ...ldap.value }
    // Only send password if changed
    if (!payload.bind_password) delete payload.bind_password
    delete payload.bind_password_set
    await ldapApi.saveConfig(payload)
    savedLdap.value = true
    setTimeout(() => { savedLdap.value = false }, 3000)
    const r = await ldapApi.getConfig()
    ldap.value = { ...ldap.value, ...r.data, bind_password: '' }
  } catch (e: any) { errorLdap.value = e.response?.data?.message || 'Failed to save'
  } finally { savingLdap.value = false }
}

async function testLdap() {
  testingLdap.value = true; testResult.value = null
  try {
    const { data } = await ldapApi.testConnection()
    testResult.value = data
  } catch (e: any) {
    testResult.value = { ok: false, message: e.response?.data?.message || 'Connection failed' }
  } finally { testingLdap.value = false }
}

// ── Mappings ──────────────────────────────────────────────────────────────
async function addMapping() {
  if (!newMap.value.group_dn.trim() || !newMap.value.project_id) return
  addingMap.value = true
  try {
    const { data } = await ldapApi.createMapping({
      group_dn:   newMap.value.group_dn.trim(),
      project_id: newMap.value.project_id,
      role:       newMap.value.role,
    })
    mappings.value.push(data)
    newMap.value = { group_dn: '', project_id: '', role: 'task_runner' }
  } catch (e: any) {
    alert(e.response?.data?.message || 'Failed to add mapping')
  } finally { addingMap.value = false }
}

async function deleteMapping(id: string) {
  if (!confirm('Delete this mapping?')) return
  await ldapApi.deleteMapping(id)
  mappings.value = mappings.value.filter(m => m.id !== id)
}
</script>

<template>
  <div class="max-w-2xl space-y-8">
    <div>
      <h1 class="text-2xl font-semibold text-gray-900">Settings</h1>
      <p class="text-sm text-gray-400 mt-1">System-wide configuration.</p>
    </div>

    <!-- ── MFA Enforce ───────────────────────────────────────────────────── -->
    <section class="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
      <div>
        <h2 class="text-base font-semibold text-gray-900">Two-Factor Authentication (MFA)</h2>
        <p class="text-sm text-gray-400 mt-0.5">When enabled, all users must set up TOTP 2FA before they can use the application. They are redirected to their profile page on first login.</p>
      </div>
      <label class="flex items-center gap-3 cursor-pointer select-none">
        <div class="relative">
          <input type="checkbox" v-model="mfaRequired" class="sr-only peer" />
          <div class="w-10 h-6 bg-gray-200 peer-checked:bg-brand-600 rounded-full transition-colors"></div>
          <div class="absolute top-1 left-1 w-4 h-4 bg-white rounded-full shadow transition-transform peer-checked:translate-x-4"></div>
        </div>
        <span class="text-sm font-medium text-gray-700">Require MFA for all users</span>
      </label>
      <div class="flex items-center gap-4">
        <button @click="saveMfa" :disabled="savingMfa"
          class="flex items-center gap-2 bg-brand-600 hover:bg-brand-700 text-white text-sm px-4 py-2 rounded-lg disabled:opacity-60">
          <Save class="w-4 h-4" />{{ savingMfa ? 'Saving…' : 'Save' }}
        </button>
        <span v-if="savedMfa" class="flex items-center gap-1 text-sm text-green-600"><CheckCircle2 class="w-4 h-4" /> Saved</span>
      </div>
    </section>

    <!-- ── Task History Retention ────────────────────────────────────────── -->
    <section class="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
      <div>
        <h2 class="text-base font-semibold text-gray-900">Task History Retention</h2>
        <p class="text-sm text-gray-400 mt-0.5">Finished tasks older than this are deleted by a background job (runs hourly). Log output is deleted as well.</p>
      </div>
      <div class="flex flex-wrap gap-2">
        <button v-for="p in presets" :key="p.value" type="button" @click="historyDays = p.value"
          class="text-xs px-3 py-1.5 rounded-lg border transition-colors"
          :class="historyDays === p.value ? 'bg-brand-600 text-white border-brand-600' : 'border-gray-300 text-gray-600 hover:bg-gray-50'">
          {{ p.label }}</button>
      </div>
      <div class="flex items-center gap-3">
        <div class="relative w-36">
          <input v-model="historyDays" type="number" min="0" step="1" placeholder="0"
            class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm pr-12 focus:outline-none focus:ring-2 focus:ring-brand-500"
            :class="errorHistory ? 'border-red-400' : ''" />
          <span class="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-gray-400 pointer-events-none">days</span>
        </div>
        <p class="text-xs text-gray-400">
          <span v-if="historyDays === '0' || historyDays === ''">Retention is <strong>disabled</strong> — tasks kept forever.</span>
          <span v-else>Tasks older than <strong>{{ historyDays }} day{{ historyDays === '1' ? '' : 's' }}</strong> will be deleted.</span>
        </p>
      </div>
      <div class="flex items-start gap-2 text-xs text-blue-700 bg-blue-50 border border-blue-200 rounded-lg px-3 py-2.5">
        <Info class="w-3.5 h-3.5 mt-0.5 shrink-0" />
        <span>Only <strong>finished</strong> tasks are deleted. Running tasks are never affected.</span>
      </div>
      <p v-if="errorHistory" class="text-xs text-red-500">{{ errorHistory }}</p>
      <div class="flex items-center gap-4">
        <button @click="saveHistory" :disabled="savingHistory"
          class="flex items-center gap-2 bg-brand-600 hover:bg-brand-700 text-white text-sm px-4 py-2 rounded-lg disabled:opacity-60">
          <Save class="w-4 h-4" />{{ savingHistory ? 'Saving…' : 'Save' }}
        </button>
        <span v-if="savedHistory" class="flex items-center gap-1 text-sm text-green-600"><CheckCircle2 class="w-4 h-4" /> Saved</span>
      </div>
    </section>

    <!-- ── SMTP ─────────────────────────────────────────────────────────── -->
    <section class="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
      <div>
        <h2 class="text-base font-semibold text-gray-900">SMTP / E-Mail</h2>
        <p class="text-sm text-gray-400 mt-0.5">Required for e-mail notifications. Leave blank to disable.</p>
      </div>
      <div class="grid grid-cols-2 gap-4">
        <div class="col-span-2">
          <label class="block text-xs font-medium text-gray-600 mb-1">SMTP Host</label>
          <input v-model="smtp.SMTP_HOST" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" placeholder="smtp.example.com" />
        </div>
        <div>
          <label class="block text-xs font-medium text-gray-600 mb-1">Port</label>
          <input v-model="smtp.SMTP_PORT" type="number" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" placeholder="587" />
        </div>
        <div>
          <label class="block text-xs font-medium text-gray-600 mb-1">Use TLS</label>
          <select v-model="smtp.SMTP_TLS" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500">
            <option value="true">Yes (recommended)</option>
            <option value="false">No</option>
          </select>
        </div>
        <div>
          <label class="block text-xs font-medium text-gray-600 mb-1">Username</label>
          <input v-model="smtp.SMTP_USER" autocomplete="off" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" placeholder="user@example.com" />
        </div>
        <div>
          <label class="block text-xs font-medium text-gray-600 mb-1">Password</label>
          <input v-model="smtp.SMTP_PASSWORD" type="password" autocomplete="new-password" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
        </div>
        <div class="col-span-2">
          <label class="block text-xs font-medium text-gray-600 mb-1">From address</label>
          <input v-model="smtp.SMTP_FROM" type="email" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" placeholder="oachkatzl@example.com" />
        </div>
      </div>
      <p v-if="errorSmtp" class="text-xs text-red-500">{{ errorSmtp }}</p>
      <div class="flex items-center gap-4">
        <button @click="saveSmtp" :disabled="savingSmtp"
          class="flex items-center gap-2 bg-brand-600 hover:bg-brand-700 text-white text-sm px-4 py-2 rounded-lg disabled:opacity-60">
          <Save class="w-4 h-4" />{{ savingSmtp ? 'Saving…' : 'Save' }}
        </button>
        <span v-if="savedSmtp" class="flex items-center gap-1 text-sm text-green-600"><CheckCircle2 class="w-4 h-4" /> Saved</span>
      </div>
    </section>

    <!-- ── LDAP / Active Directory ───────────────────────────────────────── -->
    <section class="bg-white rounded-xl border border-gray-200 p-6 space-y-5">
      <div>
        <h2 class="text-base font-semibold text-gray-900">LDAP / Active Directory</h2>
        <p class="text-sm text-gray-400 mt-0.5">
          Users can log in with their AD credentials. On login, group memberships are synced to project roles automatically.
        </p>
      </div>

      <!-- Enable toggle -->
      <label class="flex items-center gap-3 cursor-pointer">
        <div class="relative">
          <input v-model="ldap.enabled" type="checkbox" class="sr-only" />
          <div class="w-10 h-6 rounded-full transition-colors" :class="ldap.enabled ? 'bg-brand-600' : 'bg-gray-300'"></div>
          <div class="absolute top-1 left-1 w-4 h-4 bg-white rounded-full shadow transition-transform"
            :class="ldap.enabled ? 'translate-x-4' : ''"></div>
        </div>
        <span class="text-sm font-medium text-gray-700">Enable LDAP authentication</span>
      </label>

      <div class="grid grid-cols-2 gap-4" :class="!ldap.enabled ? 'opacity-50 pointer-events-none' : ''">
        <div class="col-span-2">
          <label class="block text-xs font-medium text-gray-600 mb-1">Server URL</label>
          <input v-model="ldap.server_url" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-brand-500"
            placeholder="ldap://dc.corp.local:389" />
        </div>
        <label class="flex items-center gap-2 text-sm text-gray-700 col-span-1">
          <input v-model="ldap.use_tls" type="checkbox" class="rounded" />
          STARTTLS
        </label>
        <label class="flex items-center gap-2 text-sm text-gray-700 col-span-1">
          <input v-model="ldap.use_ssl" type="checkbox" class="rounded" />
          LDAPS (SSL)
        </label>
        <div class="col-span-2">
          <label class="block text-xs font-medium text-gray-600 mb-1">Bind DN <span class="text-gray-400 font-normal">(service account)</span></label>
          <input v-model="ldap.bind_dn" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-brand-500"
            placeholder="CN=svc-oachkatzl,OU=ServiceAccounts,DC=corp,DC=local" />
        </div>
        <div class="col-span-2">
          <label class="block text-xs font-medium text-gray-600 mb-1">
            Bind Password
            <span v-if="ldap.bind_password_set" class="text-green-600 font-normal ml-1">● currently set</span>
          </label>
          <input v-model="ldap.bind_password" type="password" autocomplete="new-password"
            class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            :placeholder="ldap.bind_password_set ? '(leave blank to keep current password)' : 'Enter password'" />
        </div>
        <div class="col-span-2">
          <label class="block text-xs font-medium text-gray-600 mb-1">Base DN</label>
          <input v-model="ldap.base_dn" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-brand-500"
            placeholder="DC=corp,DC=local" />
        </div>
        <div class="col-span-2">
          <label class="block text-xs font-medium text-gray-600 mb-1">User Search Filter</label>
          <input v-model="ldap.user_search_filter" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-brand-500"
            placeholder="(sAMAccountName={username})" />
          <p class="text-xs text-gray-400 mt-1"><code class="bg-gray-100 px-1 rounded">{username}</code> is replaced with the entered username.</p>
        </div>
        <div>
          <label class="block text-xs font-medium text-gray-600 mb-1">Group Membership Attribute</label>
          <input v-model="ldap.group_membership_attr" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-brand-500"
            placeholder="memberOf" />
        </div>
        <div class="flex items-end pb-2">
          <label class="flex items-center gap-2 text-sm text-gray-700">
            <input v-model="ldap.follow_nested_groups" type="checkbox" class="rounded" />
            Follow nested groups (AD LDAP_MATCHING_RULE_IN_CHAIN)
          </label>
        </div>
        <div class="border-t border-gray-100 col-span-2 pt-3">
          <p class="text-xs font-medium text-gray-500 mb-3">Attribute mapping</p>
          <div class="grid grid-cols-3 gap-3">
            <div>
              <label class="block text-xs text-gray-500 mb-1">UID attribute</label>
              <input v-model="ldap.attr_uid" class="w-full border border-gray-300 rounded-lg px-3 py-1.5 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-brand-500" placeholder="objectGUID" />
            </div>
            <div>
              <label class="block text-xs text-gray-500 mb-1">E-Mail attribute</label>
              <input v-model="ldap.attr_email" class="w-full border border-gray-300 rounded-lg px-3 py-1.5 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-brand-500" placeholder="mail" />
            </div>
            <div>
              <label class="block text-xs text-gray-500 mb-1">Display name attribute</label>
              <input v-model="ldap.attr_display_name" class="w-full border border-gray-300 rounded-lg px-3 py-1.5 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-brand-500" placeholder="displayName" />
            </div>
          </div>
        </div>
        <!-- Admin groups -->
        <div class="border-t border-gray-100 col-span-2 pt-3">
          <p class="text-xs font-medium text-gray-500 mb-1">Global admin groups</p>
          <p class="text-xs text-gray-400 mb-3">
            Members of these AD groups are granted system-wide admin access on login.
            Removing a user from all admin groups revokes admin on next login.
          </p>
          <div class="space-y-1.5 mb-2">
            <div v-for="(g, i) in ldap.admin_groups" :key="i"
              class="flex items-center gap-2 bg-amber-50 border border-amber-200 rounded-lg px-3 py-1.5">
              <ShieldAlert class="w-3.5 h-3.5 text-amber-500 flex-shrink-0" />
              <span class="flex-1 text-xs font-mono text-gray-700 truncate" :title="g">{{ g }}</span>
              <button type="button" @click="removeAdminGroup(i)"
                class="text-gray-400 hover:text-red-500 flex-shrink-0">
                <X class="w-3.5 h-3.5" />
              </button>
            </div>
            <p v-if="ldap.admin_groups.length === 0" class="text-xs text-gray-400 italic">No admin groups configured.</p>
          </div>
          <div class="flex gap-2">
            <input v-model="newAdminGroup" @keydown.enter.prevent="addAdminGroup"
              class="flex-1 border border-gray-300 rounded-lg px-3 py-1.5 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-brand-500"
              placeholder="CN=Oachkatzl-Admins,OU=Groups,DC=corp,DC=local" />
            <button type="button" @click="addAdminGroup"
              class="flex items-center gap-1 border border-gray-300 text-gray-600 hover:bg-gray-50 text-sm px-3 py-1.5 rounded-lg">
              <Plus class="w-3.5 h-3.5" /> Add
            </button>
          </div>
        </div>
      </div>

      <!-- Test + Save -->
      <p v-if="errorLdap" class="text-xs text-red-500">{{ errorLdap }}</p>
      <div class="flex flex-wrap items-center gap-3">
        <button @click="saveLdap" :disabled="savingLdap"
          class="flex items-center gap-2 bg-brand-600 hover:bg-brand-700 text-white text-sm px-4 py-2 rounded-lg disabled:opacity-60">
          <Save class="w-4 h-4" />{{ savingLdap ? 'Saving…' : 'Save' }}
        </button>
        <button @click="testLdap" :disabled="testingLdap || !ldap.enabled"
          class="flex items-center gap-2 border border-gray-300 text-gray-700 hover:bg-gray-50 text-sm px-4 py-2 rounded-lg disabled:opacity-50 transition-colors">
          <Wifi class="w-4 h-4" />{{ testingLdap ? 'Testing…' : 'Test connection' }}
        </button>
        <span v-if="savedLdap" class="flex items-center gap-1 text-sm text-green-600"><CheckCircle2 class="w-4 h-4" /> Saved</span>
        <span v-if="testResult" class="text-sm" :class="testResult.ok ? 'text-green-600' : 'text-red-500'">
          {{ testResult.ok ? '✓' : '✗' }} {{ testResult.message }}
        </span>
      </div>
    </section>

    <!-- ── LDAP Group → Role Mappings ─────────────────────────────────────── -->
    <section class="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
      <div>
        <h2 class="text-base font-semibold text-gray-900">LDAP Group → Project Role Mappings</h2>
        <p class="text-sm text-gray-400 mt-0.5">
          Members of the specified AD group automatically receive the assigned role in the project on login.
          Roles are re-synced every login.
        </p>
      </div>

      <!-- Existing mappings -->
      <div v-if="mappings.length > 0" class="divide-y divide-gray-100 rounded-lg border border-gray-200 overflow-hidden">
        <div v-for="m in mappings" :key="m.id"
          class="flex items-center gap-3 px-4 py-3 bg-gray-50">
          <code class="flex-1 text-xs text-gray-700 truncate" :title="m.group_dn">{{ m.group_dn }}</code>
          <span class="text-xs text-gray-400 shrink-0">→</span>
          <span class="text-sm text-gray-700 shrink-0 w-32 truncate">{{ m.project_name }}</span>
          <span class="text-xs px-2 py-0.5 rounded font-medium shrink-0"
            :class="{
              'bg-blue-50 text-blue-700': m.role === 'owner',
              'bg-green-50 text-green-700': m.role === 'manager',
              'bg-yellow-50 text-yellow-700': m.role === 'task_runner',
              'bg-gray-100 text-gray-600': m.role === 'guest',
            }">{{ m.role }}</span>
          <button @click="deleteMapping(m.id)" class="text-gray-300 hover:text-red-500 transition-colors shrink-0">
            <Trash2 class="w-4 h-4" />
          </button>
        </div>
      </div>
      <p v-else class="text-sm text-gray-400 italic">No mappings defined yet.</p>

      <!-- Add new mapping -->
      <div class="border border-dashed border-gray-300 rounded-lg p-4 space-y-3">
        <p class="text-xs font-medium text-gray-500">Add mapping</p>
        <div class="flex gap-2 flex-wrap">
          <input v-model="newMap.group_dn" placeholder="CN=DevOps,OU=Groups,DC=corp,DC=local"
            class="flex-1 min-w-48 border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-brand-500" />
          <select v-model="newMap.project_id"
            class="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500">
            <option value="">— Project —</option>
            <option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</option>
          </select>
          <select v-model="newMap.role"
            class="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500">
            <option v-for="r in ROLES" :key="r" :value="r">{{ r }}</option>
          </select>
          <button @click="addMapping" :disabled="addingMap || !newMap.group_dn || !newMap.project_id"
            class="flex items-center gap-1.5 bg-brand-600 hover:bg-brand-700 text-white text-sm px-3 py-2 rounded-lg disabled:opacity-50">
            <Plus class="w-4 h-4" />{{ addingMap ? '…' : 'Add' }}
          </button>
        </div>
      </div>
    </section>
  </div>
</template>
