import api from './client'

export const authApi = {
  login: (username: string, password: string) =>
    api.post('/auth/login', { username, password }),

  verify2fa: (tempToken: string, code: string) =>
    api.post('/auth/login/verify-2fa', { temp_token: tempToken, code }),

  me: () => api.get('/auth/me'),

  setup2fa: () => api.get('/auth/2fa/setup'),
  enable2fa: (code: string) => api.post('/auth/2fa/enable', { code }),
  disable2fa: () => api.post('/auth/2fa/disable'),

  changePassword: (currentPassword: string, newPassword: string) =>
    api.post('/auth/change-password', { current_password: currentPassword, new_password: newPassword }),

  listTokens: () => api.get('/auth/tokens'),
  createToken: (name: string) => api.post('/auth/tokens', { name }),
  revokeToken: (id: string) => api.delete(`/auth/tokens/${id}`),
}
