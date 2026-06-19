import axios from 'axios'

// Send credentials (cookies) with requests so server-set HttpOnly cookie is included
const API_ORIGIN = import.meta.env.VITE_API_URL ?? ''
const api = axios.create({ baseURL: `${API_ORIGIN}/api`, withCredentials: true, timeout: 20000 })

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
  if (!item) return getSessionCachedList(params)
  if (Date.now() - item.at > CADASTROS_CACHE_MS) return null
  return item.data
}

export const buildDocUrl = (path) => {
  if (!path) return null
  if (path.startsWith('http')) return path
  return `${API_ORIGIN}${path}`
}

const setCachedList = (params = {}, data = []) => {
  const key = cacheKey(params)
  const item = { at: Date.now(), data }
  cadastrosListCache.set(key, item)
  try {
    sessionStorage.setItem(`${CADASTROS_SESSION_PREFIX}${key}`, JSON.stringify(item))
  } catch {
    // Cache é só otimização visual; falha de storage não deve afetar a tela.
  }
}

const getSessionCachedList = (params = {}) => {
  const key = cacheKey(params)
  try {
    const raw = sessionStorage.getItem(`${CADASTROS_SESSION_PREFIX}${key}`)
    if (!raw) return null
    const item = JSON.parse(raw)
    if (!item || Date.now() - item.at > CADASTROS_CACHE_MS) return null
    cadastrosListCache.set(key, item)
    return item.data
  } catch {
    return null
  }
}

const clearCadastrosCache = () => {
  cadastrosListCache.clear()
  try {
    Object.keys(sessionStorage)
      .filter((key) => key.startsWith(CADASTROS_SESSION_PREFIX))
      .forEach((key) => sessionStorage.removeItem(key))
  } catch {
    // Ignora falhas de storage.
  }
}

export const normalizarLista = (payload) => {
  if (Array.isArray(payload)) return payload
  if (Array.isArray(payload?.items)) return payload.items
  if (Array.isArray(payload?.data)) return payload.data
  if (Array.isArray(payload?.results)) return payload.results
  return []
}

// With cookie-based auth we don't attach Authorization header from localStorage.
// Keep a simple response interceptor to redirect on 401.
api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 422 && Array.isArray(err.response.data?.detail)) {
      const msgs = err.response.data.detail.map(d => {
        const field = d.loc?.slice(-1)[0]
        return field ? `${field}: ${d.msg}` : d.msg
      })
      err.response.data.detail = msgs.join(' | ')
    }
    
    const url = err.config?.url || ''
    const isAuthMe = url.includes('/auth/me')
    const isLoginPage = typeof window !== 'undefined' && window.location.pathname === '/login'
    if (err.response?.status === 401 && !url.includes('/auth/token') && !isAuthMe && !isLoginPage) {
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export const auth = {
  login: (email, senha) =>
    api.post('/auth/token', new URLSearchParams({ username: email, password: senha }),
      { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }),
  me: () => api.get('/auth/me'),
  listarUsuarios: () => api.get('/auth/usuarios'),
  criarUsuario: (data) => api.post('/auth/usuarios', data),
  atualizarUsuario: (id, data) => api.patch(`/auth/usuarios/${id}`, data),
  excluirUsuario: (id) => api.delete(`/auth/usuarios/${id}`),
  listarAuditoria: (params) => api.get('/auth/auditoria', { params }),
  exportarAuditoria: (params) => api.get('/auth/auditoria/export', { params, responseType: 'blob' }),
  forgotPassword: (email) => api.post('/auth/password/forgot', { email }),
  resetPassword: (token, novaSenha) => api.post('/auth/password/reset', { token, nova_senha: novaSenha }),
  changePassword: (senhaAtual, novaSenha) => api.put('/auth/password/change', { senha_atual: senhaAtual, nova_senha: novaSenha }),
  logout: () => api.post('/auth/logout'),
}

export const cadastros = {
  listar: (params) => api.get('/cadastros/', { params }),
  listarCached: async (params = {}) => {
    const cached = getCachedList(params)
    if (cached) {
      api.get('/cadastros/', { params: { ...params, _ts: Date.now() } })
        .then((r) => setCachedList(params, normalizarLista(r.data)))
        .catch(() => {})
      return { data: cached, cached: true }
    }
    const r = await api.get('/cadastros/', { params: { ...params, _ts: Date.now() } })
    const data = normalizarLista(r.data)
    setCachedList(params, data)
    return { ...r, data }
  },
  getCachedList,
  buscar: (id) => api.get(`/cadastros/${id}`),
  exportarCsv: async (params) => {
    const r = await api.get('/cadastros/export/cadastros.csv', { params, responseType: 'blob' })
    return r.data
  },
  exportarGraficosCsv: async (params) => {
    const r = await api.get('/cadastros/export/graficos.csv', { params, responseType: 'blob' })
    return r.data
  },
  exportarCadastrosXlsx: async (params) => {
    const r = await api.get('/cadastros/export/cadastros.xlsx', { params, responseType: 'blob' })
    return r.data
  },
  exportarGraficosXlsx: async (params) => {
    const r = await api.get('/cadastros/export/graficos.xlsx', { params, responseType: 'blob' })
    return r.data
  },
  relatorioComparativoMensal: () => api.get('/cadastros/relatorios/comparativo-mensal'),
  exportarRelatorioComparativoMensalPdf: async () => {
    const r = await api.get('/cadastros/relatorios/comparativo-mensal.pdf', { responseType: 'blob' })
    return r.data
  },
  criar: (data) => api.post('/cadastros/', data).then((r) => { clearCadastrosCache(); return r }),
  criarPendenteAssinatura: (data) => api.post('/cadastros/pendente-assinatura', data).then((r) => { clearCadastrosCache(); return r }),
  atualizar: (id, data) => api.patch(`/cadastros/${id}`, data).then((r) => { clearCadastrosCache(); return r }),
  assinar: (id, data) => api.post(`/cadastros/${id}/assinar`, data).then((r) => { clearCadastrosCache(); return r }),
  previewTermo: async (data) => {
    const r = await api.post('/cadastros/preview-termo', data, { responseType: 'blob' })
    return r.data
  },
  excluirLgpd: (id, motivo) => api.post(`/cadastros/${id}/lgpd/excluir`, { motivo }).then((r) => { clearCadastrosCache(); return r }),
  excluir: (id) => api.delete(`/cadastros/${id}`).then((r) => { clearCadastrosCache(); return r }),
  aprovar: (id) => api.post(`/cadastros/${id}/aprovar`).then((r) => { clearCadastrosCache(); return r }),
  baixarPdf: async (id) => {
    const r = await api.get(`/cadastros/${id}/pdf`, { responseType: 'blob' })
    return r.data
  },
  uploadDoc: (id, tipo, arquivo) => {
    const form = new FormData()
    form.append('arquivo', arquivo)
    return api.post(`/cadastros/${id}/documentos/${tipo}`, form).then((r) => { clearCadastrosCache(); return r })
  },
}

export default api
