const SHEET_NAME = 'cadastros';
const TOKEN = 'troque-este-token-por-um-segredo-grande';

const HEADERS = [
  'id',
  'nome',
  'nome_social',
  'cpf',
  'rg',
  'orgao_expedidor',
  'data_nascimento',
  'email',
  'telefone',
  'endereco',
  'cidade',
  'uf',
  'estado_civil',
  'cor_raca',
  'identidade_genero',
  'pcd',
  'renda_media',
  'com_encaminhamento',
  'encaminhamento_realizado',
  'foto_url',
  'comprovante_residencia_url',
  'documento_pessoal_url',
  'termo_imagem_url',
  'termo_lgpd_url',
  'status',
  'aprovado_por_id',
  'observacoes',
  'criado_em',
  'atualizado_em',
];

function doPost(e) {
  try {
    const body = JSON.parse(e.postData.contents || '{}');
    if (body.token !== TOKEN) {
      return json({ ok: false, error: 'Token inválido' });
    }

    const payload = body.payload || {};
    if (body.action === 'list') return json({ ok: true, data: listRows() });
    if (body.action === 'get') return json({ ok: true, data: getRow(Number(payload.id)) });
    if (body.action === 'create') return json({ ok: true, data: createRow(payload.row || {}) });
    if (body.action === 'update') return json({ ok: true, data: updateRow(Number(payload.id), payload.row || {}) });
    if (body.action === 'delete') {
      deleteRow(Number(payload.id));
      return json({ ok: true, data: true });
    }
    return json({ ok: false, error: 'Ação inválida' });
  } catch (err) {
    return json({ ok: false, error: String(err && err.message ? err.message : err) });
  }
}

function json(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

function sheet() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sh = ss.getSheetByName(SHEET_NAME);
  if (!sh) sh = ss.insertSheet(SHEET_NAME);
  ensureHeaders(sh);
  return sh;
}

function ensureHeaders(sh) {
  const current = sh.getRange(1, 1, 1, Math.max(sh.getLastColumn(), HEADERS.length)).getValues()[0];
  const missing = HEADERS.some((h, i) => current[i] !== h);
  if (missing) {
    sh.getRange(1, 1, 1, HEADERS.length).setValues([HEADERS]);
    sh.setFrozenRows(1);
  }
}

function listRows() {
  const sh = sheet();
  const lastRow = sh.getLastRow();
  if (lastRow < 2) return [];
  return sh.getRange(2, 1, lastRow - 1, HEADERS.length).getValues().map(valuesToObject);
}

function getRow(id) {
  const found = findRowIndex(id);
  if (!found) return null;
  return valuesToObject(sheet().getRange(found, 1, 1, HEADERS.length).getValues()[0]);
}

function createRow(row) {
  const sh = sheet();
  const newId = nextId();
  const now = new Date().toISOString();
  const normalized = Object.assign({}, row, {
    id: newId,
    status: row.status || 'pendente',
    criado_em: row.criado_em || now,
    atualizado_em: row.atualizado_em || now,
  });
  sh.appendRow(HEADERS.map(h => normalized[h] === undefined || normalized[h] === null ? '' : normalized[h]));
  return getRow(newId);
}

function updateRow(id, row) {
  const sh = sheet();
  const found = findRowIndex(id);
  if (!found) throw new Error('Cadastro não encontrado');
  const current = valuesToObject(sh.getRange(found, 1, 1, HEADERS.length).getValues()[0]);
  const updated = Object.assign({}, current, row, { id: id, atualizado_em: new Date().toISOString() });
  sh.getRange(found, 1, 1, HEADERS.length).setValues([HEADERS.map(h => updated[h] === undefined || updated[h] === null ? '' : updated[h])]);
  return getRow(id);
}

function deleteRow(id) {
  const found = findRowIndex(id);
  if (!found) throw new Error('Cadastro não encontrado');
  sheet().deleteRow(found);
}

function findRowIndex(id) {
  const sh = sheet();
  const lastRow = sh.getLastRow();
  if (lastRow < 2) return null;
  const ids = sh.getRange(2, 1, lastRow - 1, 1).getValues();
  for (let i = 0; i < ids.length; i++) {
    if (Number(ids[i][0]) === Number(id)) return i + 2;
  }
  return null;
}

