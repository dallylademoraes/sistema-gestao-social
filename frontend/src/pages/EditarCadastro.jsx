import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { cadastros as api } from '../services/api'
import { useAuth } from '../hooks/useAuth'

const Input = ({ label, required, children, ...props }) => (
  <div style={{ marginBottom: 12 }}>
    <label className="form-label">
      {label} {required && <span style={{ color: 'var(--danger)' }}>*</span>}
    </label>
    {children || <input required={required} className="form-input" {...props} />}
  </div>
)

const Select = ({ label, required, options, ...props }) => (
  <div style={{ marginBottom: 12 }}>
    <label className="form-label">
      {label} {required && <span style={{ color: 'var(--danger)' }}>*</span>}
    </label>
    <select required={required} className="form-select" {...props}>
      <option value="">Selecione...</option>
      {options.map((o) => <option key={o} value={o}>{o}</option>)}
    </select>
  </div>
)

const Secao = ({ titulo }) => (
  <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-soft)', textTransform: 'uppercase', letterSpacing: '0.5px', margin: '1.5rem 0 1rem', paddingBottom: 6, borderBottom: '1px solid var(--border)' }}>
    {titulo}
  </div>
)

const toInputDate = (value) => {
  if (!value) return ''
  return String(value).slice(0, 10)
}

