import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import SignatureCanvas from 'react-signature-canvas'
import { useAuth } from '../hooks/useAuth'
import { cadastros as api } from '../services/api'

function formatarErroApi(err) {
  const d = err.response?.data?.detail
  if (Array.isArray(d)) {
    return d.map((x) => x.msg || JSON.stringify(x)).join(' ')
  }
  return d || 'Não foi possível concluir a assinatura.'
}

export default function AssinarCadastro() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { usuario } = useAuth()
  const sigRef = useRef(null)
  const containerRef = useRef(null)
  const [cadastro, setCadastro] = useState(null)
  const [aceiteLgpd, setAceiteLgpd] = useState(false)
  const [aceiteImagem, setAceiteImagem] = useState(false)
  const [salvando, setSalvando] = useState(false)
  const [erro, setErro] = useState('')
  const podeAssinar = ['coordenadora', 'assistente'].includes(usuario?.perfil)

  useEffect(() => {
    api.buscar(id).then((r) => setCadastro(r.data))
  }, [id])

  // Recalcula o tamanho interno do canvas para alinhar com o tamanho da tela (evita corte do ponteiro)
  useEffect(() => {
    const resizeCanvas = () => {
      if (sigRef.current && containerRef.current) {
        const canvas = sigRef.current.getCanvas()
        const ratio = Math.max(window.devicePixelRatio || 1, 1)
        const w = containerRef.current.offsetWidth
        const h = containerRef.current.offsetHeight
        if (canvas.width !== w * ratio || canvas.height !== h * ratio) {
          const data = sigRef.current.toData() // Salva o rabisco atual
          canvas.width = w * ratio
          canvas.height = h * ratio
          canvas.getContext('2d').scale(ratio, ratio)
          sigRef.current.clear()
          sigRef.current.fromData(data) // Restaura o rabisco
        }
      }
    }
    if (cadastro && !cadastro.lgpd_concluido) {
      setTimeout(resizeCanvas, 50)
      window.addEventListener('resize', resizeCanvas)
      return () => window.removeEventListener('resize', resizeCanvas)
    }
  }, [cadastro])

  const assinar = async (e) => {
    e.preventDefault()
    setErro('')
    if (!aceiteLgpd || !aceiteImagem) {
      setErro('Marque os dois termos para continuar.')
      return
    }
    if (!sigRef.current || sigRef.current.isEmpty()) {
      setErro('Assine no quadro antes de concluir.')
      return
    }
    setSalvando(true)
    try {
      await api.assinar(id, {
        aceite_termo_lgpd: true,
        aceite_termo_imagem: true,
        assinatura_base64: sigRef.current.toDataURL('image/png'),
      })
      navigate(`/cadastros/${id}`)
    } catch (err) {
      setErro(formatarErroApi(err))
    } finally {
      setSalvando(false)
    }
  }

  if (!podeAssinar) {
    return (
      <div className="centered-form-shell">
        <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 8 }}>Sem permissão</h1>
        <p style={{ color: 'var(--text-muted)' }}>Seu perfil não pode coletar assinaturas.</p>
      </div>
    )
  }

  if (!cadastro) return <p style={{ color: 'var(--text-soft)', fontSize: 14 }}>Carregando...</p>

  if (cadastro.lgpd_concluido) {
    return (
      <div className="centered-form-shell">
        <button className="btn-back" onClick={() => navigate('/assinaturas-pendentes')} style={{ marginBottom: 12 }}>← Pendentes</button>
        <div style={{ background: 'var(--surface-card)', border: '1px solid var(--border)', borderRadius: 10, padding: '1.5rem' }}>
          <h1 style={{ fontSize: 24, fontWeight: 700, marginTop: 0 }}>Assinatura concluída</h1>
          <p style={{ color: 'var(--text-muted)' }}>{cadastro.nome_social || cadastro.nome} já possui os termos assinados.</p>
          <button type="button" className="btn-primary" onClick={() => navigate(`/cadastros/${id}`)}>Ver cadastro</button>
        </div>
      </div>
    )
  }

  return (
    <div className="centered-form-shell">
      <button className="btn-back" onClick={() => navigate('/assinaturas-pendentes')} style={{ marginBottom: 12 }}>← Pendentes</button>
      <form onSubmit={assinar} style={{ background: 'var(--surface-card)', border: '1px solid var(--border)', borderRadius: 10, padding: '1.5rem' }}>
        <div style={{ marginBottom: '1.25rem' }}>
          <h1 style={{ fontSize: 26, fontWeight: 700, margin: 0 }}>{cadastro.nome_social || cadastro.nome}</h1>
          <div style={{ color: 'var(--text-muted)', fontSize: 14, marginTop: 5 }}>CPF {cadastro.cpf} · cadastro #{String(cadastro.id).padStart(4, '0')}</div>
        </div>

        <label style={{ display: 'flex', alignItems: 'flex-start', gap: 10, marginBottom: 12, fontSize: 16, cursor: 'pointer' }}>
          <input type="checkbox" checked={aceiteLgpd} onChange={(e) => setAceiteLgpd(e.target.checked)} style={{ marginTop: 5, width: 18, height: 18 }} />
          <span>Li e aceito o <strong>Termo LGPD</strong> da ASAP.</span>
        </label>
        <label style={{ display: 'flex', alignItems: 'flex-start', gap: 10, marginBottom: 18, fontSize: 16, cursor: 'pointer' }}>
          <input type="checkbox" checked={aceiteImagem} onChange={(e) => setAceiteImagem(e.target.checked)} style={{ marginTop: 5, width: 18, height: 18 }} />
          <span>Li e aceito o <strong>Termo de uso de imagem</strong> da ASAP.</span>
        </label>

        <div style={{ marginBottom: 8 }}>
          <span className="form-label" style={{ fontSize: 14 }}>Assinatura do titular <span style={{ color: '#c0392b' }}>*</span></span>
          <div ref={containerRef} style={{ border: '1px solid var(--border)', borderRadius: 8, background: '#fff', touchAction: 'none', height: 260, width: '100%' }}>
            <SignatureCanvas
              ref={sigRef}
              penColor="#111"
              canvasProps={{ style: { width: '100%', height: '100%', display: 'block' } }}
            />
          </div>
          <button type="button" className="btn-secondary" style={{ marginTop: 10 }} onClick={() => sigRef.current?.clear()}>
            Limpar assinatura
          </button>
        </div>

        {erro && <p style={{ color: 'var(--danger)', fontSize: 13, margin: '12px 0' }}>{erro}</p>}

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: '1rem' }}>
          <button type="button" className="btn-secondary" onClick={() => navigate('/assinaturas-pendentes')}>
            Cancelar
          </button>
          <button type="submit" disabled={salvando} className="btn-primary">
            {salvando ? 'Salvando...' : 'Concluir assinatura'}
          </button>
        </div>
      </form>
    </div>
  )
}
