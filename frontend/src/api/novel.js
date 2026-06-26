import client from './client'

export const novelAPI = {
  list: () => client.get('/novels'),
  get: (id) => client.get(`/novels/${id}`),
  create: (data) => client.post('/novels', data),
  update: (id, data) => client.put(`/novels/${id}`, data),
  delete: (id) => client.delete(`/novels/${id}`),
  updateCursor: (id, cursorPosition) => client.put(`/novels/${id}/cursor`, { cursor_position: cursorPosition }),
}
