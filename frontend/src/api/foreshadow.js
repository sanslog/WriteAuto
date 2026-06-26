import client from './client'

export const foreshadowAPI = {
  list: (novelId) => client.get(`/novels/${novelId}/foreshadows`),
  create: (data) => client.post('/foreshadows', data),
  update: (id, data) => client.put(`/foreshadows/${id}`, data),
  delete: (id) => client.delete(`/foreshadows/${id}`),
}
