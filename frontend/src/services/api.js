import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (r) => r,
  (err) => {
    const url = err.config?.url || ''
    if (err.response?.status === 401 && !url.includes('/auth/token')) {
      localStorage.removeItem('token')
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
  listarAuditoria: (params) => api.get('/auth/auditoria', { params }),
  exportarAuditoria: (params) => api.get('/auth/auditoria/export', { params, responseType: 'blob' }),
  forgotPassword: (email) => api.post('/auth/password/forgot', { email }),
  resetPassword: (token, novaSenha) => api.post('/auth/password/reset', { token, nova_senha: novaSenha }),
}

export const cadastros = {
  listar: (params) => api.get('/cadastros/', { params }),
  buscar: (id) => api.get(`/cadastros/${id}`),
  criar: (data) => api.post('/cadastros/', data),
  atualizar: (id, data) => api.patch(`/cadastros/${id}`, data),
  previewTermo: async (data) => {
    const r = await api.post('/cadastros/preview-termo', data, { responseType: 'blob' })
    return r.data
  },
  excluirLgpd: (id, motivo) => api.post(`/cadastros/${id}/lgpd/excluir`, { motivo }),
  excluir: (id) => api.delete(`/cadastros/${id}`),
  aprovar: (id) => api.post(`/cadastros/${id}/aprovar`),
  baixarPdf: async (id) => {
    const r = await api.get(`/cadastros/${id}/pdf`, { responseType: 'blob' })
    return r.data
  },
  uploadDoc: (id, tipo, arquivo) => {
    const form = new FormData()
    form.append('arquivo', arquivo)
    return api.post(`/cadastros/${id}/documentos/${tipo}`, form)
  },
}

export default api
