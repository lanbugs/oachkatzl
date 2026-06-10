import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api/auth'

export interface User {
  id: string
  username: string
  email: string
  name: string
  is_admin: boolean
  totp_enabled: boolean
  mfa_setup_required: boolean
  auth_provider: string
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('token'))
  const user = ref<User | null>(null)
  const loading = ref(false)

  const isAuthenticated = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.is_admin ?? false)
  const mustSetupMfa = computed(() => user.value?.mfa_setup_required ?? false)

  async function login(username: string, password: string) {
    const { data } = await authApi.login(username, password)
    if (data.requires_2fa) {
      return { requires2fa: true, tempToken: data.temp_token }
    }
    if (data.mfa_setup_required) {
      // Login succeeded but MFA enforce is on — give the user a token so they
      // can reach the profile page and set up 2FA.
      setToken(data.token)
      await fetchMe()
      return { requires2fa: false, mfaSetupRequired: true }
    }
    setToken(data.token)
    await fetchMe()
    return { requires2fa: false, mfaSetupRequired: false }
  }

  async function verify2fa(tempToken: string, code: string) {
    const { data } = await authApi.verify2fa(tempToken, code)
    setToken(data.token)
    await fetchMe()
  }

  async function fetchMe() {
    try {
      const { data } = await authApi.me()
      user.value = data
    } catch {
      logout()
    }
  }

  function setToken(t: string) {
    token.value = t
    localStorage.setItem('token', t)
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('token')
  }

  return { token, user, loading, isAuthenticated, isAdmin, mustSetupMfa, login, verify2fa, fetchMe, logout }
})
