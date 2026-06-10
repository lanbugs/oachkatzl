<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { authApi } from '@/api/auth'
import { ShieldCheck, ShieldOff, KeyRound, Copy, Check, Lock } from 'lucide-vue-next'

const auth = useAuthStore()

// ── MFA state ─────────────────────────────────────────────────────────────
const mfaEnabled    = computed(() => auth.user?.totp_enabled ?? false)
const setupStep     = ref<'idle' | 'qr' | 'verify' | 'codes'>('idle')
const qrSvg         = ref('')
const totpSecret    = ref('')
const verifyCode    = ref('')
const recoveryCodes = ref<string[]>([])
const verifyError   = ref('')
const loading       = ref(false)
const copied        = ref(false)

// Disable flow
const showDisable  = ref(false)
const disableError = ref('')

// ── Change password state ──────────────────────────────────────────────────
const isLocalUser    = computed(() => !auth.user?.auth_provider || auth.user.auth_provider === 'local')
const pwCurrent      = ref('')
const pwNew          = ref('')
const pwConfirm      = ref('')
const pwLoading      = ref(false)
const pwError        = ref('')
const pwSuccess      = ref(false)

async function changePassword() {
  pwError.value = ''
  pwSuccess.value = false
  if (pwNew.value.length < 8) { pwError.value = 'New password must be at least 8 characters.'; return }
  if (pwNew.value !== pwConfirm.value) { pwError.value = 'Passwords do not match.'; return }
  pwLoading.value = true
  try {
    await authApi.changePassword(pwCurrent.value, pwNew.value)
    pwSuccess.value = true
    pwCurrent.value = ''
    pwNew.value = ''
    pwConfirm.value = ''
    setTimeout(() => { pwSuccess.value = false }, 4000)
  } catch (e: any) {
    pwError.value = e.response?.data?.message ?? 'Failed to change password.'
  } finally {
    pwLoading.value = false
  }
}

onMounted(async () => {
  await auth.fetchMe()
})

async function startSetup() {
  loading.value = true
  verifyError.value = ''
  try {
    const { data } = await authApi.setup2fa()
    qrSvg.value    = data.qr_svg
    totpSecret.value = data.secret
    setupStep.value = 'qr'
  } finally {
    loading.value = false
  }
}

async function verifyAndEnable() {
  if (!verifyCode.value) return
  verifyError.value = ''
  loading.value = true
  try {
    const { data } = await authApi.enable2fa(verifyCode.value)
    recoveryCodes.value = data.recovery_codes
    setupStep.value = 'codes'
    await auth.fetchMe()
  } catch (e: any) {
    verifyError.value = e.response?.data?.message ?? 'Invalid code'
  } finally {
    loading.value = false
    verifyCode.value = ''
  }
}

async function confirmCodes() {
  setupStep.value = 'idle'
  recoveryCodes.value = []
}

async function disableMfa() {
  disableError.value = ''
  loading.value = true
  try {
    await authApi.disable2fa()
    showDisable.value = false
    await auth.fetchMe()
  } catch (e: any) {
    disableError.value = e.response?.data?.message ?? 'Failed'
  } finally {
    loading.value = false
  }
}

async function copyCodes() {
  await navigator.clipboard.writeText(recoveryCodes.value.join('\n'))
  copied.value = true
  setTimeout(() => { copied.value = false }, 2000)
}
</script>

