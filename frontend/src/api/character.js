import client from './client'

export const characterAPI = {
  list: (novelId) => client.get(`/novels/${novelId}/characters`),
  create: (data) => client.post('/characters', data),
  update: (id, data) => client.put(`/characters/${id}`, data),
  delete: (id) => client.delete(`/characters/${id}`),
}
