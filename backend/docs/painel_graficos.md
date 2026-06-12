# Painel de Estatísticas e Exportação

<p align="center">
  <img src="./ASAP_icon_hd.png" alt="ASAP" width="120" />
</p>

## Visão geral

Esta funcionalidade adiciona um painel de estatísticas que gera gráficos automaticamente a partir dos cadastros existentes e permite exportar os dados em CSV ou PDF. O objetivo é aumentar o escopo do projeto com uma feature de alto valor: visualização rápida de métricas e extração de relatórios para tomada de decisão.

## Principais comportamentos
- Agregações por campos comuns: status, sexo, faixa etária, mês de cadastro, etc.
- Visualização instantânea em gráficos (barras, donuts, linhas) usando os componentes já presentes.
- Exportação dos dados filtrados/agrupados em CSV e PDF.
- Endpoints read-only protegidos por autenticação e autorização.

## API proposta

- `GET /api/stats/cadastros?group_by=<campo>&from=YYYY-MM-DD&to=YYYY-MM-DD`
  - Parâmetros: `group_by` (status|sexo|idade|mes), `from`, `to` (opcionais)
  - Resposta: `[{ "label": "Ativo", "value": 34 }, ...]`

- `GET /api/stats/cadastros/export?group_by=<campo>&format=csv|pdf&from=...&to=...`
  - Retorna um arquivo para download (`text/csv` ou `application/pdf`).

## Backend (onde adicionar)

Adicionar rota em `backend/app/api/routes/cadastros.py` que realiza consultas agregadas com SQLAlchemy (func.count, group_by). Para export CSV, montar um `StreamingResponse` com o módulo `csv`. Para PDF, reutilizar a stack de geração de PDF já existente se houver (p.ex. `app/services/pdf.py`).

Exemplo de resposta esperada (JSON):

```json
[{"label": "Ativo", "value": 34}, {"label": "Inativo", "value": 12}]
```

## Frontend (onde integrar)

- Criar/atualizar a página `frontend/src/pages/Painel.jsx` para buscar os endpoints e alimentar os componentes `BarChart.jsx` e `DonutChart.jsx` já existentes.
- Mapear a resposta para o formato aceito pelos componentes (rótulo/valor). Exemplo de fetch:

```js
const res = await fetch(`/api/stats/cadastros?group_by=status`);
const data = await res.json();
// transformar em dataset para o componente de gráfico
```

- Botão de export: abrir `/api/stats/cadastros/export?group_by=status&format=csv` para download.

## Segurança e permissões
- Endpoints devem exigir autenticação (token) e verificar permissões (por exemplo, somente `admin` ou `gestor` podem exportar).

## Estimativa de esforço
- Implementação mínima (endpoints + 2 gráficos + export CSV): 1-3 dias por uma pessoa.
- Implementação completa (PDF, filtros avançados, testes): 3-5 dias.

## Testes e validação rápida
- Testar agregações com `curl` ou Postman.
- Validar a exportação CSV abrindo o link no navegador.
- Verificar que gráficos refletem os mesmos números das APIs.

## Próximos passos recomendados
1. Implementar os endpoints `stats/cadastros` (status, sexo, mês).
2. Criar `Painel.jsx` que consome os endpoints e reusa componentes de gráfico.
3. Adicionar botão de export CSV; depois implementar export PDF.
4. Testes manuais e ajustes de UI.

---

Arquivo gerado automaticamente: documentação da nova funcionalidade de painel.
