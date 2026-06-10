import api from './client'

export const ldapApi = {
  getConfig:      ()           => api.get('/ldap/config'),
  saveConfig:     (data: any)  => api.put('/ldap/config', data),
  testConnection: ()           => api.post('/ldap/test'),
  getMappings:    ()           => api.get('/ldap/mappings'),
  createMapping:  (data: any)  => api.post('/ldap/mappings', data),
  deleteMapping:  (id: string) => api.delete(`/ldap/mappings/${id}`),
}
