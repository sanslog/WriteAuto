import client from './client'

export const outlineAPI = {
  list: (novelId) => client.get(`/novels/${novelId}/outline`),
  create: (data) => client.post('/plot-nodes', data),
  update: (id, data) => client.put(`/plot-nodes/${id}`, data),
  delete: (id) => client.delete(`/plot-nodes/${id}`),
}
