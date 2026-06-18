import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../services/api'

const FaqItem = ({ pergunta, children }) => {
  const [aberto, setAberto] = useState(false)
  
  return (
    <div style={{ borderBottom: '1px solid var(--border)', padding: '14px 0' }}>
      <button
        type="button"
        onClick={() => setAberto(!aberto)}
        style={{
          width: '100%', display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          background: 'none', border: 'none', padding: 0, cursor: 'pointer', textAlign: 'left',
          fontSize: 15, fontWeight: 600, color: 'var(--text-main)'
        }}
      >
        {pergunta}
        <span style={{ fontSize: 20, color: 'var(--text-soft)', transition: 'transform 0.2s', transform: aberto ? 'rotate(45deg)' : 'none' }}>
          +
        </span>
      </button>
      {aberto && (
        <div style={{ marginTop: 12, fontSize: 14, color: 'var(--text-muted)', lineHeight: 1.6 }}>
          {children}
        </div>
      )}
    </div>
  )
}

export default function FAQ() {
  const navigate = useNavigate()
  
  const [perfilUsuario, setPerfilUsuario] = useState('')

  useEffect(() => {
    // Busca os dados do usuário logado na API para liberar a documentação
    api.get('/auth/me')
      .then((response) => {
        setPerfilUsuario(response.data.perfil || '')
      })
      .catch((error) => console.error("Erro ao buscar perfil do usuário", error))
  }, [])

  return (
    <div className="centered-form-shell" style={{ maxWidth: 800, margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, margin: 0 }}>Ajuda e Tutoriais</h1>
        <button className="btn-secondary" onClick={() => navigate(-1)}>Voltar</button>
      </div>

      {/* Seção do Vídeo Tutorial */}
      <div style={{ background: 'var(--surface-card)', border: '1px solid var(--border)', borderRadius: 10, padding: '1.5rem', marginBottom: '1.5rem' }}>
        <h2 style={{ fontSize: 18, fontWeight: 600, marginTop: 0, marginBottom: 8 }}>Vídeo Tutorial do Sistema</h2>
        <p style={{ color: 'var(--text-muted)', fontSize: 14, marginBottom: 16 }}>
          Assista ao nosso vídeo de treinamento para aprender a usar o sistema completo, desde a criação de cadastros até a exportação de relatórios.
        </p>
        <a 
        href="https://drive.google.com/file/d/1cNAlGMv04ntFFxDs2rPxi9fOanMfiSsH/view?usp=sharing" 
          target="_blank" 
          rel="noreferrer" 
          className="btn-primary" 
          style={{ display: 'inline-flex', textDecoration: 'none' }}
        >
          Assistir Tutorial no Drive
        </a>
      </div>

      {/* Seção da Documentação Técnica (Restrito para TI) */}
      {perfilUsuario.toLowerCase() === 'ti' && (
        <div style={{ background: 'var(--surface-card)', border: '1px solid var(--border)', borderRadius: 10, padding: '1.5rem', marginBottom: '1.5rem' }}>
          <h2 style={{ fontSize: 18, fontWeight: 600, marginTop: 0, marginBottom: 8 }}>Documentação Técnica (Acesso Restrito)</h2>
          <p style={{ color: 'var(--text-muted)', fontSize: 14, marginBottom: 16 }}>
            Visão exclusiva para o perfil de TI. Contém informações detalhadas sobre a infraestrutura (Render, Neon.tech), variáveis de ambiente e arquitetura do sistema.
          </p>
          <a 
            href="https://drive.google.com/file/d/1prDcROxPmgjtVRW_bsV3xWvfcbFcAlvg/view?usp=sharing" 
            target="_blank" 
            rel="noreferrer" 
            className="btn-primary" 
            style={{ display: 'inline-flex', textDecoration: 'none', backgroundColor: '#3b82f6', borderColor: '#3b82f6' }}
          >
            Acessar Documentação Técnica
          </a>
        </div>
      )}

      {/* Seção de Perguntas Frequentes */}
      <div style={{ background: 'var(--surface-card)', border: '1px solid var(--border)', borderRadius: 10, padding: '1.5rem' }}>
        <h2 style={{ fontSize: 18, fontWeight: 600, marginTop: 0, marginBottom: '1rem' }}>Perguntas Frequentes (FAQ)</h2>

        <FaqItem pergunta="1. Quais são os perfis de acesso e o que cada um pode fazer?">
          <ul style={{ paddingLeft: '1.5rem', margin: 0 }}>
            <li style={{ marginBottom: 6 }}><strong>Coordenadora:</strong> Gerencia tudo. É a única que pode criar usuários, excluir cadastros permanentemente, aprovar cadastros pendentes e visualizar as auditorias.</li>
            <li style={{ marginBottom: 6 }}><strong>Assistente:</strong> Pode criar e editar cadastros, fazer upload de documentos e coletar assinaturas. Não possui poder de aprovação ou exclusão.</li>
            <li><strong>TI:</strong> Tem acesso apenas de leitura (visualização) aos cadastros e dados do painel. Não pode criar, editar, assinar nem apagar nenhum registro.</li>
          </ul>
        </FaqItem>

        <FaqItem pergunta="2. Como funciona a coleta de assinaturas?">
          <p style={{ margin: 0 }}>Você tem duas formas de coletar a assinatura dos Termos (LGPD e Uso de Imagem):</p>
          <ul style={{ paddingLeft: '1.5rem', marginTop: 8, marginBottom: 0 }}>
            <li style={{ marginBottom: 6 }}><strong>No próprio computador:</strong> Se a pessoa estiver do seu lado, ela pode assinar direto na tela de <em>Novo Cadastro</em> usando o mouse ou um monitor touch.</li>
            <li><strong>No tablet:</strong> Clique no botão "Salvar para assinar no tablet". Depois, abra o tablet, vá na tela <em>Assinaturas Pendentes</em>, selecione o nome da pessoa e colete a assinatura lá. O sistema vinculará ao cadastro automaticamente.</li>
          </ul>
        </FaqItem>

        <FaqItem pergunta="3. O que impede um cadastro de ser aprovado?">
          <p style={{ margin: 0, marginBottom: 8 }}>Para que a Coordenadora consiga aprovar um cadastro, o sistema exige que os dados críticos estejam preenchidos. Ele será bloqueado se:</p>
          <ul style={{ paddingLeft: '1.5rem', margin: 0 }}>
            <li>Os Termos LGPD e Uso de Imagem não estiverem assinados.</li>
            <li>O CPF for inválido ou já estiver em uso em outro cadastro.</li>
            <li>Faltarem o nome, telefone ou data de nascimento.</li>
            <li>A idade registrada for menor de 16 anos.</li>
          </ul>
          <p style={{ margin: '8px 0 0' }}><em>Nota:</em> A falta de Foto, RG ou Comprovante de Residência gera apenas um <strong>alerta</strong>, mas a aprovação é permitida mesmo assim.</p>
        </FaqItem>

        <FaqItem pergunta="4. Qual a diferença entre Excluir permanentemente e a Exclusão LGPD?">
          <p style={{ margin: 0, marginBottom: 8 }}>Apenas a <strong>Coordenadora</strong> tem acesso a essas duas opções:</p>
          <ul style={{ paddingLeft: '1.5rem', margin: 0 }}>
            <li style={{ marginBottom: 6 }}><strong>Exclusão permanente:</strong> Remove completamente a ficha da pessoa do banco de dados do sistema, como se nunca tivesse existido.</li>
            <li><strong>Exclusão lógica por política LGPD:</strong> É usada quando o prazo legal acabou e a pessoa solicita a exclusão. Ela não apaga a linha do banco, mas sobrescreve os dados sensíveis (Nome vira "DADO EXCLUIDO", CPF etc. são apagados) e inativa o cadastro. Isso serve para a ASAP manter estatísticas anônimas, sem reter o dado pessoal.</li>
          </ul>
        </FaqItem>

        <FaqItem pergunta="5. Esqueci minha senha, como eu recupero?">
          <p style={{ margin: 0 }}>Como o sistema tem acesso restrito, não há redefinição automática de senha por e-mail para usuários assistentes. Se você esqueceu sua senha, você deve <strong>falar com a Coordenadora</strong>. Ela pode acessar a tela de <em>Usuários</em> e digitar uma nova senha provisória na sua linha para você voltar a entrar.</p>
        </FaqItem>

        <FaqItem pergunta="6. Como eu extraio as informações para planilhas?">
          <p style={{ margin: 0 }}>
            Você pode extrair dados em dois lugares: <br />
            1) Na aba <strong>Cadastros</strong>, faça uma busca ou aplique filtros (como "só inativos") e clique em "Exportar Excel". O sistema vai gerar uma planilha apenas com o que você filtrou. <br />
            2) Na aba <strong>Painel</strong>, você encontra botões no topo para "Exportar Resumo de Gráficos" (que gera uma aba de Excel para criar Dashboards). Também é possível baixar os gráficos individualmente clicando no botão "PNG" acima de cada gráfico.
          </p>
        </FaqItem>
      </div>
    </div>
  )
}