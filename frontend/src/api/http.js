import axios from 'axios'

const http = axios.create({ baseURL: '/api', timeout: 60000 })

http.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  const type = localStorage.getItem('auth_type')
  if (token) config.headers.Authorization = `Bearer ${token}`
  if (type) config.headers['X-Auth-Type'] = type
  return config
})

http.interceptors.response.use(
  (res) => res,
  (err) => {
    const url = err.config?.url || ''
    if (err.response?.status === 401) {
      const isLogin =
        url.includes('/auth/login') || url.includes('/platform/auth/login')
      if (!isLogin) {
        console.warn('API 401:', url)
        const authType = localStorage.getItem('auth_type')
        if (authType === 'platform' && url.includes('/platform/')) {
          clearAuth()
          if (!window.location.pathname.startsWith('/platform/login')) {
            window.location.assign('/platform/login')
          }
        }
      }
    }
    return Promise.reject(err)
  },
)

export default http

export function setAuth(token, type = 'tenant') {
  localStorage.setItem('token', token)
  localStorage.setItem('auth_type', type)
}

export function clearAuth() {
  localStorage.removeItem('token')
  localStorage.removeItem('auth_type')
}

/** FastAPI 错误 detail 可能是字符串或校验数组 */
export function formatApiError(err, fallback = '请求失败') {
  const detail = err?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail.map((x) => x.msg || x.message || String(x)).join('；') || fallback
  }
  if (detail && typeof detail === 'object') return detail.message || fallback
  return err?.message || fallback
}
