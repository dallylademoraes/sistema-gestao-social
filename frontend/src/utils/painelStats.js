const MESES = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']

export function contarPorCampo(lista, campo, rotulos = {}) {
  const map = {}
  for (const item of lista) {
    const bruto = item[campo]
    const chave = bruto == null || String(bruto).trim() === '' ? 'Não informado' : String(bruto).trim()
    map[chave] = (map[chave] || 0) + 1
  }
  return Object.entries(map)
    .map(([label, value]) => ({
      label: rotulos[label] ?? label,
      value,
    }))
    .sort((a, b) => b.value - a.value)
}

export function statusDistribuicao(lista) {
  const rotulos = { ativo: 'Ativos', pendente: 'Pendentes', inativo: 'Inativos' }
  const contagem = contarPorCampo(lista, 'status', rotulos)
  const mapa = Object.fromEntries(contagem.map((d) => [d.label, d.value]))
  return ['ativo', 'pendente', 'inativo'].map((s) => ({
    label: rotulos[s],
    value: mapa[rotulos[s]] || 0,
  }))
}

export function cadastrosPorMes(lista, meses = 6) {
  const agora = new Date()
  const buckets = []
  for (let i = meses - 1; i >= 0; i--) {
    const d = new Date(agora.getFullYear(), agora.getMonth() - i, 1)
    buckets.push({
      key: `${d.getFullYear()}-${d.getMonth()}`,
      label: `${MESES[d.getMonth()]}/${String(d.getFullYear()).slice(-2)}`,
      value: 0,
    })
  }
  const indice = Object.fromEntries(buckets.map((b, i) => [b.key, i]))
  for (const c of lista) {
    if (!c.criado_em) continue
    const dt = new Date(c.criado_em)
    const key = `${dt.getFullYear()}-${dt.getMonth()}`
    if (key in indice) buckets[indice[key]].value += 1
  }
  return buckets
}

export function termosLgpd(lista) {
  const ok = lista.filter((c) => c.lgpd_concluido).length
  const pend = lista.length - ok
  return [
    { label: 'Termos ok', value: ok, color: 'var(--metric-accent-1)' },
    { label: 'Termos pendentes', value: pend, color: 'var(--metric-accent-2)' },
  ].filter((d) => d.value > 0)
}

export function topCidades(lista, limite = 5) {
  return contarPorCampo(lista, 'cidade')
    .filter((d) => d.label !== 'Não informado')
    .slice(0, limite)
}

export function identidadeGeneroDistribuicao(lista, limite = 8) {
  return contarPorCampo(lista, 'identidade_genero').slice(0, limite)
}

export function corRacaDistribuicao(lista) {
  return contarPorCampo(lista, 'cor_raca')
}

export function rendaDistribuicao(lista) {
  const ordem = [
    'Sem renda',
    'Até 1 salário mínimo',
    '1 a 2 salários',
    '2 a 3 salários',
    'Acima de 3 salários',
    'Não informado',
  ]
  const dados = contarPorCampo(lista, 'renda_media')
  const mapa = Object.fromEntries(dados.map((d) => [d.label, d.value]))
  return ordem
    .filter((label) => mapa[label])
    .map((label) => ({ label, value: mapa[label] }))
}

function idadeEmAnos(data) {
  if (!data) return null
  const nascimento = new Date(data)
  if (Number.isNaN(nascimento.getTime())) return null
  const hoje = new Date()
  let idade = hoje.getFullYear() - nascimento.getFullYear()
  const antesAniversario = hoje.getMonth() < nascimento.getMonth()
    || (hoje.getMonth() === nascimento.getMonth() && hoje.getDate() < nascimento.getDate())
  if (antesAniversario) idade -= 1
  return idade
}

export function faixaEtariaDistribuicao(lista) {
  const faixas = [
    { label: '16 a 17', min: 16, max: 17, value: 0 },
    { label: '18 a 29', min: 18, max: 29, value: 0 },
    { label: '30 a 44', min: 30, max: 44, value: 0 },
    { label: '45 a 59', min: 45, max: 59, value: 0 },
    { label: '60+', min: 60, max: Infinity, value: 0 },
    { label: 'Não informado', min: null, max: null, value: 0 },
  ]
  for (const c of lista) {
    const idade = idadeEmAnos(c.data_nascimento)
    const faixa = idade == null
      ? faixas[faixas.length - 1]
      : faixas.find((f) => idade >= f.min && idade <= f.max)
    ;(faixa || faixas[faixas.length - 1]).value += 1
  }
  return faixas.filter((f) => f.value > 0).map(({ label, value }) => ({ label, value }))
}

export function encaminhamentoDistribuicao(lista) {
  const com = lista.filter((c) => c.com_encaminhamento).length
  const realizado = lista.filter((c) => c.encaminhamento_realizado).length
  return [
    { label: 'Com encaminhamento', value: com, color: 'var(--metric-accent-3)' },
    { label: 'Encaminhamento realizado', value: realizado, color: 'var(--metric-accent-1)' },
    { label: 'Sem encaminhamento', value: Math.max(lista.length - com, 0), color: '#8fa8a0' },
  ].filter((d) => d.value > 0)
}

export function pcdDistribuicao(lista) {
  const sim = lista.filter((c) => c.pcd).length
  const nao = lista.length - sim
  return [
    { label: 'PCD', value: sim, color: 'var(--metric-accent-3)' },
    { label: 'Não PCD', value: nao, color: '#8fa8a0' },
  ].filter((d) => d.value > 0)
}
