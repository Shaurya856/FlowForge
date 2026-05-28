import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

// Workflows
export const getWorkflows = () => api.get('/workflows')
export const createWorkflow = (data: { name: string; description: string }) => api.post('/workflows', data)
export const deleteWorkflow = (id: string) => api.delete(`/workflows/${id}`)
export const updateWorkflow = (id: string, data: any) => api.put(`/workflows/${id}`, data)
export const validateWorkflow = (id: string) => api.get(`/workflows/${id}/validate`)
export const exportWorkflow = (id: string) => api.get(`/workflows/${id}/export`)
export const importWorkflow = (data: any) => api.post('/workflows/import', data)

// Steps
export const getSteps = (workflowId: string) => api.get(`/workflows/${workflowId}/steps`)
export const createStep = (workflowId: string, data: any) => api.post(`/workflows/${workflowId}/steps`, data)
export const deleteStep = (stepId: string) => api.delete(`/steps/${stepId}`)
export const updateStep = (stepId: string, data: any) => api.put(`/steps/${stepId}`, data)

// Executions
export const startExecution = (data: any) => api.post('/executions', data)
export const getExecutions = (workflowId?: string) =>
  api.get('/executions', { params: workflowId ? { workflow_id: workflowId } : {} })
export const getExecution = (id: string) => api.get(`/executions/${id}`)
export const getTraces = (id: string) => api.get(`/executions/${id}/traces`)
export const getMetrics = (id: string) => api.get(`/executions/${id}/metrics`)
export const getAnomalies = (id: string) => api.get(`/executions/${id}/anomalies`)
export const cancelExecution = (id: string) => api.post(`/executions/${id}/cancel`)

// Mock
export const getMockConfigs = () => api.get('/mock-configs')
export const createMockConfig = (data: any) => api.post('/mock-configs', data)
export const deleteMockConfig = (id: string) => api.delete(`/mock-configs/${id}`)

// Dashboard + Analytics
export const getDashboard = () => api.get('/dashboard')
export const getAnalytics = (workflowId?: string) =>
  api.get('/analytics', { params: workflowId ? { workflow_id: workflowId } : {} })
export const getBaseline = (workflowId: string) => api.get(`/baseline/${workflowId}`)
