# ASAP — Sistema de Gestão

## Stack
- **Backend:** Python 3.11 + FastAPI + PostgreSQL + SQLAlchemy
- **Frontend:** React 18 + Vite
- **Deploy:** Railway (backend + banco) · Vercel (frontend)

---

## Cadastros em Google Planilha via Apps Script

O sistema pode manter login/usuários no banco atual e gravar **todos os cadastros** em uma planilha do Google.

1. Crie uma Planilha Google.
2. Na planilha, acesse **Extensões → Apps Script**.
3. Cole o conteúdo de `backend/docs/google-apps-script-cadastros.js`.
4. Troque o valor de `TOKEN` por um segredo grande.
5. Clique em **Implantar → Nova implantação → App da Web**.
6. Configure:
   - **Executar como:** você
   - **Quem pode acessar:** qualquer pessoa
7. Copie a URL terminada em `/exec`.
8. No `backend/.env`, adicione:

```env
CADASTROS_STORAGE=sheets
GOOGLE_APPS_SCRIPT_URL=https://script.google.com/macros/s/SEU_DEPLOY_ID/exec
GOOGLE_APPS_SCRIPT_TOKEN=mesmo-token-configurado-no-apps-script
```

A aba `cadastros` e os cabeçalhos são criados automaticamente no primeiro cadastro/listagem.

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

### Novo cadastro, termos e assinatura

- No **novo cadastro**, o assistente ou coordenadora pode assinar no próprio formulário ou usar **Salvar para assinar no tablet**. Nesse segundo fluxo, o cadastro fica salvo com os termos pendentes.
- No tablet, acesse **Assinaturas pendentes**, abra o cadastro da pessoa atendida, marque os dois termos e colete a assinatura. O backend gera automaticamente dois PDFs com os dados e a assinatura, e o cadastro no PC passa a mostrar os termos como concluídos.
- Para aprovação, foto, comprovante de residência e documento pessoal aparecem como **alertas**, mas não bloqueiam a decisão do usuário coordenador. Termos assinados, CPF válido e dados essenciais continuam obrigatórios.
- Os textos jurídicos dos PDFs vêm de `backend/assets/termos/texto_lgpd.txt` e `texto_imagem.txt` — substitua pelo texto oficial da ASAP (ver `backend/assets/termos/README.md`).
- **Prévia:** no formulário, use «Baixar prévia» para conferir o PDF sem gravar o cadastro.
- Cadastros antigos sem os dois PDFs podem mostrar «Termos: pendente» até serem recriados ou tratados manualmente.
- Se você já usava SQLite local (`dev.db`) de uma versão anterior e ocorrer erro de coluna ao subir o backend, apague `backend/dev.db` e suba de novo (perde dados locais) ou faça migração manual; o projeto não inclui Alembic neste repositório.

### Exportações para Excel e relatórios

- No **Painel**, use **Exportar cadastros CSV** para baixar a base completa e **Exportar gráficos CSV** para baixar um resumo com indicadores e séries dos gráficos.
- Em cada gráfico do Painel, o botão **CSV** exporta só aquela série para uso direto no Excel.
- O Painel prioriza gráficos úteis para relatório social: status, novos cadastros por mês, faixa etária, PCD, encaminhamentos, renda média, cor/raça, identidade de gênero e principais cidades.
- Na tela **Cadastros**, o botão **Exportar Excel** baixa os cadastros respeitando os filtros aplicados na lista.
- Os arquivos são CSV com separador `;`, BOM UTF-8 e linha `sep=;`, para abrir corretamente no Excel em português.

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
| `ti` | Visualiza todos os cadastros (sem criar, sem editar, sem upload, sem aprovar e sem excluir) |

---

## Endpoints principais

| Método | Rota | Descrição |
|---|---|---|
| POST | `/api/auth/token` | Login |
| GET | `/api/auth/me` | Usuário logado |
| POST | `/api/auth/usuarios` | Criar usuário (somente coordenadora) |
| GET | `/api/cadastros` | Listar (com filtros) |
| GET | `/api/cadastros/export/cadastros.csv` | Exportar cadastros em CSV compatível com Excel |
| GET | `/api/cadastros/export/graficos.csv` | Exportar resumo dos gráficos em CSV compatível com Excel |
| POST | `/api/cadastros` | Criar cadastro |
| GET | `/api/cadastros/{id}` | Detalhe |
| PATCH | `/api/cadastros/{id}` | Editar |
| DELETE | `/api/cadastros/{id}` | Excluir cadastro (somente coordenadora) |
| POST | `/api/cadastros/{id}/aprovar` | Aprovar |
| GET | `/api/cadastros/{id}/pdf` | Baixar PDF |
| POST | `/api/cadastros/{id}/documentos/{tipo}` | Upload de documento |
