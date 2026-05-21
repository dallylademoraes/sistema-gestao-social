# Deploy do Apps Script de Usuários

<p align="center">
   <img src="./ASAP_icon_hd.png" alt="ASAP" width="120" />
</p>

Este projeto usa Google Planilhas como armazenamento de cadastros e usuários.

## O que publicar

Cole o conteúdo de `google-apps-script-cadastros.js` no editor do Apps Script da planilha.
O script cria e gerencia duas abas:
- `cadastros`
- `usuarios`

## Passo a passo

1. Abra a planilha no Google Sheets.
2. Vá em `Extensões > Apps Script`.
3. Substitua o conteúdo do arquivo pelo código de `google-apps-script-cadastros.js`.
4. Salve.
5. Vá em `Implantar > Nova implantação`.
6. Escolha o tipo `App da web`.
7. Configure:
   - `Executar como`: você
   - `Quem tem acesso`: qualquer pessoa com o link, ou conforme sua política interna
8. Clique em `Implantar`.
9. Copie a URL publicada do web app.
10. Atualize o `GOOGLE_APPS_SCRIPT_URL` em `backend/.env` se a URL mudar.
11. Garanta que `GOOGLE_APPS_SCRIPT_TOKEN` no `backend/.env` seja igual ao `TOKEN` do script.

## Validar

Depois do deploy, rode no backend:

```powershell
cd backend
.\venv\Scripts\python.exe seed.py
```

Isso cria ou corrige o usuário inicial:
- `admin@asap.org`
- `troque-essa-senha`

## Teste esperado

Se estiver tudo certo, o backend deve conseguir:
- ler o usuário `admin@asap.org` da aba `usuarios`
- autenticar o login sem erro 401
- listar e criar usuários pela tela `/usuarios`

## Se der erro

- Se o login continuar em 401, a implantação do Apps Script provavelmente ainda está na versão antiga.
- Se aparecer `Token inválido`, o `GOOGLE_APPS_SCRIPT_TOKEN` está diferente no backend e no script.
- Se a aba `usuarios` estiver vazia, rode o `seed.py` de novo após o deploy.
