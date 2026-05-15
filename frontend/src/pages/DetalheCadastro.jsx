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
  const [excluindoLgpd, setExcluindoLgpd] = useState(false)
  const [erroLgpd, setErroLgpd] = useState('')
  const [mostrarConfirmacaoExclusao, setMostrarConfirmacaoExclusao] = useState(false)
  const [motivoExclusaoLgpd, setMotivoExclusaoLgpd] = useState('')
  const [baixandoPdf, setBaixandoPdf] = useState(false)
  const [erroAprovar, setErroAprovar] = useState('')

  const carregarCadastro = async () => {
    const r = await api.buscar(id)
    setCadastro(r.data)
  }

  useEffect(() => {
    carregarCadastro()
  }, [id])

  const aprovar = async () => {
    setErroAprovar('')
    setAprovando(true)
    try {
      await api.aprovar(id)
      await carregarCadastro()
    } catch (err) {
      const d = err.response?.data?.detail
      setErroAprovar(typeof d === 'string' ? d : 'Não foi possível aprovar o cadastro.')
    } finally {
      setAprovando(false)
    }
  }

  const uploadDoc = async (tipo, arquivo) => {
    setErroAprovar('')
    await api.uploadDoc(id, tipo, arquivo)
    await carregarCadastro()
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

  const baixarPdf = async () => {
    setBaixandoPdf(true)
    try {
      const blob = await api.baixarPdf(id)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `cadastro_${String(id).padStart(4, '0')}.pdf`
      a.rel = 'noopener'
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      setTimeout(() => URL.revokeObjectURL(url), 60_000)
    } catch {
      alert('Não foi possível baixar o PDF do cadastro.')
    } finally {
      setBaixandoPdf(false)
    }
  }

  if (!cadastro) return <p style={{ color: 'var(--text-soft)', fontSize: 14 }}>Carregando...</p>

  const podeCriarOuEditarCadastro = ['coordenadora', 'assistente'].includes(usuario?.perfil)
  const podeAprovar = ['coordenadora', 'ti'].includes(usuario?.perfil)
  const podeExcluir = usuario?.perfil === 'coordenadora'
  const lgpdConcluido = Boolean(cadastro.lgpd_concluido)
  const prontoAprovacao = Boolean(cadastro.pronto_aprovacao)
  const pendenciasAprovacao = cadastro.pendencias_aprovacao || []

  const docsUpload = [
    { tipo: 'foto', label: 'Foto', url: cadastro.foto_url, dica: 'Arquivo de identificação visual do cadastro.', acao: 'Enviar foto' },
    { tipo: 'comprovante', label: 'Comprovante de residência', url: cadastro.comprovante_residencia_url, dica: 'Anexe PDF/JPG do comprovante atualizado.', acao: 'Enviar comprovante' },
    { tipo: 'documento', label: 'Documento pessoal', url: cadastro.documento_pessoal_url, dica: 'RG, CNH ou outro documento oficial com foto.', acao: 'Enviar documento' },
  ]

  const docsTermos = [
    { label: 'Termo LGPD (gerado no cadastro)', url: cadastro.termo_lgpd_url },
    { label: 'Termo de uso de imagem (gerado no cadastro)', url: cadastro.termo_imagem_url },
  ]

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
              {lgpdConcluido ? 'Termos: ok' : 'Termos: pendente'}
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
          <button
            type="button"
            className="btn-secondary"
            onClick={baixarPdf}
            disabled={baixandoPdf}
          >
            {baixandoPdf ? 'Gerando PDF…' : 'Baixar PDF'}
          </button>
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
              disabled={aprovando || !prontoAprovacao}
              className="btn-primary"
              title={
                !prontoAprovacao && pendenciasAprovacao.length
                  ? `Pendências: ${pendenciasAprovacao.join(', ')}`
                  : ''
              }
            >
              {aprovando ? 'Aprovando...' : 'Aprovar cadastro'}
            </button>
          )}
        </div>
      </div>

      {cadastro.status === 'pendente' && !prontoAprovacao && (
        <div style={{ marginBottom: '1rem', border: '1px solid var(--badge-pending-text)', background: 'var(--badge-pending-bg)', color: 'var(--text-main)', padding: '10px 12px', borderRadius: 10, fontSize: 13 }}>
          Aprovação bloqueada
          {pendenciasAprovacao.length > 0
            ? `: ${pendenciasAprovacao.join(', ')}.`
            : ': anexe foto, comprovante de residência, documento pessoal e confira os termos gerados no cadastro.'}
        </div>
      )}

      {erroAprovar && (
        <p style={{ color: 'var(--danger)', marginBottom: '1rem', fontSize: 13 }}>{erroAprovar}</p>
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
          {docsUpload.map(({ tipo, label, url, dica, acao }) => (
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

        {secao('Termos assinados (PDF)')}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          {docsTermos.map(({ label, url }) => (
            <div key={label} style={{ border: '1px solid var(--border)', borderRadius: 8, padding: '10px 12px' }}>
              <div style={{ fontSize: 12, color: 'var(--text-soft)', marginBottom: 6 }}>{label}</div>
              {url
                ? <a href={urlArquivo(url)} target="_blank" rel="noreferrer" style={{ fontSize: 13, color: 'var(--link)', fontWeight: 700 }}>Baixar PDF</a>
                : <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Indisponível (cadastro antigo ou erro na geração).</span>
              }
            </div>
          ))}
        </div>

        {podeExcluir && (
          <div style={{ marginTop: '1.5rem', border: '1px solid var(--danger)', borderRadius: 8, padding: 12 }}>
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
