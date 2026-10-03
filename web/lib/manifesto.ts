/** O arquivo que o celular lê para instalar o site como app. */
export function manifesto(nome: string, nomeCurto: string, inicio: string) {
  const cor = '#0e2240'
  const icone = (arquivo: string, tamanho: string, finalidade = 'any') => ({
    src: `/img/${arquivo}`,
    sizes: tamanho,
    type: 'image/png',
    purpose: finalidade,
  })
  return Response.json(
    {
      name: nome,
      short_name: nomeCurto,
      lang: 'pt-BR',
      start_url: inicio,
      scope: inicio,
      display: 'standalone',
      background_color: cor,
      theme_color: cor,
      icons: [icone('icone-192.png', '192x192'), icone('icone-512.png', '512x512'), icone('icone-512.png', '512x512', 'maskable')],
    },
    { headers: { 'Content-Type': 'application/manifest+json' } },
  )
}
