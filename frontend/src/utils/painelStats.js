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

export function pcdDistribuicao(lista) {
  const sim = lista.filter((c) => c.pcd).length
  const nao = lista.length - sim
  return [
    { label: 'PCD', value: sim, color: 'var(--metric-accent-3)' },
    { label: 'Não PCD', value: nao, color: '#8fa8a0' },
  ].filter((d) => d.value > 0)
}
