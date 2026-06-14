import { Component } from 'react'

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { erro: null }
  }

  static getDerivedStateFromError(erro) {
    return { erro }
  }

  componentDidCatch(erro, info) {
    console.error('Erro ao renderizar a aplicação', erro, info)
  }

  render() {
    if (this.state.erro) {
      return (
        <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', background: 'var(--surface-page)', padding: 24 }}>
          <div style={{ width: 'min(520px, 100%)', background: 'var(--surface-card)', border: '1px solid var(--border)', borderRadius: 10, padding: 24 }}>
            <h1 style={{ margin: 0, fontSize: 20 }}>Não foi possível abrir esta tela</h1>
            <p style={{ color: 'var(--text-soft)', fontSize: 14, lineHeight: 1.5 }}>
              Atualize a página. Se continuar acontecendo, confira o Console do navegador e envie a primeira mensagem de erro.
            </p>
            <button type="button" className="btn-primary" onClick={() => window.location.reload()}>
              Atualizar
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
