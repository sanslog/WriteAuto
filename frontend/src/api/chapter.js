import client from './client'

export const chapterAPI = {
  list: (novelId) => client.get(`/novels/${novelId}/chapters`),
  get: (id) => client.get(`/chapters/${id}`),
  create: (data) => client.post('/chapters', data),
  update: (id, data) => client.put(`/chapters/${id}`, data),
  delete: (id) => client.delete(`/chapters/${id}`),
}
