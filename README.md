# 📋 Sistema de Cadastro ASAP — Planejamento do Projeto

> **Disciplina de Extensão** | Projeto voluntário para a ASAP  
> **Período:** 21/04/2025 – 20/06/2026 (8 semanas / 2 meses)  
> **Equipe:** Dallyla · Neci · Heloísa

---

## 🧭 Visão Geral

**Objetivo do sistema:** Criar um banco de dados de usuários/as e doadores do projeto ASAP para apoio na prestação de contas descritiva, com coleta de dados pessoais, socioeconômicos e documentos, respeitando a LGPD.

**Premissa de custo zero:** toda a infraestrutura usa Google Workspace (Forms + Sheets + Drive), sem servidor próprio, sem banco de dados pago.

---

## 🛠️ Stack Escolhida e Justificativa

| Camada | Tecnologia | Motivo |
|---|---|---|
| **Formulário de cadastro** | Google Forms | Gratuito, sem código, acessível de qualquer dispositivo, já familiar para o público-alvo |
| **Banco de dados** | Google Sheets | Integração nativa com Forms, exportação direta para Excel/PDF, controle de acesso por e-mail |
| **Armazenamento de documentos** | Google Drive | Upload de fotos, PDFs e termos; organização em pastas por beneficiário |
| **Geração de PDF** | Google Apps Script | Automação gratuita dentro do ecossistema Google; gera PDF do cadastro e envia por e-mail |
| **Controle de acesso** | Google Workspace (compartilhamento) | Permissões granulares: coordenadora, assistente social e TI — sem custo extra |
| **Notificações** | Apps Script + Gmail API | E-mail automático de confirmação após cadastro e alerta para aprovação |
| **Interface de gestão (MVP web)** | HTML + CSS + JS puro | Página estática hospedada no GitHub Pages (grátis) que consome a Sheets via API pública para visualização |

**Por que não usar banco de dados tradicional?**  
Um sistema com Node/Express + PostgreSQL exigiria hospedagem paga, manutenção de servidor e conhecimento técnico contínuo da equipe da ASAP. O ecossistema Google resolve o problema com custo zero, sem deixar dados dependentes de uma pessoa só, e com ferramentas que a coordenação já sabe usar.

---

## 👥 Papéis da Equipe

| Pessoa | Papel principal |
|---|---|
| **Dallyla** | Tech Lead & Arquitetura — decisões técnicas, Apps Script, integração Sheets/Drive, deploy |
| **Neci** | UX & Formulários — design do formulário, validações, fluxo do usuário, documentação de uso |
| **Heloísa** | Dados & Conformidade — estrutura dos campos, LGPD, testes de cadastro, treinamento da equipe ASAP |

---

## 🗓️ Sprints

### Sprint 0 — Kickoff (21/04 – 27/04)
**Objetivo:** alinhar escopo, montar infraestrutura base e distribuir tarefas.

| Responsável | Tarefa |
|---|---|
| **Dallyla** | Criar a pasta principal no Google Drive; criar a planilha-mãe no Sheets com as abas: `Cadastros`, `Pendentes`, `Log`; configurar permissões de acesso para coordenadora, assistente social e TI |
| **Neci** | Mapear todos os campos obrigatórios do levantamento de requisitos; rascunhar wireframe do formulário no Google Forms (sem publicar ainda) |
| **Heloísa** | Levantar quais dados são sensíveis segundo a LGPD (raça/cor, renda, PCD, gênero); redigir primeira versão do Termo de Uso de Imagem e Termo LGPD em Google Docs |

**Entrega ao final:** estrutura de pastas criada, campos mapeados, termos em rascunho.

---

### Sprint 1 — Formulário e Campos (28/04 – 04/05)
**Objetivo:** construir o formulário completo e validar com a equipe ASAP.

| Responsável | Tarefa |
|---|---|
| **Dallyla** | Publicar o Google Forms conectado à planilha; configurar seções do formulário (dados pessoais, socioeconômicos, encaminhamento); testar envio e recebimento na Sheets |
| **Neci** | Definir ordem lógica dos campos no formulário; escrever as instruções/textos de ajuda de cada campo; criar seção de upload de documentos (foto, comprovante de endereço, RG, termos) via Drive |
| **Heloísa** | Revisar campos sensíveis (raça/cor, PCD, identidade de gênero, renda) e garantir linguagem adequada; conferir se todos os campos do levantamento de requisitos estão presentes; validar o termo LGPD com a coordenação |

