import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AuthProvider } from './hooks/useAuth'
import { ThemeProvider } from './hooks/useTheme'
import Layout from './components/Layout'
import Login from './pages/Login'
import Painel from './pages/Painel'
import ListaCadastros from './pages/ListaCadastros'
import DetalheCadastro from './pages/DetalheCadastro'
import NovoCadastro from './pages/NovoCadastro'
import EditarCadastro from './pages/EditarCadastro'
import Usuarios from './pages/Usuarios'
import EsqueciSenha from './pages/EsqueciSenha'
import RedefinirSenha from './pages/RedefinirSenha'

export default function App() {
  return (
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
              <Route path="/cadastros/:id/editar" element={<EditarCadastro />} />
              <Route path="/cadastros/:id" element={<DetalheCadastro />} />
              <Route path="/usuarios" element={<Usuarios />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  )
}
