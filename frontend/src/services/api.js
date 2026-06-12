import axios from 'axios'

const api = axios.create({ baseURL: import.meta.env.VITE_API_URL + '/api', withCredentials: true })

// Interceptor de Requisição: Adiciona o Token de forma segura
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Interceptor de Resposta: Protege contra erros de redirecionamento em loop
api.interceptors.response.use(
  (r) => r,
  (err) => {
    const status = err.response?.status;
    const url = err.config?.url || '';
    
    if (status === 401 && !url.includes('/auth/token') && !url.includes('/auth/me')) {
      localStorage.removeItem('token');
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(err);
  }
);

// Cache de cadastros (Seguro)
const cadastrosListCache = new Map()
const CADASTROS_CACHE_MS = 5 * 60 * 1000
const CADASTROS_SESSION_PREFIX = 'cadastros:list:'

const cacheKey = (params = {}) => {
  const clean = Object.entries(params || {})
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

// Auth Seguro
export const auth = {
  login: async (email, senha) => {
    try {
      const response = await api.post('/auth/token', new URLSearchParams({ username: email, password: senha }),
        { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } })
      
      const token = response?.data?.access_token || response?.data?.token;
      if (token) {
        localStorage.setItem('token', token);
      }
      return response;
    } catch (error) {
      console.error("Erro no login:", error);
      throw error;
    }
  },
  me: () => api.get('/auth/me').catch(() => ({ data: null })), // Retorna null em vez de quebrar
  listarUsuarios: () => api.get('/auth/usuarios').catch(() => ({ data: [] })),
  criarUsuario: (data) => api.post('/auth/usuarios', data),
  atualizarUsuario: (id, data) => api.patch(`/auth/usuarios/${id}`, data),
  logout: () => {
    localStorage.removeItem('token')
    return api.post('/auth/logout').catch(() => {})
  },
}

// Cadastros com Proteção contra 'undefined'
export const cadastros = {
  listar: async (params) => {
    try {
      const r = await api.get('/cadastros/', { params });
      return r || { data: [] };
    } catch { return { data: [] } }
  },
  listarCached: async (params = {}) => {
    const cached = getCachedList(params)
    if (cached) return { data: cached, cached: true }
    return await cadastros.listar(params)
  },
  buscar: async (id) => {
    try { return await api.get(`/cadastros/${id}`) } catch { return { data: null } }
  },
  // Funções de exportação protegidas
  exportarCsv: async (params) => (await api.get('/cadastros/export/cadastros.csv', { params, responseType: 'blob' }).catch(() => ({data: null}))).data,
  exportarGraficosCsv: async (params) => (await api.get('/cadastros/export/graficos.csv', { params, responseType: 'blob' }).catch(() => ({data: null}))).data,
  exportarCadastrosXlsx: async (params) => (await api.get('/cadastros/export/cadastros.xlsx', { params, responseType: 'blob' }).catch(() => ({data: null}))).data,
  exportarGraficosXlsx: async (params) => (await api.get('/cadastros/export/graficos.xlsx', { params, responseType: 'blob' }).catch(() => ({data: null}))).data,
  // Métodos de escrita com cache clear
  criar: (data) => api.post('/cadastros/', data).then((r) => { clearCadastrosCache(); return r }),
  atualizar: (id, data) => api.patch(`/cadastros/${id}`, data).then((r) => { clearCadastrosCache(); return r }),
  excluir: (id) => api.delete(`/cadastros/${id}`).then((r) => { clearCadastrosCache(); return r }),
}

export default api