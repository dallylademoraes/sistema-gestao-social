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

Isso abre dois terminais: backend em `http://127.0.0.1:8000/docs` e frontend em `http://localhost:5173`. Se ainda não existir `backend/.env`, o script copia `backend/.env.example` para `backend/.env`.

O `run-dev.ps1` **não** executa o seed. Na **primeira vez**, depois que o backend estiver no ar, abra um terminal na pasta `backend` (com o `venv` ativado) e rode `python seed.py` — veja [Primeiro acesso (login na interface)](#primeiro-acesso-login-na-interface).

### Primeiro acesso (login na interface)

Siga esta ordem na primeira máquina ou banco novo:

1. **Configure o ambiente** — Garanta `backend/.env` com `DATABASE_URL` e `SECRET_KEY` (o `run-dev.ps1` pode criar o `.env` a partir de `.env.example`). Com SQLite no exemplo local, não é obrigatório ter PostgreSQL instalado.
2. **Suba o backend pelo menos uma vez** — Ao iniciar o Uvicorn, a aplicação importa `app.main` e o SQLAlchemy **cria as tabelas** no banco (`create_all`). Sem esse passo, o seed pode falhar por tabela inexistente.
3. **Rode o seed (obrigatório para existir usuário de login)** — No diretório `backend`, com o ambiente virtual ativo:
   ```bash
   python seed.py
   ```
   - Se aparecer `Usuário criado: admin@asap.org / troque-essa-senha`, o primeiro usuário coordenadora foi criado.
   - Se aparecer `Usuário já existe.`, a conta já estava cadastrada; use as credenciais abaixo ou redefina a senha pela aplicação.
4. **Acesse o frontend** em `http://localhost:5173` e faça login na tela de entrada.

**Credenciais padrão após o seed (ambiente de desenvolvimento):**

| Campo   | Valor                 |
|---------|-----------------------|
| E-mail  | `admin@asap.org`      |
| Senha   | `troque-essa-senha`   |

Em produção, troque essa senha assim que possível (ou crie outro usuário e desative o admin padrão).

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate       # Windows: .\venv\Scripts\Activate.ps1
pip install -r requirements.txt

cp .env.example .env           # se ainda não tiver .env; ajuste DATABASE_URL se usar PostgreSQL
# edite .env: SECRET_KEY obrigatória; DATABASE_URL conforme o banco

uvicorn app.main:app --reload  # primeiro start cria as tabelas no banco
```

Em outro terminal (com o mesmo `venv`):

```bash
cd backend
python seed.py                 # cria o usuário inicial; rode uma vez por banco novo
```

Documentação interativa: `http://127.0.0.1:8000/docs` (ou `http://localhost:8000/docs`).

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Acesse: `http://localhost:5173` e use o login descrito em [Primeiro acesso (login na interface)](#primeiro-acesso-login-na-interface).

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
7. O seed cria o mesmo usuário inicial que no ambiente local. Para testar o login: **e-mail** `admin@asap.org`, **senha** `troque-essa-senha` (detalhes e avisos em [Primeiro acesso (login na interface)](#primeiro-acesso-login-na-interface)). Altere a senha em produção.

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
