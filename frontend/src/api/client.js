import axios from 'axios'

const client = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

client.interceptors.response.use(
  (res) => res.data,
  (err) => {
    const msg = err.response?.data?.detail || err.message || '请求失败'
    const error = new Error(msg)
    error.response = err.response
    error.request = err.request
    return Promise.reject(error)
  }
)

export default client