**Entrega ao final:** formulário publicado e funcional, validado pela equipe ASAP.

---

### Sprint 2 — Automações e Fluxo de Aprovação (05/05 – 18/05)
**Objetivo:** automatizar o fluxo pós-cadastro (e-mail de confirmação, alerta de aprovação, geração de PDF).

| Responsável | Tarefa |
|---|---|
| **Dallyla** | Desenvolver script em Google Apps Script para: (1) enviar e-mail de confirmação ao cadastrado; (2) mover linha para aba `Pendentes` até aprovação; (3) gerar PDF do cadastro formatado e salvar no Drive |
| **Neci** | Criar template visual do PDF do cadastro (layout, logo ASAP, campos organizados); escrever o texto do e-mail de confirmação e do alerta para a coordenadora |
| **Heloísa** | Testar fluxo completo: preencher formulário → verificar Sheets → checar e-mail → verificar PDF gerado; documentar bugs e melhorias; validar com assistente social da ASAP |

**Entrega ao final:** automação funcional de ponta a ponta testada com dados reais de teste.

---

### Sprint 3 — Prevenção de Duplicatas e Painel (19/05 – 01/06)
**Objetivo:** implementar checagem de CPF duplicado e painel de visualização para a gestão.

| Responsável | Tarefa |
|---|---|
| **Dallyla** | Implementar lógica de detecção de CPF duplicado via Apps Script (verificar CPF na planilha antes de confirmar cadastro; alertar por e-mail se duplicata detectada); publicar MVP do painel web (GitHub Pages) |
| **Neci** | Prototipar e finalizar o painel de visualização (lista de cadastros, filtros por status: ativo/pendente, busca por nome/CPF); garantir que o painel é acessível em dispositivos móveis |
| **Heloísa** | Testar casos de borda: CPF duplicado, campos faltando, upload sem arquivo; criar manual de uso do sistema para a coordenação da ASAP (Google Docs, passo a passo com prints) |

**Entrega ao final:** duplicatas bloqueadas, painel web funcionando, manual de uso pronto.

---

### Sprint 4 — Exportação, Testes Finais e Entrega (02/06 – 20/06)
**Objetivo:** finalizar exportação de dados, ajustes finais, treinar a equipe ASAP e entregar.

| Responsável | Tarefa |
|---|---|
| **Dallyla** | Implementar exportação para Excel e PDF via Apps Script (botão no painel ou script agendado); garantir backup automático semanal da planilha; escrever documentação técnica do sistema |
| **Neci** | Aplicar feedbacks de UX da equipe ASAP; ajustar textos do formulário e e-mails conforme necessário; preparar apresentação final do projeto (slides) |
| **Heloísa** | Conduzir sessão de treinamento com a equipe ASAP (coordenadora + assistente social); coletar feedback pós-treinamento; garantir que o sistema está em conformidade com LGPD na versão final |

**Entrega ao final:** sistema entregue, equipe ASAP treinada, documentação completa, apresentação da disciplina pronta.

---

## 📦 Artefatos de Entrega

- [ ] Google Forms publicado e conectado à Sheets
- [ ] Planilha com abas `Cadastros`, `Pendentes`, `Log`
- [ ] Script de automação (confirmação, aprovação, PDF)
- [ ] Painel web de visualização (GitHub Pages)
- [ ] Termos LGPD e de Uso de Imagem
- [ ] Manual de uso para a ASAP
- [ ] Documentação técnica do sistema
- [ ] Apresentação final da disciplina

---

## ⚠️ Riscos e Mitigações

| Risco | Mitigação |
|---|---|
| Equipe ASAP sem conta Google | Criar conta institucional gratuita no início da Sprint 0 |
| Limite de respostas do Forms | Sheets suporta até 5 milhões de células — sem risco para o volume do projeto |
| Perda de dados | Habilitar histórico de versões no Sheets + backup manual na Sprint 4 |
| LGPD | Acesso restrito, termos assinados digitalmente, dados sensíveis com permissão diferenciada |

---

*Documento gerado em 17/04/2026 · Projeto de Extensão Universitária*
