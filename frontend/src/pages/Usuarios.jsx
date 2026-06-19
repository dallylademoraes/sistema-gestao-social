import { useEffect, useState } from 'react'
import { useAuth } from '../hooks/useAuth'
import { auth } from '../services/api'

export default function Usuarios() {
  const { usuario } = useAuth()
  const [lista, setLista] = useState([])
  const [carregando, setCarregando] = useState(true)
  const [carregandoAuditoria, setCarregandoAuditoria] = useState(true)
  const [salvando, setSalvando] = useState(false)
  const [salvandoLinhaId, setSalvandoLinhaId] = useState(null)
  const [erro, setErro] = useState('')
  const [ok, setOk] = useState('')
  const [auditoria, setAuditoria] = useState([])
  const [auditAction, setAuditAction] = useState('')
  const [auditUser, setAuditUser] = useState('')
  const [auditFrom, setAuditFrom] = useState('')
  const [auditTo, setAuditTo] = useState('')
  const [auditSkip, setAuditSkip] = useState(0)
  const [auditLimit, setAuditLimit] = useState(20)
  const [auditTotal, setAuditTotal] = useState(0)
  const [edicao, setEdicao] = useState({})
  const [form, setForm] = useState({
    nome: '',
    email: '',
    senha: '',
    perfil: 'assistente',
  })

  const ehCoordenadora = usuario?.perfil === 'coordenadora'

  const actionLabels = {
    'user.create': 'Usuário criado',
    'user.update': 'Usuário atualizado',
    'cadastro.create': 'Cadastro criado',
    'cadastro.update': 'Cadastro atualizado',
    'cadastro.approve': 'Cadastro aprovado',
    'cadastro.delete': 'Cadastro excluído',
  }

  const carregar = async () => {
    setCarregando(true)
    setErro('')
    try {
      const r = await auth.listarUsuarios()
      setLista(r.data)
      const estadoInicial = {}
      for (const u of r.data) {
        estadoInicial[u.id] = {
          nome: u.nome,
          email: u.email,
          perfil: u.perfil,
          ativo: u.ativo,
        }
      }
      setEdicao(estadoInicial)
    } catch (e) {
      setErro(e.response?.data?.detail || 'Não foi possível carregar usuários.')
    } finally {
      setCarregando(false)
    }
  }

  const carregarAuditoria = async (skip = auditSkip) => {
    setCarregandoAuditoria(true)
    try {
      const params = {
        limit: auditLimit,
        skip,
        action: auditAction || undefined,
        usuario: auditUser.trim() || undefined,
        data_inicio: auditFrom ? `${auditFrom}T00:00:00` : undefined,
        data_fim: auditTo ? `${auditTo}T23:59:59` : undefined,
      }
      const r = await auth.listarAuditoria(params)
      setAuditoria(r.data.items)
      setAuditTotal(r.data.total)
      setAuditSkip(r.data.skip)
    } catch {
      // manter silencioso para não bloquear gestão de usuários
    } finally {
      setCarregandoAuditoria(false)
    }
  }

  useEffect(() => {
    if (ehCoordenadora) {
      carregar()
      carregarAuditoria(0)
    }
  }, [ehCoordenadora])

  useEffect(() => {
    if (ehCoordenadora) carregarAuditoria(0)
  }, [auditAction, auditUser, auditFrom, auditTo, auditLimit])

  const update = (field) => (e) => {
    setForm((prev) => ({ ...prev, [field]: e.target.value }))
  }

  const submit = async (e) => {
    e.preventDefault()
    setSalvando(true)
    setErro('')
    setOk('')
    try {
      await auth.criarUsuario(form)
      setOk('Usuário criado com sucesso.')
      setForm({ nome: '', email: '', senha: '', perfil: 'assistente' })
      await carregar()
      await carregarAuditoria(0)
    } catch (err) {
      setErro(err.response?.data?.detail || 'Erro ao criar usuário.')
    } finally {
      setSalvando(false)
    }
  }

  const updateEdicao = (id, field) => (e) => {
    const value = field === 'ativo' ? e.target.checked : e.target.value
    setEdicao((prev) => ({
      ...prev,
      [id]: {
        ...prev[id],
        [field]: value,
      },
    }))
  }

  const salvarLinha = async (id) => {
    const originalDados = edicao[id]
    if (!originalDados) return
    const dados = { ...originalDados }
    if (!dados.nova_senha) {
      delete dados.nova_senha
    }
    
    setErro('')
    setOk('')
    setSalvandoLinhaId(id)
    try {
      await auth.atualizarUsuario(id, dados)
      setOk('Usuário atualizado com sucesso.')
      await carregar()
      await carregarAuditoria(auditSkip)
    } catch (err) {
      setErro(err.response?.data?.detail || 'Erro ao atualizar usuário.')
    } finally {
      setSalvandoLinhaId(null)
    }
  }

  const handleExcluirUsuario = async (u) => {
    if (!window.confirm(`ATENÇÃO: Deseja EXCLUIR PERMANENTEMENTE o usuário "${u.nome}"? Esta ação não pode ser desfeita.`)) {
      return
    }
    setErro('')
    setOk('')
    try {
      await auth.excluirUsuario(u.id)
      setOk('Usuário excluído permanentemente.')
      await carregar()
      await carregarAuditoria(0)
    } catch (err) {
      setErro(err.response?.data?.detail || 'Erro ao excluir usuário.')
    }
  }

  if (!ehCoordenadora) {
    return (
      <div className="centered-form-shell">
        <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 8 }}>Sem permissão</h1>
        <p style={{ color: 'var(--text-muted)' }}>Apenas coordenadora pode gerenciar usuários.</p>
      </div>
    )
  }

  const exportarCsv = async () => {
    try {
      const params = {
        action: auditAction || undefined,
        usuario: auditUser.trim() || undefined,
        data_inicio: auditFrom ? `${auditFrom}T00:00:00` : undefined,
        data_fim: auditTo ? `${auditTo}T23:59:59` : undefined,
      }
      const r = await auth.exportarAuditoria(params)
      const blobUrl = URL.createObjectURL(r.data)
      const a = document.createElement('a')
      a.href = blobUrl
      a.download = 'auditoria.csv'
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(blobUrl)
    } catch {
      setErro('Não foi possível exportar a auditoria em CSV.')
    }
  }

  return (
    <div className="centered-form-shell">
      <h1 style={{ fontSize: 25, fontWeight: 700, marginBottom: '1rem' }}>Usuários</h1>

      <div className="centered-form-card" style={{ marginBottom: '1rem' }}>
        <h2 style={{ fontSize: 16, marginTop: 0 }}>Novo usuário</h2>
        <form onSubmit={submit} autoComplete="off">
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div>
              <label className="form-label">Nome</label>
              <input className="form-input" name="novo-usuario-nome" autoComplete="off" value={form.nome} onChange={update('nome')} required />
            </div>
            <div>
              <label className="form-label">E-mail</label>
              <input className="form-input" type="email" name="novo-usuario-email" autoComplete="off" value={form.email} onChange={update('email')} required />
            </div>
            <div>
              <label className="form-label">Senha</label>
              <input className="form-input" type="password" name="novo-usuario-senha" autoComplete="new-password" value={form.senha} onChange={update('senha')} required />
            </div>
            <div>
              <label className="form-label">Perfil</label>
              <select className="form-select" value={form.perfil} onChange={update('perfil')}>
                <option value="assistente">assistente</option>
                <option value="ti">ti</option>
                <option value="coordenadora">coordenadora</option>
              </select>
            </div>
          </div>
          {erro && <p style={{ color: 'var(--danger)', marginTop: 12, marginBottom: 0 }}>{erro}</p>}
          {ok && <p style={{ color: 'var(--link)', marginTop: 12, marginBottom: 0, fontWeight: 600 }}>{ok}</p>}
          <div style={{ marginTop: 12 }}>
            <button className="btn-primary" type="submit" disabled={salvando}>
              {salvando ? 'Salvando...' : 'Criar usuário'}
            </button>
          </div>
        </form>
      </div>

      <div className="centered-form-card">
        <h2 style={{ fontSize: 16, marginTop: 0 }}>Usuários cadastrados</h2>
        {carregando ? (
          <p style={{ color: 'var(--text-soft)' }}>Carregando...</p>
        ) : lista.length === 0 ? (
          <p style={{ color: 'var(--text-soft)' }}>Nenhum usuário cadastrado.</p>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ background: 'var(--surface-subtle)' }}>
                  <th style={{ textAlign: 'left', padding: '10px', borderBottom: '1px solid var(--border)' }}>Nome</th>
                  <th style={{ textAlign: 'left', padding: '10px', borderBottom: '1px solid var(--border)' }}>E-mail</th>
                  <th style={{ textAlign: 'left', padding: '10px', borderBottom: '1px solid var(--border)' }}>Perfil</th>
                  <th style={{ textAlign: 'left', padding: '10px', borderBottom: '1px solid var(--border)' }}>Nova Senha</th>
                  <th style={{ textAlign: 'left', padding: '10px', borderBottom: '1px solid var(--border)' }}>Ativo</th>
                  <th style={{ textAlign: 'left', padding: '10px', borderBottom: '1px solid var(--border)' }}>Ação</th>
                </tr>
              </thead>
              <tbody>
                {lista.map((u) => (
                  <tr key={u.id} style={{ borderBottom: '1px solid var(--row-border)' }}>
                    <td style={{ padding: '10px' }}>
                      <input
                        className="form-input"
                        style={{ minWidth: 160 }}
                        value={edicao[u.id]?.nome || ''}
                        onChange={updateEdicao(u.id, 'nome')}
                      />
                    </td>
                    <td style={{ padding: '10px', color: 'var(--text-muted)' }}>
                      <input
                        className="form-input"
                        style={{ minWidth: 210 }}
                        type="email"
                        value={edicao[u.id]?.email || ''}
                        onChange={updateEdicao(u.id, 'email')}
                        pattern="[^\s@]+@[^\s@]+\.[^\s@]+"
                        title="Insira um e-mail válido (ex: nome@dominio.com)"
                      />
                    </td>
                    <td style={{ padding: '10px' }}>
                      <select className="form-select" style={{ minWidth: 130 }} value={edicao[u.id]?.perfil || 'assistente'} onChange={updateEdicao(u.id, 'perfil')}>
                        <option value="assistente">assistente</option>
                        <option value="ti">ti</option>
                        <option value="coordenadora">coordenadora</option>
                      </select>
                    </td>
                    <td style={{ padding: '10px' }}>
                      <input
                        className="form-input"
                        style={{ minWidth: 120 }}
                        type="password"
                        placeholder="Em branco = manter"
                        value={edicao[u.id]?.nova_senha || ''}
                        onChange={updateEdicao(u.id, 'nova_senha')}
                      />
                    </td>
                    <td style={{ padding: '10px' }}>
                      <label style={{ display: 'inline-flex', alignItems: 'center', gap: 8, fontSize: 13 }}>
                        <input type="checkbox" checked={Boolean(edicao[u.id]?.ativo)} onChange={updateEdicao(u.id, 'ativo')} />
                        {edicao[u.id]?.ativo ? 'Ativo' : 'Inativo'}
                      </label>
                    </td>
                    <td style={{ padding: '10px', display: 'flex', gap: '8px', alignItems: 'center' }}>
                      <button className="btn-secondary" onClick={() => salvarLinha(u.id)} disabled={salvandoLinhaId === u.id}>
                        {salvandoLinhaId === u.id ? 'Salvando...' : 'Salvar'}
                      </button>
                      {!edicao[u.id]?.ativo && (
                        <button
                          type="button"
                          className="btn-secondary"
                          style={{ borderColor: 'var(--danger)', color: 'var(--danger)' }}
                          onClick={() => handleExcluirUsuario(u)}>
                          Excluir
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="centered-form-card" style={{ marginTop: '1rem' }}>
        <h2 style={{ fontSize: 16, marginTop: 0 }}>Auditoria (últimas ações)</h2>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}>
          <select className="form-select" value={auditAction} onChange={(e) => setAuditAction(e.target.value)} style={{ width: 'auto' }}>
            <option value="">Todas as ações</option>
            <option value="user.create">Usuário criado</option>
            <option value="user.update">Usuário atualizado</option>
            <option value="cadastro.create">Cadastro criado</option>
            <option value="cadastro.update">Cadastro atualizado</option>
            <option value="cadastro.approve">Cadastro aprovado</option>
            <option value="cadastro.delete">Cadastro excluído</option>
          </select>
          <input
            className="form-input"
            type="text"
            placeholder="Buscar por usuário"
            value={auditUser}
            onChange={(e) => setAuditUser(e.target.value)}
            style={{ width: 220 }}
          />
          <input className="form-input" type="date" value={auditFrom} onChange={(e) => setAuditFrom(e.target.value)} style={{ width: 'auto' }} />
          <input className="form-input" type="date" value={auditTo} onChange={(e) => setAuditTo(e.target.value)} style={{ width: 'auto' }} />
          <select className="form-select" value={auditLimit} onChange={(e) => setAuditLimit(Number(e.target.value))} style={{ width: 'auto' }}>
            <option value={20}>20 por página</option>
            <option value={50}>50 por página</option>
            <option value={100}>100 por página</option>
          </select>
          <button className="btn-secondary" onClick={exportarCsv}>Exportar CSV</button>
        </div>
        {carregandoAuditoria ? (
          <p style={{ color: 'var(--text-soft)' }}>Carregando...</p>
        ) : auditoria.length === 0 ? (
          <p style={{ color: 'var(--text-soft)' }}>Nenhum log de auditoria ainda.</p>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ background: 'var(--surface-subtle)' }}>
                  <th style={{ textAlign: 'left', padding: '10px', borderBottom: '1px solid var(--border)' }}>Quando</th>
                  <th style={{ textAlign: 'left', padding: '10px', borderBottom: '1px solid var(--border)' }}>Quem</th>
                  <th style={{ textAlign: 'left', padding: '10px', borderBottom: '1px solid var(--border)' }}>Ação</th>
                  <th style={{ textAlign: 'left', padding: '10px', borderBottom: '1px solid var(--border)' }}>Entidade</th>
                  <th style={{ textAlign: 'left', padding: '10px', borderBottom: '1px solid var(--border)' }}>IP</th>
                </tr>
              </thead>
              <tbody>
                {auditoria.map((a) => (
                  <tr key={a.id} style={{ borderBottom: '1px solid var(--row-border)' }}>
                    <td style={{ padding: '10px' }}>{new Date(a.created_em).toLocaleString('pt-BR')}</td>
                    <td style={{ padding: '10px' }}>{a.actor_nome || 'Sistema'}</td>
                    <td style={{ padding: '10px' }}>{actionLabels[a.action] || a.action}</td>
                    <td style={{ padding: '10px' }}>{a.entity_type} #{a.entity_id ?? '—'}</td>
                    <td style={{ padding: '10px', color: 'var(--text-muted)' }}>{a.ip_address || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <div style={{ marginTop: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
          <button className="btn-secondary" onClick={() => carregarAuditoria(Math.max(0, auditSkip - auditLimit))} disabled={auditSkip === 0 || carregandoAuditoria}>
            Anterior
          </button>
          <button className="btn-secondary" onClick={() => carregarAuditoria(auditSkip + auditLimit)} disabled={auditSkip + auditLimit >= auditTotal || carregandoAuditoria}>
            Próxima
          </button>
          <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
            Mostrando {auditTotal === 0 ? 0 : auditSkip + 1} - {Math.min(auditSkip + auditLimit, auditTotal)} de {auditTotal}
          </span>
        </div>
      </div>
    </div>
  )
}