function nextId() {
  const rows = listRows();
  return rows.reduce((max, row) => Math.max(max, Number(row.id) || 0), 0) + 1;
}

function valuesToObject(values) {
  const row = {};
  HEADERS.forEach((h, i) => {
    const value = values[i];
    row[h] = value instanceof Date ? value.toISOString() : value;
  });
  return row;
}

function popularCadastrosFake() {
  limparCadastros();

  const hoje = new Date();
  const fakeRows = [
    {
      nome: 'Ana Carolina Souza',
      nome_social: '',
      cpf: '123.456.789-09',
      rg: '1234567',
      orgao_expedidor: 'SSP-TO',
      data_nascimento: '1994-03-12',
      email: 'ana.souza@example.com',
      telefone: '(63) 99911-2233',
      endereco: 'Rua das Acacias, 120',
      cidade: 'Palmas',
      uf: 'TO',
      estado_civil: 'Solteira',
      cor_raca: 'Parda',
      identidade_genero: 'Mulher cis',
      pcd: false,
      renda_media: '1 a 2 salarios',
      com_encaminhamento: true,
      encaminhamento_realizado: false,
      foto_url: 'fake/foto-ana.jpg',
      comprovante_residencia_url: 'fake/comprovante-ana.pdf',
      documento_pessoal_url: 'fake/documento-ana.pdf',
      termo_imagem_url: 'fake/termo-imagem-ana.pdf',
      termo_lgpd_url: 'fake/termo-lgpd-ana.pdf',
      status: 'ativo',
      aprovado_por_id: 1,
      observacoes: 'Cadastro fake para testes do painel.',
      criado_em: diasAtras(hoje, 10),
    },
    {
      nome: 'Bruno Henrique Lima',
      nome_social: '',
      cpf: '987.654.321-00',
      rg: '7654321',
      orgao_expedidor: 'SSP-TO',
      data_nascimento: '1987-11-02',
      email: 'bruno.lima@example.com',
      telefone: '(63) 99222-3344',
      endereco: 'Avenida Brasil, 455',
      cidade: 'Araguaina',
      uf: 'TO',
      estado_civil: 'Casado',
      cor_raca: 'Preta',
      identidade_genero: 'Homem cis',
      pcd: false,
      renda_media: '2 a 3 salarios',
      com_encaminhamento: true,
      encaminhamento_realizado: true,
      foto_url: 'fake/foto-bruno.jpg',
      comprovante_residencia_url: 'fake/comprovante-bruno.pdf',
      documento_pessoal_url: 'fake/documento-bruno.pdf',
      termo_imagem_url: 'fake/termo-imagem-bruno.pdf',
      termo_lgpd_url: 'fake/termo-lgpd-bruno.pdf',
      status: 'ativo',
      aprovado_por_id: 1,
      observacoes: 'Encaminhado para atendimento social.',
      criado_em: diasAtras(hoje, 25),
    },
    {
      nome: 'Camila Oliveira Santos',
      nome_social: 'Cami',
      cpf: '111.222.333-96',
      rg: '9988776',
      orgao_expedidor: 'SSP-MA',
      data_nascimento: '2001-07-28',
      email: 'camila.santos@example.com',
      telefone: '(99) 98888-7777',
      endereco: 'Travessa Norte, 88',
      cidade: 'Imperatriz',
      uf: 'MA',
      estado_civil: 'Solteira',
      cor_raca: 'Branca',
      identidade_genero: 'Mulher trans',
      pcd: false,
      renda_media: 'Ate 1 salario',
      com_encaminhamento: false,
      encaminhamento_realizado: false,
      foto_url: '',
      comprovante_residencia_url: 'fake/comprovante-camila.pdf',
      documento_pessoal_url: '',
      termo_imagem_url: '',
      termo_lgpd_url: '',
      status: 'pendente',
      aprovado_por_id: '',
      observacoes: 'Pendente de assinatura dos termos.',
      criado_em: diasAtras(hoje, 4),
    },
    {
      nome: 'Diego Matos Ferreira',
      nome_social: '',
      cpf: '222.333.444-05',
      rg: '4455667',
      orgao_expedidor: 'SSP-PA',
      data_nascimento: '1978-01-19',
      email: 'diego.ferreira@example.com',
      telefone: '(94) 97777-6655',
      endereco: 'Rua Belem, 32',
      cidade: 'Maraba',
      uf: 'PA',
      estado_civil: 'Divorciado',
      cor_raca: 'Parda',
      identidade_genero: 'Homem cis',
      pcd: true,
      renda_media: 'Ate 1 salario',
      com_encaminhamento: true,
      encaminhamento_realizado: false,
      foto_url: 'fake/foto-diego.jpg',
      comprovante_residencia_url: '',
      documento_pessoal_url: 'fake/documento-diego.pdf',
      termo_imagem_url: 'fake/termo-imagem-diego.pdf',
      termo_lgpd_url: 'fake/termo-lgpd-diego.pdf',
      status: 'pendente',
      aprovado_por_id: '',
      observacoes: 'Cadastro fake com alerta de comprovante pendente.',
      criado_em: diasAtras(hoje, 45),
    },
    {
      nome: 'Elisa Martins Rocha',
      nome_social: '',
      cpf: '333.444.555-14',
      rg: '3344556',
      orgao_expedidor: 'SSP-TO',
      data_nascimento: '1963-09-05',
      email: 'elisa.rocha@example.com',
      telefone: '(63) 96666-5544',
      endereco: 'Alameda Central, 900',
      cidade: 'Gurupi',
      uf: 'TO',
      estado_civil: 'Viuva',
      cor_raca: 'Indigena',
      identidade_genero: 'Mulher cis',
      pcd: true,
      renda_media: 'Sem renda',
      com_encaminhamento: false,
      encaminhamento_realizado: false,
      foto_url: 'fake/foto-elisa.jpg',
      comprovante_residencia_url: 'fake/comprovante-elisa.pdf',
      documento_pessoal_url: 'fake/documento-elisa.pdf',
      termo_imagem_url: 'fake/termo-imagem-elisa.pdf',
      termo_lgpd_url: 'fake/termo-lgpd-elisa.pdf',
      status: 'inativo',
      aprovado_por_id: '',
      observacoes: 'Cadastro fake inativo.',
      criado_em: diasAtras(hoje, 80),
    },
    {
      nome: 'Felipe Andrade Costa',
      nome_social: '',
      cpf: '444.555.666-23',
      rg: '2211334',
      orgao_expedidor: 'SSP-GO',
      data_nascimento: '1999-12-17',
      email: 'felipe.costa@example.com',
      telefone: '(62) 95555-4433',
      endereco: 'Rua Goiania, 77',
      cidade: 'Goiania',
      uf: 'GO',
      estado_civil: 'Uniao estavel',
      cor_raca: 'Amarela',
      identidade_genero: 'Nao binario',
      pcd: false,
      renda_media: '3 a 5 salarios',
      com_encaminhamento: true,
      encaminhamento_realizado: true,
      foto_url: 'fake/foto-felipe.jpg',
      comprovante_residencia_url: 'fake/comprovante-felipe.pdf',
      documento_pessoal_url: 'fake/documento-felipe.pdf',
      termo_imagem_url: 'fake/termo-imagem-felipe.pdf',
      termo_lgpd_url: 'fake/termo-lgpd-felipe.pdf',
      status: 'ativo',
      aprovado_por_id: 1,
      observacoes: 'Cadastro fake completo.',
      criado_em: diasAtras(hoje, 120),
    },
  ];

  fakeRows.forEach(row => createRow(row));
  SpreadsheetApp.getUi().alert(`${fakeRows.length} cadastros fake foram criados na aba ${SHEET_NAME}.`);
}

function limparCadastros() {
  const sh = sheet();
  const lastRow = sh.getLastRow();
  if (lastRow > 1) {
    sh.deleteRows(2, lastRow - 1);
  }
}

function diasAtras(base, dias) {
  const d = new Date(base);
  d.setDate(d.getDate() - dias);
  return d.toISOString();
}
