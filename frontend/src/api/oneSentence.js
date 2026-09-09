import client from './client'

export const oneSentenceAPI = {
  cancel: (generationId) => client.post(`/one-sentence/${generationId}/cancel`),
  status: (generationId) => client.get(`/one-sentence/${generationId}/status`),
}