export default function EditarCadastro() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { usuario } = useAuth()
  const [erro, setErro] = useState('')
  const [salvando, setSalvando] = useState(false)
  const [carregando, setCarregando] = useState(true)
  const [form, setForm] = useState(null)
  const podeCriarOuEditarCadastro = ['coordenadora', 'assistente'].includes(usuario?.perfil)

  if (!podeCriarOuEditarCadastro) {
    return (
      <div className="centered-form-shell">
        <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 8 }}>Sem permissão</h1>
        <p style={{ color: 'var(--text-muted)', marginBottom: 16 }}>Seu perfil pode visualizar e aprovar, mas não pode editar cadastros.</p>
        <button className="btn-secondary" onClick={() => navigate(`/cadastros/${id}`)}>Voltar para detalhe</button>
      </div>
    )
  }

  const carregarCadastro = async () => {
    const r = await api.buscar(id)
    const c = r.data
    setForm({
      nome: c.nome || '',
      nome_social: c.nome_social || '',
      cpf: c.cpf || '',
      rg: c.rg || '',
      orgao_expedidor: c.orgao_expedidor || '',
      data_nascimento: toInputDate(c.data_nascimento),
      email: c.email || '',
      telefone: c.telefone || '',
      endereco: c.endereco || '',
      cidade: c.cidade || '',
      uf: c.uf || '',
      estado_civil: c.estado_civil || '',
      cor_raca: c.cor_raca || '',
      identidade_genero: c.identidade_genero || '',
      pcd: c.pcd ? 'Sim' : 'Não',
      renda_media: c.renda_media || '',
      com_encaminhamento: c.com_encaminhamento ? 'Sim' : 'Não',
      encaminhamento_realizado: c.encaminhamento_realizado ? 'Sim' : 'Não',
      observacoes: c.observacoes || '',
    })
  }

  useEffect(() => {
    carregarCadastro()
      .catch(() => setErro('Não foi possível carregar o cadastro.'))
      .finally(() => setCarregando(false))
  }, [id])

  const update = (field) => (e) => {
    const value = e.target.value
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  const mascaraCPF = (v) => v.replace(/\D/g, '').slice(0, 11)
    .replace(/(\d{3})(\d)/, '$1.$2')
    .replace(/(\d{3})(\d)/, '$1.$2')
    .replace(/(\d{3})(\d{1,2})$/, '$1-$2')

  const handleSubmit = async (e) => {
    e.preventDefault()
    setErro('')
    setSalvando(true)

    const dados = {
      nome: form.nome,
      nome_social: form.nome_social || null,
      cpf: form.cpf,
      rg: form.rg || null,
      orgao_expedidor: form.orgao_expedidor || null,
      data_nascimento: form.data_nascimento,
      email: form.email || null,
      telefone: form.telefone,
      endereco: form.endereco || null,
      cidade: form.cidade || null,
      uf: form.uf || null,
      estado_civil: form.estado_civil || null,
      cor_raca: form.cor_raca || null,
      identidade_genero: form.identidade_genero || null,
      pcd: form.pcd === 'Sim',
      renda_media: form.renda_media || null,
      com_encaminhamento: form.com_encaminhamento === 'Sim',
      encaminhamento_realizado: form.encaminhamento_realizado === 'Sim',
      observacoes: form.observacoes || null,
    }

    try {
      await api.atualizar(id, dados)
      navigate(`/cadastros/${id}`)
    } catch (err) {
      setErro(err.response?.data?.detail || 'Erro ao atualizar cadastro.')
    } finally {
      setSalvando(false)
    }
  }

  if (carregando) return <p style={{ color: 'var(--text-soft)', fontSize: 14 }}>Carregando...</p>
  if (!form) return <p style={{ color: 'var(--danger)', fontSize: 14 }}>{erro || 'Erro ao abrir tela de edição.'}</p>

  return (
    <div className="centered-form-shell">
      <button className="btn-back" onClick={() => navigate(-1)} style={{ marginBottom: 12 }}>← Voltar</button>
      <h1 style={{ fontSize: 25, fontWeight: 700, marginBottom: '1.5rem' }}>Editar cadastro</h1>

      <form onSubmit={handleSubmit}>
        <div className="centered-form-card">
          <Secao titulo="Dados pessoais" />
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 1.5rem' }}>
            <div style={{ gridColumn: '1 / -1' }}><Input label="Nome completo" name="nome" required value={form.nome} onChange={update('nome')} /></div>
            <Input label="Nome social" name="nome_social" value={form.nome_social} onChange={update('nome_social')} />
            <Input label="CPF" name="cpf" required placeholder="000.000.000-00" maxLength={14} value={form.cpf}
              onChange={(e) => setForm((prev) => ({ ...prev, cpf: mascaraCPF(e.target.value) }))} />
            <Input label="RG" name="rg" value={form.rg} onChange={update('rg')} />
            <Input label="Órgão expedidor" name="orgao_expedidor" placeholder="SSP/TO" value={form.orgao_expedidor} onChange={update('orgao_expedidor')} />
            <Input label="Data de nascimento" name="data_nascimento" type="date" required value={form.data_nascimento} onChange={update('data_nascimento')} />
            <Select label="Estado civil" name="estado_civil" options={['Solteiro/a', 'Casado/a', 'União estável', 'Divorciado/a', 'Viúvo/a']} value={form.estado_civil} onChange={update('estado_civil')} />
            <Select label="Identidade de gênero" name="identidade_genero" options={['Mulher cisgênero', 'Homem cisgênero', 'Mulher transgênero', 'Homem transgênero', 'Não-binário', 'Prefiro não informar']} value={form.identidade_genero} onChange={update('identidade_genero')} />
            <Select label="Cor/raça" name="cor_raca" options={['Branca', 'Preta', 'Parda', 'Amarela', 'Indígena', 'Prefiro não informar']} value={form.cor_raca} onChange={update('cor_raca')} />
            <Select label="PCD" name="pcd" options={['Não', 'Sim']} value={form.pcd} onChange={update('pcd')} />
            <Select label="Renda média" name="renda_media" options={['Sem renda', 'Até 1 salário mínimo', '1 a 2 salários', '2 a 3 salários', 'Acima de 3 salários']} value={form.renda_media} onChange={update('renda_media')} />
          </div>

          <Secao titulo="Contato e endereço" />
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 1.5rem' }}>
            <Input label="E-mail" name="email" type="email" value={form.email} onChange={update('email')} pattern="[^\s@]+@[^\s@]+\.[^\s@]+" title="Insira um e-mail válido (ex: nome@dominio.com)" />
            <Input label="Telefone" name="telefone" required placeholder="(63) 90000-0000" value={form.telefone} onChange={update('telefone')} />
            <div style={{ gridColumn: '1 / -1' }}><Input label="Endereço" name="endereco" placeholder="Rua, número, bairro" value={form.endereco} onChange={update('endereco')} /></div>
            <Input label="Cidade" name="cidade" value={form.cidade} onChange={update('cidade')} />
            <Input label="UF" name="uf" maxLength={2} placeholder="TO" value={form.uf} onChange={update('uf')} />
          </div>

          <Secao titulo="Encaminhamento" />
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 1.5rem' }}>
            <Select label="Com encaminhamento" name="com_encaminhamento" options={['Não', 'Sim']} value={form.com_encaminhamento} onChange={update('com_encaminhamento')} />
            <Select label="Encaminhamento realizado" name="encaminhamento_realizado" options={['Não', 'Sim']} value={form.encaminhamento_realizado} onChange={update('encaminhamento_realizado')} />
          </div>

          <Secao titulo="Observações" />
          <div style={{ marginBottom: 12 }}>
            <label className="form-label">Observações</label>
            <textarea name="observacoes" rows={3} className="form-textarea" style={{ resize: 'vertical' }} value={form.observacoes} onChange={update('observacoes')} />
          </div>

          <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: 0 }}>
            Os PDFs dos termos (LGPD e uso de imagem) foram gerados na criação do cadastro. Para alterá-los, é necessário um novo cadastro ou fluxo definido pela coordenação.
          </p>
        </div>

        {erro && <p style={{ color: 'var(--danger)', fontSize: 13, margin: '12px 0' }}>{erro}</p>}

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: '1rem' }}>
          <button type="button" className="btn-secondary" onClick={() => navigate(-1)}>
            Cancelar
          </button>
          <button type="submit" disabled={salvando} className="btn-primary">
            {salvando ? 'Salvando...' : 'Salvar alterações'}
          </button>
        </div>
      </form>
    </div>
  )
}
