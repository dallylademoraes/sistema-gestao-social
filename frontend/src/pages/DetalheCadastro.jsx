import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { cadastros as api } from '../services/api'
import { useAuth } from '../hooks/useAuth'
import ConfirmModal from '../components/ConfirmModal'

const campo = (label, valor) => (
  <div key={label} style={{ marginBottom: 12 }}>
    <div style={{ fontSize: 11, color: 'var(--text-soft)', marginBottom: 2, textTransform: 'uppercase', letterSpacing: '0.4px' }}>{label}</div>
    <div style={{ fontSize: 14, color: 'var(--text-main)' }}>{valor || '—'}</div>
  </div>
)

const secao = (titulo) => (
  <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-soft)', textTransform: 'uppercase', letterSpacing: '0.5px', margin: '1.5rem 0 0.75rem', paddingBottom: 6, borderBottom: '1px solid var(--border)' }}>
    {titulo}
  </div>
)

const urlArquivo = (url) => {
  if (!url) return ''
  if (url.startsWith('http://') || url.startsWith('https://') || url.startsWith('/')) return url
  return `/${url}`
}

export default function DetalheCadastro() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { usuario } = useAuth()
  const [cadastro, setCadastro] = useState(null)
  const [aprovando, setAprovando] = useState(false)
  const [excluindo, setExcluindo] = useState(false)
  const [salvandoLgpd, setSalvandoLgpd] = useState(false)
  const [registrandoConsentimento, setRegistrandoConsentimento] = useState(false)
  const [excluindoLgpd, setExcluindoLgpd] = useState(false)
  const [erroLgpd, setErroLgpd] = useState('')
  const [mostrarConfirmacaoExclusao, setMostrarConfirmacaoExclusao] = useState(false)
  const [lgpdForm, setLgpdForm] = useState({
    base_legal: 'consentimento',
    status_lgpd: 'pendente',
    retencao_ate: '',
  })
  const [consentimentoForm, setConsentimentoForm] = useState({
    tipo: 'concedido',
    base_legal: 'consentimento',
    observacao: '',
  })
  const [motivoExclusaoLgpd, setMotivoExclusaoLgpd] = useState('')

  const carregarCadastro = async () => {
    const r = await api.buscar(id)
    const c = r.data
    setCadastro(c)
    setLgpdForm({
      base_legal: c.base_legal || 'consentimento',
      status_lgpd: c.status_lgpd || 'pendente',
      retencao_ate: c.retencao_ate ? String(c.retencao_ate).slice(0, 16) : '',
    })
    setConsentimentoForm((prev) => ({
      ...prev,
      base_legal: c.base_legal || prev.base_legal,
    }))
  }

  useEffect(() => {
    carregarCadastro()
  }, [id])

  const aprovar = async () => {
    setAprovando(true)
    try {
      await api.aprovar(id)
      await carregarCadastro()
    } finally {
      setAprovando(false)
    }
  }

  const uploadDoc = async (tipo, arquivo) => {
    await api.uploadDoc(id, tipo, arquivo)
    await carregarCadastro()
  }

  const salvarLgpd = async () => {
    setErroLgpd('')
    setSalvandoLgpd(true)
    try {
      await api.atualizarLgpd(id, {
        base_legal: lgpdForm.base_legal || undefined,
        status_lgpd: lgpdForm.status_lgpd || undefined,
        retencao_ate: lgpdForm.retencao_ate ? `${lgpdForm.retencao_ate}:00` : null,
      })
      await carregarCadastro()
    } catch (err) {
      setErroLgpd(err.response?.data?.detail || 'Não foi possível atualizar os dados LGPD.')
    } finally {
      setSalvandoLgpd(false)
    }
  }

  const registrarConsentimento = async () => {
    setErroLgpd('')
    setRegistrandoConsentimento(true)
    try {
      await api.registrarConsentimentoLgpd(id, consentimentoForm)
      setConsentimentoForm((prev) => ({ ...prev, observacao: '' }))
      await carregarCadastro()
    } catch (err) {
      setErroLgpd(err.response?.data?.detail || 'Não foi possível registrar o consentimento.')
    } finally {
      setRegistrandoConsentimento(false)
    }
  }

  const aplicarExclusaoLgpd = async () => {
    if (!motivoExclusaoLgpd.trim()) {
      setErroLgpd('Informe o motivo da exclusão LGPD.')
      return
    }
    setErroLgpd('')
    setExcluindoLgpd(true)
    try {
      await api.excluirLgpd(id, motivoExclusaoLgpd.trim())
      setMotivoExclusaoLgpd('')
      await carregarCadastro()
    } catch (err) {
      setErroLgpd(err.response?.data?.detail || 'Não foi possível executar a exclusão LGPD.')
    } finally {
      setExcluindoLgpd(false)
    }
  }

  const excluir = async () => {
    setExcluindo(true)
    try {
      await api.excluir(id)
      navigate('/cadastros')
    } finally {
      setExcluindo(false)
      setMostrarConfirmacaoExclusao(false)
    }
  }

  if (!cadastro) return <p style={{ color: 'var(--text-soft)', fontSize: 14 }}>Carregando...</p>

  const podeCriarOuEditarCadastro = ['coordenadora', 'assistente'].includes(usuario?.perfil)
  const podeAprovar = ['coordenadora', 'ti'].includes(usuario?.perfil)
  const podeExcluir = usuario?.perfil === 'coordenadora'
  const lgpdConcluido = Boolean(cadastro.lgpd_concluido)

  return (
    <div className="centered-form-shell">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.5rem' }}>
        <div>
          <button className="btn-back" onClick={() => navigate(-1)} style={{ marginBottom: 10 }}>
            ← Voltar
          </button>
          <h1 style={{ fontSize: 20, fontWeight: 600 }}>{cadastro.nome_social || cadastro.nome}</h1>
          <div style={{ fontSize: 13, color: 'var(--text-soft)' }}>#{String(cadastro.id).padStart(4, '0')} · CPF {cadastro.cpf}</div>
          <div style={{ marginTop: 8 }}>
            <span
              style={{
                background: lgpdConcluido ? 'var(--badge-active-bg)' : 'var(--badge-pending-bg)',
                color: lgpdConcluido ? 'var(--badge-active-text)' : 'var(--badge-pending-text)',
                padding: '4px 10px',
                borderRadius: 999,
                fontSize: 11,
                fontWeight: 700,
              }}
            >
              {lgpdConcluido ? 'LGPD: concluído' : 'LGPD: pendente'}
            </span>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            type="button"
            className="btn-secondary"
            onClick={() => navigate(`/cadastros/${id}/editar`)}
            disabled={!podeCriarOuEditarCadastro}
          >
            Editar
          </button>
          <a
            href={api.pdfUrl(id)}
            target="_blank"
            rel="noreferrer"
            className="btn-secondary"
            style={{ textDecoration: 'none', display: 'inline-flex', alignItems: 'center' }}
          >
            Baixar PDF
          </a>
          <button
            type="button"
            className="btn-secondary"
            onClick={() => setMostrarConfirmacaoExclusao(true)}
            disabled={excluindo || !podeExcluir}
            style={{ borderColor: 'var(--danger)', color: 'var(--danger)' }}
          >
            {excluindo ? 'Excluindo...' : 'Excluir'}
          </button>
          {podeAprovar && cadastro.status === 'pendente' && (
            <button
              onClick={aprovar}
              disabled={aprovando || !lgpdConcluido}
              className="btn-primary"
              title={!lgpdConcluido ? 'Anexe o termo LGPD assinado antes de aprovar' : ''}
            >
              {aprovando ? 'Aprovando...' : 'Aprovar cadastro'}
            </button>
          )}
        </div>
      </div>

      {!lgpdConcluido && (
        <div style={{ marginBottom: '1rem', border: '1px solid var(--badge-pending-text)', background: 'var(--badge-pending-bg)', color: 'var(--text-main)', padding: '10px 12px', borderRadius: 10, fontSize: 13 }}>
          Aprovação bloqueada: anexe os documentos obrigatórios e garanta consentimento LGPD ativo.
        </div>
      )}

      <ConfirmModal
        open={mostrarConfirmacaoExclusao}
        title="Excluir cadastro"
        message="Tem certeza que deseja excluir este cadastro? Essa acao nao pode ser desfeita."
        confirmLabel="Excluir"
        cancelLabel="Cancelar"
        onConfirm={excluir}
        onClose={() => setMostrarConfirmacaoExclusao(false)}
        loading={excluindo}
        danger
      />

      <div style={{ background: 'var(--surface-card)', border: '1px solid var(--border)', borderRadius: 10, padding: '1.5rem' }}>
        {secao('Dados pessoais')}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 2rem' }}>
          {campo('Nome completo', cadastro.nome)}
          {campo('Nome social', cadastro.nome_social)}
          {campo('CPF', cadastro.cpf)}
          {campo('RG / Órgão', `${cadastro.rg || ''} ${cadastro.orgao_expedidor || ''}`.trim())}
          {campo('Data de nascimento', cadastro.data_nascimento)}
          {campo('Estado civil', cadastro.estado_civil)}
          {campo('Identidade de gênero', cadastro.identidade_genero)}
          {campo('Cor/raça', cadastro.cor_raca)}
          {campo('PCD', cadastro.pcd ? 'Sim' : 'Não')}
          {campo('Renda média', cadastro.renda_media)}
        </div>

        {secao('Contato e endereço')}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 2rem' }}>
          {campo('E-mail', cadastro.email)}
          {campo('Telefone', cadastro.telefone)}
          {campo('Endereço', cadastro.endereco)}
          {campo('Cidade/UF', `${cadastro.cidade || ''}/${cadastro.uf || ''}`)}
        </div>

        {secao('Encaminhamento')}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 2rem' }}>
          {campo('Com encaminhamento', cadastro.com_encaminhamento ? 'Sim' : 'Não')}
          {campo('Encaminhamento realizado', cadastro.encaminhamento_realizado ? 'Sim' : 'Não')}
        </div>

        {secao('Documentos')}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          {[
            { tipo: 'foto', label: 'Foto', url: cadastro.foto_url, dica: 'Arquivo de identificação visual do cadastro.', acao: 'Enviar foto' },
            { tipo: 'comprovante', label: 'Comprovante de residência', url: cadastro.comprovante_residencia_url, dica: 'Anexe PDF/JPG do comprovante atualizado.', acao: 'Enviar comprovante' },
            { tipo: 'documento', label: 'Documento pessoal', url: cadastro.documento_pessoal_url, dica: 'RG, CNH ou outro documento oficial com foto.', acao: 'Enviar documento' },
            { tipo: 'termo_imagem', label: 'Termo de imagem', url: cadastro.termo_imagem_url, dica: 'Termo assinado autorizando uso de imagem.', acao: 'Anexar termo' },
            { tipo: 'termo_lgpd', label: 'Termo LGPD (assinado)', url: cadastro.termo_lgpd_url, dica: 'Anexe o termo de consentimento LGPD assinado (PDF/JPG).', acao: 'Anexar termo LGPD' },
          ].map(({ tipo, label, url, dica, acao }) => (
            <div key={tipo} style={{ border: '1px solid var(--border)', borderRadius: 8, padding: '10px 12px' }}>
              <div style={{ fontSize: 12, color: 'var(--text-soft)', marginBottom: 6 }}>{label}</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 8 }}>{dica}</div>
              {url
                ? <a href={urlArquivo(url)} target="_blank" rel="noreferrer" style={{ fontSize: 13, color: 'var(--link)', fontWeight: 700 }}>Ver arquivo</a>
                : podeCriarOuEditarCadastro ? <label style={{ fontSize: 13, color: 'var(--link)', cursor: 'pointer', fontWeight: 700 }}>
                    {acao}
                    <input type="file" style={{ display: 'none' }} onChange={(e) => uploadDoc(tipo, e.target.files[0])} />
                  </label> : <span style={{ fontSize: 12, color: 'var(--text-soft)' }}>Sem permissão para upload</span>
              }
            </div>
          ))}
        </div>

        {secao('LGPD operacional')}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 }}>
          <div>
            <label className="form-label">Base legal</label>
            <select
              className="form-select"
              value={lgpdForm.base_legal}
              onChange={(e) => setLgpdForm((prev) => ({ ...prev, base_legal: e.target.value }))}
              disabled={!podeCriarOuEditarCadastro}
            >
              <option value="consentimento">consentimento</option>
              <option value="execucao_de_politica_publica">execução de política pública</option>
              <option value="obrigacao_legal">obrigação legal</option>
              <option value="protecao_da_vida">proteção da vida</option>
              <option value="legitimo_interesse">legítimo interesse</option>
            </select>
          </div>
          <div>
            <label className="form-label">Status LGPD</label>
            <select
              className="form-select"
              value={lgpdForm.status_lgpd}
              onChange={(e) => setLgpdForm((prev) => ({ ...prev, status_lgpd: e.target.value }))}
              disabled={!podeCriarOuEditarCadastro}
            >
              <option value="pendente">pendente</option>
              <option value="consentido">consentido</option>
              <option value="revogado">revogado</option>
            </select>
          </div>
          <div>
            <label className="form-label">Retenção até</label>
            <input
              className="form-input"
              type="datetime-local"
              value={lgpdForm.retencao_ate}
              onChange={(e) => setLgpdForm((prev) => ({ ...prev, retencao_ate: e.target.value }))}
              disabled={!podeCriarOuEditarCadastro}
            />
          </div>
          <div style={{ display: 'flex', alignItems: 'end' }}>
            <button className="btn-secondary" onClick={salvarLgpd} disabled={!podeCriarOuEditarCadastro || salvandoLgpd}>
              {salvandoLgpd ? 'Salvando...' : 'Salvar dados LGPD'}
            </button>
          </div>
        </div>

        <div style={{ border: '1px solid var(--border)', borderRadius: 8, padding: 12, marginBottom: 12 }}>
          <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 8 }}>Registrar consentimento</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 8 }}>
            <div>
              <label className="form-label">Tipo</label>
              <select
                className="form-select"
                value={consentimentoForm.tipo}
                onChange={(e) => setConsentimentoForm((prev) => ({ ...prev, tipo: e.target.value }))}
                disabled={!podeCriarOuEditarCadastro}
              >
                <option value="concedido">concedido</option>
                <option value="revogado">revogado</option>
              </select>
            </div>
            <div>
              <label className="form-label">Base legal</label>
              <input
                className="form-input"
                value={consentimentoForm.base_legal}
                onChange={(e) => setConsentimentoForm((prev) => ({ ...prev, base_legal: e.target.value }))}
                disabled={!podeCriarOuEditarCadastro}
              />
            </div>
          </div>
          <div>
            <label className="form-label">Observação</label>
            <textarea
              className="form-textarea"
              rows={2}
              style={{ resize: 'vertical' }}
              value={consentimentoForm.observacao}
              onChange={(e) => setConsentimentoForm((prev) => ({ ...prev, observacao: e.target.value }))}
              disabled={!podeCriarOuEditarCadastro}
            />
          </div>
          <div style={{ marginTop: 8 }}>
            <button className="btn-secondary" onClick={registrarConsentimento} disabled={!podeCriarOuEditarCadastro || registrandoConsentimento}>
              {registrandoConsentimento ? 'Registrando...' : 'Registrar consentimento'}
            </button>
          </div>
        </div>

        <div style={{ border: '1px solid var(--border)', borderRadius: 8, padding: 12, marginBottom: 12 }}>
          <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 8 }}>Histórico de consentimento</div>
          {!cadastro.consentimentos?.length ? (
            <p style={{ fontSize: 13, color: 'var(--text-soft)', margin: 0 }}>Sem registros até o momento.</p>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ background: 'var(--surface-subtle)' }}>
                    <th style={{ textAlign: 'left', padding: 8, borderBottom: '1px solid var(--border)' }}>Quando</th>
                    <th style={{ textAlign: 'left', padding: 8, borderBottom: '1px solid var(--border)' }}>Tipo</th>
                    <th style={{ textAlign: 'left', padding: 8, borderBottom: '1px solid var(--border)' }}>Base legal</th>
                    <th style={{ textAlign: 'left', padding: 8, borderBottom: '1px solid var(--border)' }}>Observação</th>
                  </tr>
                </thead>
                <tbody>
                  {cadastro.consentimentos.map((i) => (
                    <tr key={i.id} style={{ borderBottom: '1px solid var(--row-border)' }}>
                      <td style={{ padding: 8 }}>{new Date(i.criado_em).toLocaleString('pt-BR')}</td>
                      <td style={{ padding: 8 }}>{i.tipo}</td>
                      <td style={{ padding: 8 }}>{i.base_legal}</td>
                      <td style={{ padding: 8 }}>{i.observacao || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {podeExcluir && (
          <div style={{ border: '1px solid var(--danger)', borderRadius: 8, padding: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--danger)', marginBottom: 8 }}>Exclusão lógica por política LGPD</div>
            <label className="form-label">Motivo da exclusão</label>
            <textarea
              className="form-textarea"
              rows={2}
              style={{ resize: 'vertical' }}
              value={motivoExclusaoLgpd}
              onChange={(e) => setMotivoExclusaoLgpd(e.target.value)}
              placeholder="Ex.: prazo de retenção expirado e solicitação do titular"
            />
            <div style={{ marginTop: 8 }}>
              <button className="btn-secondary" style={{ borderColor: 'var(--danger)', color: 'var(--danger)' }} onClick={aplicarExclusaoLgpd} disabled={excluindoLgpd}>
                {excluindoLgpd ? 'Aplicando...' : 'Aplicar exclusão LGPD'}
              </button>
            </div>
          </div>
        )}

        {erroLgpd && <p style={{ color: 'var(--danger)', marginTop: 12, marginBottom: 0 }}>{erroLgpd}</p>}
      </div>
    </div>
  )
}
