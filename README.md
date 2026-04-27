# ASAP — Sistema de Cadastro

## Stack
- **Backend:** Python 3.11 + FastAPI + PostgreSQL + SQLAlchemy
- **Frontend:** React 18 + Vite
- **Deploy:** Railway (backend + banco) · Vercel (frontend)

---

## Rodando localmente

### Comando unico (Windows)

Na raiz do projeto, rode:

```powershell
powershell -ExecutionPolicy Bypass -File .\run-dev.ps1
```

Isso abre dois terminais: backend em `http://127.0.0.1:8000/docs` e frontend em `http://localhost:5173`.

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# edite .env com sua DATABASE_URL e SECRET_KEY

uvicorn app.main:app --reload
```

Depois rode o seed para criar o primeiro usuário:

```bash
python seed.py
```

Acesse a documentação interativa da API em: http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Acesse: http://localhost:5173

---

## Deploy no Railway (backend + banco)

1. Crie conta em [railway.app](https://railway.app)
2. **New Project → Deploy from GitHub repo** (aponte para a pasta `backend`)
3. Adicione um serviço **PostgreSQL** no mesmo projeto
4. Na aba **Variables** do serviço backend, adicione:
   - `DATABASE_URL` → copie o valor gerado pelo PostgreSQL
   - `SECRET_KEY` → gere com `python -c "import secrets; print(secrets.token_hex(32))"`
5. Railway detecta o `Procfile` automaticamente e sobe o serviço
6. Após o primeiro deploy, rode o seed via **Railway CLI** ou pelo terminal do serviço:
   ```
   python seed.py
   ```

## Deploy do frontend no Vercel

1. Crie conta em [vercel.com](https://vercel.com)
2. **New Project → Import** o repositório
3. Defina **Root Directory** como `frontend`
4. Adicione a variável de ambiente:
   - `VITE_API_URL` = URL do backend no Railway (ex: `https://asap-api.up.railway.app`)
5. Atualize `frontend/src/services/api.js`: troque `baseURL: '/api'` por `baseURL: import.meta.env.VITE_API_URL + '/api'`

---

## Perfis de acesso

| Perfil | Permissões |
|---|---|
| `coordenadora` | Gerencia tudo: cria usuários, cria/edita/exclui cadastros, upload de documentos, visualiza e aprova cadastros |
| `assistente` | Cria e edita cadastros, faz upload de documentos e visualiza cadastros (sem aprovar e sem excluir) |
| `ti` | Visualiza todos os cadastros e aprova cadastros (sem criar, sem editar, sem upload e sem excluir) |

---

## Endpoints principais

| Método | Rota | Descrição |
|---|---|---|
| POST | `/api/auth/token` | Login |
| GET | `/api/auth/me` | Usuário logado |
| POST | `/api/auth/usuarios` | Criar usuário (somente coordenadora) |
| GET | `/api/cadastros` | Listar (com filtros) |
| POST | `/api/cadastros` | Criar cadastro |
| GET | `/api/cadastros/{id}` | Detalhe |
| PATCH | `/api/cadastros/{id}` | Editar |
| DELETE | `/api/cadastros/{id}` | Excluir cadastro (somente coordenadora) |
| POST | `/api/cadastros/{id}/aprovar` | Aprovar |
| GET | `/api/cadastros/{id}/pdf` | Baixar PDF |
| POST | `/api/cadastros/{id}/documentos/{tipo}` | Upload de documento |
