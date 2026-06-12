import axios from 'axios'

// Instância da API
const api = axios.create({ baseURL: import.meta.env.VITE_API_URL + '/api' })

// Interceptor: Adiciona o token em todas as requisições
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Interceptor: Redireciona para login em caso de 401
api.interceptors.response.use(
  (r) => r,
  (err) => {
    const url = err.config?.url || ''
    const isAuthMe = url.includes('/auth/me')
    const isLoginPage = typeof window !== 'undefined' && window.location.pathname === '/login'
    
    if (err.response?.status === 401 && !url.includes('/auth/token') && !isAuthMe && !isLoginPage) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

// Cache de cadastros
const cadastrosListCache = new Map()
const CADASTROS_CACHE_MS = 5 * 60 * 1000
const CADASTROS_SESSION_PREFIX = 'cadastros:list:'

const cacheKey = (params = {}) => {
  const clean = Object.entries(params)
    .filter(([key, value]) => key !== '_ts' && value !== undefined && value !== null && value !== '')
    .sort(([a], [b]) => a.localeCompare(b))
  return JSON.stringify(clean)
}

const getCachedList = (params = {}) => {
  const key = cacheKey(params)
  const item = cadastrosListCache.get(key)
  if (!item) {
    try {
      const raw = sessionStorage.getItem(`${CADASTROS_SESSION_PREFIX}${key}`)
      if (!raw) return null
      const parsed = JSON.parse(raw)
      if (Date.now() - parsed.at > CADASTROS_CACHE_MS) return null
      cadastrosListCache.set(key, parsed)
      return parsed.data
    } catch { return null }
  }
  return Date.now() - item.at > CADASTROS_CACHE_MS ? null : item.data
}

const setCachedList = (params = {}, data = []) => {
  const key = cacheKey(params)
  const item = { at: Date.now(), data }
  cadastrosListCache.set(key, item)
  try { sessionStorage.setItem(`${CADASTROS_SESSION_PREFIX}${key}`, JSON.stringify(item)) } catch {}
}

const clearCadastrosCache = () => {
  cadastrosListCache.clear()
  try {
    Object.keys(sessionStorage)
      .filter((key) => key.startsWith(CADASTROS_SESSION_PREFIX))
      .forEach((key) => sessionStorage.removeItem(key))
  } catch {}
}

export const auth = {
  login: async (email, senha) => {
    const response = await api.post('/auth/token', new URLSearchParams({ username: email, password: senha }),
      { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } })
    if (response.data.access_token) localStorage.setItem('token', response.data.access_token)
    return response
  },
  me: () => api.get('/auth/me'),
  listarUsuarios: () => api.get('/auth/usuarios'),
  criarUsuario: (data) => api.post('/auth/usuarios', data),
  atualizarUsuario: (id, data) => api.patch(`/auth/usuarios/${id}`, data),
  listarAuditoria: (params) => api.get('/auth/auditoria', { params }),
  exportarAuditoria: (params) => api.get('/auth/auditoria/export', { params, responseType: 'blob' }),
  forgotPassword: (email) => api.post('/auth/password/forgot', { email }),
  resetPassword: (token, novaSenha) => api.post('/auth/password/reset', { token, nova_senha: novaSenha }),
  logout: () => {
    localStorage.removeItem('token')
    return api.post('/auth/logout')
  },
}

export const cadastros = {
  listar: (params) => api.get('/cadastros/', { params }),
  listarCached: async (params = {}) => {
    const cached = getCachedList(params)
    if (cached) {
      api.get('/cadastros/', { params: { ...params, _ts: Date.now() } })
        .then((r) => setCachedList(params, r.data))
        .catch(() => {})
      return { data: cached, cached: true }
    }
    const r = await api.get('/cadastros/', { params: { ...params, _ts: Date.now() } })
    setCachedList(params, r.data)
    return r
  },
  getCachedList,
  buscar: (id) => api.get(`/cadastros/${id}`),
  exportarCsv: async (params) => (await api.get('/cadastros/export/cadastros.csv', { params, responseType: 'blob' })).data,
  exportarGraficosCsv: async (params) => (await api.get('/cadastros/export/graficos.csv', { params, responseType: 'blob' })).data,
  exportarCadastrosXlsx: async (params) => (await api.get('/cadastros/export/cadastros.xlsx', { params, responseType: 'blob' })).data,
  exportarGraficosXlsx: async (params) => (await api.get('/cadastros/export/graficos.xlsx', { params, responseType: 'blob' })).data,
  relatorioComparativoMensal: () => api.get('/cadastros/relatorios/comparativo-mensal'),
  exportarRelatorioComparativoMensalPdf: async () => (await api.get('/cadastros/relatorios/comparativo-mensal.pdf', { responseType: 'blob' })).data,
  criar: (data) => api.post('/cadastros/', data).then((r) => { clearCadastrosCache(); return r }),
  criarPendenteAssinatura: (data) => api.post('/cadastros/pendente-assinatura', data).then((r) => { clearCadastrosCache(); return r }),
  atualizar: (id, data) => api.patch(`/cadastros/${id}`, data).then((r) => { clearCadastrosCache(); return r }),
  assinar: (id, data) => api.post(`/cadastros/${id}/assinar`, data).then((r) => { clearCadastrosCache(); return r }),
  previewTermo: async (data) => (await api.post('/cadastros/preview-termo', data, { responseType: 'blob' })).data,
  excluirLgpd: (id, motivo) => api.post(`/cadastros/${id}/lgpd/excluir`, { motivo }).then((r) => { clearCadastrosCache(); return r }),
  excluir: (id) => api.delete(`/cadastros/${id}`).then((r) => { clearCadastrosCache(); return r }),
  aprovar: (id) => api.post(`/cadastros/${id}/aprovar`).then((r) => { clearCadastrosCache(); return r }),
  baixarPdf: async (id) => (await api.get(`/cadastros/${id}/pdf`, { responseType: 'blob' })).data,
  uploadDoc: (id, tipo, arquivo) => {
    const form = new FormData()
    form.append('arquivo', arquivo)
    return api.post(`/cadastros/${id}/documentos/${tipo}`, form).then((r) => { clearCadastrosCache(); return r })
  },
}

export default api