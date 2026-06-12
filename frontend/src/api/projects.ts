import api from './client'

export const projectsApi = {
  list: () => api.get('/projects'),
  create: (data: { name: string; alert?: boolean }) => api.post('/projects', data),
  get: (id: string) => api.get(`/projects/${id}`),
  update: (id: string, data: object) => api.put(`/projects/${id}`, data),
  delete: (id: string) => api.delete(`/projects/${id}`),

  listMembers: (id: string) => api.get(`/projects/${id}/members`),
  listLdapMappings: (id: string) => api.get(`/projects/${id}/ldap-mappings`),
  listLdapUserMappings:  (id: string)                      => api.get(`/projects/${id}/ldap-user-mappings`),
  createLdapUserMapping: (id: string, data: object)         => api.post(`/projects/${id}/ldap-user-mappings`, data),
  deleteLdapUserMapping: (pid: string, mid: string)         => api.delete(`/projects/${pid}/ldap-user-mappings/${mid}`),
  addMember: (id: string, data: object) => api.post(`/projects/${id}/members`, data),
  updateMember: (pid: string, mid: string, data: object) => api.put(`/projects/${pid}/members/${mid}`, data),
  removeMember: (projectId: string, memberId: string) =>
    api.delete(`/projects/${projectId}/members/${memberId}`),

  listTemplates: (id: string, page = 1, perPage = 20) =>
    api.get(`/projects/${id}/templates`, { params: { page, per_page: perPage } }),
  createTemplate: (id: string, data: object) => api.post(`/projects/${id}/templates`, data),
  getTemplate: (pid: string, tid: string) => api.get(`/projects/${pid}/templates/${tid}`),
  updateTemplate: (pid: string, tid: string, data: object) =>
    api.put(`/projects/${pid}/templates/${tid}`, data),
  deleteTemplate: (pid: string, tid: string) =>
    api.delete(`/projects/${pid}/templates/${tid}`),

  listTasks: (id: string, page = 1, perPage = 20) =>
    api.get(`/projects/${id}/tasks`, { params: { page, per_page: perPage } }),
  startTask: (pid: string, tid: string, data?: object) =>
    api.post(`/projects/${pid}/tasks/${tid}/start`, data ?? {}),
  getTask: (pid: string, taskId: string) => api.get(`/projects/${pid}/tasks/${taskId}`),
  stopTask: (pid: string, taskId: string) =>
    api.post(`/projects/${pid}/tasks/${taskId}/stop`),
  getTaskLog: (pid: string, taskId: string) =>
    api.get(`/projects/${pid}/tasks/${taskId}/log`),

  listKeys: (id: string) => api.get(`/projects/${id}/keys`),
  createKey: (id: string, data: object) => api.post(`/projects/${id}/keys`, data),
  updateKey: (pid: string, kid: string, data: object) => api.put(`/projects/${pid}/keys/${kid}`, data),
  deleteKey: (pid: string, kid: string) => api.delete(`/projects/${pid}/keys/${kid}`),

  listRepos: (id: string) => api.get(`/projects/${id}/repositories`),
  createRepo: (id: string, data: object) => api.post(`/projects/${id}/repositories`, data),
  updateRepo: (pid: string, rid: string, data: object) => api.put(`/projects/${pid}/repositories/${rid}`, data),
  deleteRepo: (pid: string, rid: string) => api.delete(`/projects/${pid}/repositories/${rid}`),

  listInventories: (id: string) => api.get(`/projects/${id}/inventories`),
  createInventory: (id: string, data: object) => api.post(`/projects/${id}/inventories`, data),
  updateInventory: (pid: string, iid: string, data: object) => api.put(`/projects/${pid}/inventories/${iid}`, data),
  deleteInventory: (pid: string, iid: string) => api.delete(`/projects/${pid}/inventories/${iid}`),

  listEnvironments: (id: string) => api.get(`/projects/${id}/environments`),
  createEnvironment: (id: string, data: object) => api.post(`/projects/${id}/environments`, data),
  updateEnvironment: (pid: string, eid: string, data: object) => api.put(`/projects/${pid}/environments/${eid}`, data),
  deleteEnvironment: (pid: string, eid: string) => api.delete(`/projects/${pid}/environments/${eid}`),

  listBuilds: (pid: string, tid: string) => api.get(`/projects/${pid}/templates/${tid}/builds`),

  listCredentials: (pid: string) => api.get(`/projects/${pid}/credentials`),
  createCredential: (pid: string, data: object) => api.post(`/projects/${pid}/credentials`, data),
  updateCredential: (pid: string, cid: string, data: object) => api.put(`/projects/${pid}/credentials/${cid}`, data),
  deleteCredential: (pid: string, cid: string) => api.delete(`/projects/${pid}/credentials/${cid}`),
  listSchedules: (id: string) => api.get(`/projects/${id}/schedules`),
  createSchedule: (id: string, data: object) => api.post(`/projects/${id}/schedules`, data),
  updateSchedule: (pid: string, sid: string, data: object) => api.put(`/projects/${pid}/schedules/${sid}`, data),
  deleteSchedule: (pid: string, sid: string) => api.delete(`/projects/${pid}/schedules/${sid}`),

  // Workflow Templates
  listWorkflows: (pid: string) => api.get(`/projects/${pid}/workflows/`),
  createWorkflow: (pid: string, data: object) => api.post(`/projects/${pid}/workflows/`, data),
  getWorkflow: (pid: string, wid: string) => api.get(`/projects/${pid}/workflows/${wid}`),
  updateWorkflow: (pid: string, wid: string, data: object) => api.put(`/projects/${pid}/workflows/${wid}`, data),
  deleteWorkflow: (pid: string, wid: string) => api.delete(`/projects/${pid}/workflows/${wid}`),
  startWorkflow: (pid: string, wid: string, data?: object) =>
    api.post(`/projects/${pid}/workflows/${wid}/start`, data ?? {}),

  // Workflow Runs
  listWorkflowRuns: (pid: string, page = 1, perPage = 20) =>
    api.get(`/projects/${pid}/workflow-runs/`, { params: { page, per_page: perPage } }),
  getWorkflowRun: (pid: string, runId: string) => api.get(`/projects/${pid}/workflow-runs/${runId}`),
  stopWorkflowRun: (pid: string, runId: string) => api.post(`/projects/${pid}/workflow-runs/${runId}/stop`),
}
