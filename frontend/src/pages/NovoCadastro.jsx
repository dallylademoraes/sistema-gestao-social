import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { cadastros as api } from '../services/api'
import { useAuth } from '../hooks/useAuth'

const Input = ({ label, required, children, ...props }) => (
  <div style={{ marginBottom: 12 }}>
    <label className="form-label">
      {label} {required && <span style={{ color: '#c0392b' }}>*</span>}
    </label>
    {children || <input required={required} className="form-input" {...props} />}
  </div>
)

const Select = ({ label, required, options, ...props }) => (
  <div style={{ marginBottom: 12 }}>
    <label className="form-label">
      {label} {required && <span style={{ color: '#c0392b' }}>*</span>}
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

export default function NovoCadastro() {
  const navigate = useNavigate()
  const { usuario } = useAuth()
  const [erro, setErro] = useState('')
  const [salvando, setSalvando] = useState(false)
  const podeCriarOuEditarCadastro = ['coordenadora', 'assistente'].includes(usuario?.perfil)

  if (!podeCriarOuEditarCadastro) {
    return (
      <div className="centered-form-shell">
        <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 8 }}>Sem permissão</h1>
        <p style={{ color: 'var(--text-muted)', marginBottom: 16 }}>Seu perfil pode visualizar e aprovar, mas não pode criar cadastros.</p>
        <button className="btn-secondary" onClick={() => navigate('/cadastros')}>Voltar para cadastros</button>
      </div>
    )
  }

  const mascaraCPF = (v) => v.replace(/\D/g, '').slice(0, 11)
    .replace(/(\d{3})(\d)/, '$1.$2')
    .replace(/(\d{3})(\d)/, '$1.$2')
    .replace(/(\d{3})(\d{1,2})$/, '$1-$2')

  const handleSubmit = async (e) => {
    e.preventDefault()
    setErro('')
    setSalvando(true)
    const f = e.target
    const dados = {
      nome: f.nome.value,
      nome_social: f.nome_social.value || null,
      cpf: f.cpf.value,
      rg: f.rg.value || null,
      orgao_expedidor: f.orgao_expedidor.value || null,
      data_nascimento: f.data_nascimento.value,
      email: f.email.value || null,
      telefone: f.telefone.value,
      endereco: f.endereco.value || null,
      cidade: f.cidade.value || null,
      uf: f.uf.value || null,
      estado_civil: f.estado_civil.value || null,
      cor_raca: f.cor_raca.value || null,
      identidade_genero: f.identidade_genero.value || null,
      pcd: f.pcd.value === 'Sim',
      renda_media: f.renda_media.value || null,
      com_encaminhamento: f.com_encaminhamento.value === 'Sim',
      encaminhamento_realizado: f.encaminhamento_realizado.value === 'Sim',
      observacoes: f.observacoes.value || null,
    }
    try {
      const r = await api.criar(dados)
      navigate(`/cadastros/${r.data.id}`)
    } catch (err) {
      setErro(err.response?.data?.detail || 'Erro ao salvar. Verifique os campos.')
    } finally {
      setSalvando(false)
    }
  }

  return (
    <div className="centered-form-shell">
      <button className="btn-back" onClick={() => navigate(-1)} style={{ marginBottom: 12 }}>← Voltar</button>
      <h1 style={{ fontSize: 25, fontWeight: 700, marginBottom: '1.5rem' }}>Novo cadastro</h1>

      <form onSubmit={handleSubmit}>
        <div className="centered-form-card">

          <Secao titulo="Dados pessoais" />
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 1.5rem' }}>
            <div style={{ gridColumn: '1 / -1' }}><Input label="Nome completo" name="nome" required /></div>
            <Input label="Nome social" name="nome_social" />
            <Input label="CPF" name="cpf" required placeholder="000.000.000-00" maxLength={14}
              onChange={(e) => e.target.value = mascaraCPF(e.target.value)} />
            <Input label="RG" name="rg" />
            <Input label="Órgão expedidor" name="orgao_expedidor" placeholder="SSP/TO" />
            <Input label="Data de nascimento" name="data_nascimento" type="date" required />
            <Select label="Estado civil" name="estado_civil" options={['Solteiro/a', 'Casado/a', 'União estável', 'Divorciado/a', 'Viúvo/a']} />
            <Select label="Identidade de gênero" name="identidade_genero" options={['Mulher cisgênero', 'Homem cisgênero', 'Mulher transgênero', 'Homem transgênero', 'Não-binário', 'Prefiro não informar']} />
            <Select label="Cor/raça" name="cor_raca" options={['Branca', 'Preta', 'Parda', 'Amarela', 'Indígena', 'Prefiro não informar']} />
            <Select label="PCD" name="pcd" options={['Não', 'Sim']} />
            <Select label="Renda média" name="renda_media" options={['Sem renda', 'Até 1 salário mínimo', '1 a 2 salários', '2 a 3 salários', 'Acima de 3 salários']} />
          </div>

          <Secao titulo="Contato e endereço" />
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 1.5rem' }}>
            <Input label="E-mail" name="email" type="email" />
            <Input label="Telefone" name="telefone" required placeholder="(63) 90000-0000" />
            <div style={{ gridColumn: '1 / -1' }}><Input label="Endereço" name="endereco" placeholder="Rua, número, bairro" /></div>
            <Input label="Cidade" name="cidade" />
            <Input label="UF" name="uf" maxLength={2} placeholder="TO" />
          </div>

          <Secao titulo="Encaminhamento" />
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 1.5rem' }}>
            <Select label="Com encaminhamento" name="com_encaminhamento" options={['Não', 'Sim']} />
            <Select label="Encaminhamento realizado" name="encaminhamento_realizado" options={['Não', 'Sim']} />
          </div>

          <Secao titulo="Observações" />
          <div style={{ marginBottom: 12 }}>
            <label className="form-label">Observações</label>
            <textarea name="observacoes" rows={3} className="form-textarea" style={{ resize: 'vertical' }} />
          </div>
        </div>

        {erro && <p style={{ color: 'var(--danger)', fontSize: 13, margin: '12px 0' }}>{erro}</p>}

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: '1rem' }}>
          <button type="button" className="btn-secondary" onClick={() => navigate(-1)}>
            Cancelar
          </button>
          <button type="submit" disabled={salvando} className="btn-primary">
            {salvando ? 'Salvando...' : 'Salvar cadastro'}
          </button>
        </div>
      </form>
    </div>
  )
}