<template>
  <div class="max-w-xl space-y-6">
    <h1 class="text-2xl font-semibold text-gray-900">My Account</h1>

    <!-- MFA enforce banner -->
    <div v-if="auth.mustSetupMfa"
      class="flex items-start gap-3 bg-amber-50 border border-amber-300 rounded-xl px-4 py-3 text-sm text-amber-800">
      <span class="text-lg leading-none mt-0.5">🔒</span>
      <div>
        <p class="font-semibold">Two-factor authentication required</p>
        <p class="text-xs mt-0.5">Your administrator has made 2FA mandatory. Please set up an authenticator app below before you can use Oachkatzl.</p>
      </div>
    </div>

    <!-- Profile info -->
    <div class="bg-white rounded-xl border border-gray-200 p-6 space-y-3">
      <h2 class="text-sm font-semibold text-gray-700 mb-3">Profile</h2>
      <div class="grid grid-cols-2 gap-y-2 text-sm">
        <span class="text-gray-400">Username</span>
        <span class="font-medium text-gray-900">{{ auth.user?.username }}</span>
        <span class="text-gray-400">E-Mail</span>
        <span class="text-gray-900">{{ auth.user?.email || '—' }}</span>
        <span class="text-gray-400">Role</span>
        <span class="text-gray-900">{{ auth.isAdmin ? 'Administrator' : 'User' }}</span>
        <span class="text-gray-400">Auth provider</span>
        <span class="text-gray-900 capitalize">{{ auth.user?.auth_provider || 'local' }}</span>
      </div>
    </div>

    <!-- Change password (local accounts only) -->
    <div v-if="isLocalUser" class="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
      <div class="flex items-center gap-2">
        <Lock class="w-5 h-5 text-gray-500" />
        <h2 class="text-sm font-semibold text-gray-700">Change Password</h2>
      </div>
      <div class="space-y-3 max-w-sm">
        <div>
          <label class="block text-xs font-medium text-gray-600 mb-1">Current password</label>
          <input v-model="pwCurrent" type="password" autocomplete="current-password"
            class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
        </div>
        <div>
          <label class="block text-xs font-medium text-gray-600 mb-1">New password <span class="text-gray-400">(min. 8 characters)</span></label>
          <input v-model="pwNew" type="password" autocomplete="new-password"
            class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
        </div>
        <div>
          <label class="block text-xs font-medium text-gray-600 mb-1">Confirm new password</label>
          <input v-model="pwConfirm" type="password" autocomplete="new-password" @keydown.enter="changePassword"
            class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            :class="pwConfirm && pwNew !== pwConfirm ? 'border-red-400' : ''" />
        </div>
        <p v-if="pwError" class="text-xs text-red-500">{{ pwError }}</p>
        <div class="flex items-center gap-3 pt-1">
          <button @click="changePassword" :disabled="pwLoading || !pwCurrent || !pwNew || !pwConfirm"
            class="bg-brand-600 hover:bg-brand-700 text-white text-sm px-4 py-2 rounded-lg disabled:opacity-60 transition-colors">
            {{ pwLoading ? 'Saving…' : 'Change password' }}
          </button>
          <span v-if="pwSuccess" class="flex items-center gap-1 text-sm text-green-600">
            <Check class="w-4 h-4" /> Password updated
          </span>
        </div>
      </div>
    </div>
    <div v-else class="bg-gray-50 border border-gray-200 rounded-xl p-4 text-sm text-gray-500 flex items-center gap-2">
      <Lock class="w-4 h-4 shrink-0" />
      Password is managed by your external authentication provider ({{ auth.user?.auth_provider }}).
    </div>

    <!-- MFA -->
    <div class="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <KeyRound class="w-5 h-5 text-gray-500" />
          <h2 class="text-sm font-semibold text-gray-700">Two-Factor Authentication (TOTP)</h2>
        </div>
        <span class="text-xs font-medium px-2 py-0.5 rounded-full"
          :class="mfaEnabled ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'">
          {{ mfaEnabled ? 'Enabled' : 'Disabled' }}
        </span>
      </div>

      <!-- Enabled state -->
      <template v-if="mfaEnabled && setupStep === 'idle'">
        <p class="text-sm text-gray-500">Your account is protected with an authenticator app.</p>
        <button v-if="!showDisable" @click="showDisable = true"
          class="flex items-center gap-2 text-sm text-red-500 hover:text-red-700 border border-red-200 hover:border-red-400 px-3 py-1.5 rounded-lg transition-colors">
          <ShieldOff class="w-4 h-4" /> Disable 2FA
        </button>
        <div v-if="showDisable" class="flex items-center gap-2">
          <button @click="disableMfa" :disabled="loading"
            class="bg-red-500 hover:bg-red-600 text-white text-sm px-3 py-1.5 rounded-lg disabled:opacity-60">
            {{ loading ? 'Disabling…' : 'Yes, disable 2FA' }}
          </button>
          <button @click="showDisable = false" class="text-sm text-gray-400 hover:text-gray-600">Cancel</button>
          <p v-if="disableError" class="text-xs text-red-500 ml-2">{{ disableError }}</p>
        </div>
      </template>

      <!-- Disabled state -->
      <template v-else-if="!mfaEnabled && setupStep === 'idle'">
        <p class="text-sm text-gray-500">Protect your account with an authenticator app (Google Authenticator, Aegis, etc.).</p>
        <button @click="startSetup" :disabled="loading"
          class="flex items-center gap-2 bg-brand-600 hover:bg-brand-700 text-white text-sm px-4 py-2 rounded-lg disabled:opacity-60">
          <ShieldCheck class="w-4 h-4" />
          {{ loading ? 'Loading…' : 'Set up 2FA' }}
        </button>
      </template>

      <!-- Step 1: QR code -->
      <template v-if="setupStep === 'qr'">
        <p class="text-sm text-gray-600">Scan the QR code with your authenticator app, then enter the 6-digit code to confirm.</p>
        <div class="flex justify-center p-4 bg-white border border-gray-200 rounded-xl" v-html="qrSvg" />
        <details class="text-xs text-gray-400">
          <summary class="cursor-pointer hover:text-gray-600">Can't scan? Enter manually</summary>
          <p class="mt-1 font-mono bg-gray-50 border border-gray-200 rounded px-3 py-2 select-all break-all">{{ totpSecret }}</p>
        </details>
        <div class="flex gap-2 items-center">
          <input v-model="verifyCode" @keydown.enter="verifyAndEnable"
            class="border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono w-36 focus:outline-none focus:ring-2 focus:ring-brand-500"
            placeholder="123456" maxlength="6" autofocus />
          <button @click="verifyAndEnable" :disabled="loading || verifyCode.length < 6"
            class="bg-brand-600 hover:bg-brand-700 text-white text-sm px-4 py-2 rounded-lg disabled:opacity-60">
            {{ loading ? 'Verifying…' : 'Activate' }}
          </button>
          <button @click="setupStep = 'idle'" class="text-sm text-gray-400 hover:text-gray-600">Cancel</button>
        </div>
        <p v-if="verifyError" class="text-xs text-red-500">{{ verifyError }}</p>
      </template>

      <!-- Step 2: Recovery codes -->
      <template v-if="setupStep === 'codes'">
        <div class="callout bg-amber-50 border border-amber-200 rounded-xl p-4 space-y-3">
          <p class="text-sm font-semibold text-amber-800">✅ 2FA activated — save your recovery codes</p>
          <p class="text-xs text-amber-700">Store these codes in a safe place. Each code can be used once if you lose access to your authenticator app.</p>
          <div class="grid grid-cols-2 gap-1">
            <code v-for="c in recoveryCodes" :key="c"
              class="text-xs font-mono bg-white border border-amber-200 rounded px-2 py-1 text-center tracking-widest">
              {{ c }}
            </code>
          </div>
          <div class="flex gap-2 pt-1">
            <button @click="copyCodes"
              class="flex items-center gap-1.5 text-xs border border-amber-300 text-amber-700 hover:bg-amber-100 px-3 py-1.5 rounded-lg">
              <component :is="copied ? Check : Copy" class="w-3.5 h-3.5" />
              {{ copied ? 'Copied!' : 'Copy all' }}
            </button>
            <button @click="confirmCodes"
              class="flex items-center gap-1.5 text-xs bg-amber-600 hover:bg-amber-700 text-white px-3 py-1.5 rounded-lg">
              I've saved my codes
            </button>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>
