<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()

const username = ref('')
const password = ref('')
const code2fa = ref('')
const tempToken = ref('')
const requires2fa = ref(false)
const error = ref('')
const loading = ref(false)

async function submit() {
  error.value = ''
  loading.value = true
  try {
    if (requires2fa.value) {
      await auth.verify2fa(tempToken.value, code2fa.value)
      router.push('/')
    } else {
      const result = await auth.login(username.value, password.value)
      if (result.requires2fa) {
        tempToken.value = result.tempToken
        requires2fa.value = true
      } else if (result.mfaSetupRequired) {
        router.push('/profile')
      } else {
        router.push('/')
      }
    }
  } catch (e: any) {
    error.value = e.response?.data?.message ?? 'Login failed'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-100 px-4">
    <div class="w-full max-w-sm bg-white rounded-2xl shadow-lg p-8">
      <div class="flex items-center gap-3 mb-1">
        <img src="@/assets/logo.svg" alt="Oachkatzl" class="w-10 h-10 rounded-xl" />
        <h1 class="text-2xl font-bold text-gray-900">Oachkatzl</h1>
      </div>
      <p class="text-sm text-gray-500 mb-6">{{ requires2fa ? 'Enter your 2FA code' : 'Sign in to your account' }}</p>

      <form @submit.prevent="submit" class="space-y-4">
        <template v-if="!requires2fa">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Username</label>
            <input
              v-model="username"
              type="text"
              autocomplete="username"
              required
              class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Password</label>
            <input
              v-model="password"
              type="password"
              autocomplete="current-password"
              required
              class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </div>
        </template>

        <template v-else>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Authenticator code or recovery code</label>
            <input
              v-model="code2fa"
              type="text"
              inputmode="numeric"
              autocomplete="one-time-code"
              maxlength="10"
              required
              class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm text-center tracking-widest font-mono focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </div>
          <button type="button" class="text-xs text-gray-400 hover:text-gray-600" @click="requires2fa = false">
            ← Back to login
          </button>
        </template>

        <p v-if="error" class="text-sm text-red-600">{{ error }}</p>

        <button
          type="submit"
          :disabled="loading"
          class="w-full bg-brand-600 hover:bg-brand-700 text-white font-medium py-2 px-4 rounded-lg text-sm transition-colors disabled:opacity-60"
        >
          {{ loading ? 'Signing in…' : requires2fa ? 'Verify' : 'Sign in' }}
        </button>
      </form>
    </div>
  </div>
</template>
