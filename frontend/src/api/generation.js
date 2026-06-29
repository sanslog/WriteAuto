import client from './client'

export const generationAPI = {
  /** Prepare a generation session — returns { success, data: { generation_id, … } } */
  prepare: (novelId) => client.post(`/novels/${novelId}/generate/prepare`),

  /** Cancel a running generation — simple POST, no SSE needed */
  cancel: (genId) => client.post(`/generations/${genId}/cancel`),
}
