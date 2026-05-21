export function baixarBlob(blob, nomeArquivo) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = nomeArquivo
  a.rel = 'noopener'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  setTimeout(() => URL.revokeObjectURL(url), 60_000)
}

function protegerCelula(valor) {
  if (valor == null) return ''
  const texto = String(valor)
  return /^[=+\-@]/.test(texto) ? `'${texto}` : texto
}

function csvLinha(valores) {
  return valores
    .map((valor) => `"${protegerCelula(valor).replace(/"/g, '""')}"`)
    .join(';')
}

export function baixarCsvLinhas(linhas, nomeArquivo) {
  const conteudo = ['sep=;', ...linhas.map(csvLinha)].join('\n')
  const blob = new Blob([`\ufeff${conteudo}`], { type: 'text/csv;charset=utf-8' })
  baixarBlob(blob, nomeArquivo)
}

export function baixarCsvGrafico(titulo, data) {
  const slug = titulo
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '') || 'grafico'
  baixarCsvLinhas(
    [
      ['Série', 'Quantidade'],
      ...data.map((item) => [item.label, item.value]),
    ],
    `${slug}.csv`
  )
}
