import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AuthProvider } from './hooks/useAuth'
import { ThemeProvider } from './hooks/useTheme'
import ErrorBoundary from './components/ErrorBoundary'
import Layout from './components/Layout'
import Login from './pages/Login'
import Painel from './pages/Painel'
import ListaCadastros from './pages/ListaCadastros'
import DetalheCadastro from './pages/DetalheCadastro'
import NovoCadastro from './pages/NovoCadastro'
import EditarCadastro from './pages/EditarCadastro'
import AssinaturasPendentes from './pages/AssinaturasPendentes'
import AssinarCadastro from './pages/AssinarCadastro'
import Usuarios from './pages/Usuarios'
import EsqueciSenha from './pages/EsqueciSenha'
import RedefinirSenha from './pages/RedefinirSenha'
import TrocarSenha from './pages/TrocarSenha'
import FAQ from './pages/FAQ'

export default function App() {
  return (
    <ErrorBoundary>
      <ThemeProvider>
        <AuthProvider>
          <BrowserRouter>
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route path="/esqueci-senha" element={<EsqueciSenha />} />
              <Route path="/redefinir-senha" element={<RedefinirSenha />} />
              <Route element={<Layout />}>
                <Route path="/" element={<Painel />} />
                <Route path="/cadastros" element={<ListaCadastros />} />
                <Route path="/cadastros/novo" element={<NovoCadastro />} />
                <Route path="/assinaturas-pendentes" element={<AssinaturasPendentes />} />
                <Route path="/trocar-senha" element={<TrocarSenha />} />
                <Route path="/cadastros/:id/assinar" element={<AssinarCadastro />} />
                <Route path="/cadastros/:id/editar" element={<EditarCadastro />} />
                <Route path="/cadastros/:id" element={<DetalheCadastro />} />
                <Route path="/usuarios" element={<Usuarios />} />
                <Route path="/faq" element={<FAQ />} />
              </Route>
            </Routes>
          </BrowserRouter>
        </AuthProvider>
      </ThemeProvider>
    </ErrorBoundary>
  )
}
