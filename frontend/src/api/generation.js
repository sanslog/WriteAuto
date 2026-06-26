import client from './client'

export const generationAPI = {
  prepare: (novelId) => client.post(`/novels/${novelId}/generate/prepare`),
  run: (genId, data) => client.post(`/generations/${genId}/run`, data),
  status: (genId) => client.get(`/generations/${genId}/status`),
  judge: (genId, data) => client.post(`/generations/${genId}/judge`, data),
  cancel: (genId) => client.post(`/generations/${genId}/cancel`),
}
