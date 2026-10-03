// Service worker do Martinho: permite instalar o site como app, mostra uma
// página amigável quando o celular está sem internet e recebe os avisos
// push de novo agendamento.
//
// Páginas sempre vêm da internet (a agenda precisa estar atualizada).
// Os arquivos do build (/_next/static) têm o conteúdo no nome, então podem
// ficar guardados no celular para sempre: um CSS novo tem outro nome.
// (No Django a versão do cache era calculada pelo conteúdo do CSS; aqui o
// Next já faz isso.)
const CACHE = 'martinho-v2'
const OFFLINE = '/offline'
const ESSENCIAIS = [OFFLINE, '/img/martinho-simbolo.svg', '/img/icone-192.png']

self.addEventListener('install', (evento) => {
  evento.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(ESSENCIAIS)))
  self.skipWaiting()
})

self.addEventListener('activate', (evento) => {
  evento.waitUntil(
    caches.keys().then((nomes) => Promise.all(nomes.filter((n) => n !== CACHE).map((n) => caches.delete(n)))),
  )
  self.clients.claim()
})

// Aviso de novo agendamento: mostra a notificação no celular.
self.addEventListener('push', (evento) => {
  let dados = { titulo: 'Martinho', corpo: 'Você tem uma novidade na agenda.', url: '/' }
  try {
    dados = Object.assign(dados, evento.data.json())
  } catch {}
  evento.waitUntil(
    self.registration.showNotification(dados.titulo, {
      body: dados.corpo,
      icon: '/img/icone-192.png',
      badge: '/img/icone-192.png',
      data: { url: dados.url },
    }),
  )
})

// Toque na notificação: abre a agenda naquele dia.
self.addEventListener('notificationclick', (evento) => {
  evento.notification.close()
  const url = (evento.notification.data && evento.notification.data.url) || '/'
  evento.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((janelas) => {
      for (const janela of janelas) {
        if ('focus' in janela) {
          janela.navigate(url)
          return janela.focus()
        }
      }
      return self.clients.openWindow(url)
    }),
  )
})

self.addEventListener('fetch', (evento) => {
  const pedido = evento.request
  if (pedido.method !== 'GET') return

  if (pedido.mode === 'navigate') {
    evento.respondWith(fetch(pedido).catch(() => caches.match(OFFLINE)))
    return
  }

  const url = new URL(pedido.url)
  if (url.origin === self.location.origin && (url.pathname.startsWith('/_next/static/') || url.pathname.startsWith('/img/'))) {
    evento.respondWith(
      caches.match(pedido).then(
        (guardado) =>
          guardado ||
          fetch(pedido).then((resposta) => {
            if (resposta.ok) {
              const copia = resposta.clone()
              caches.open(CACHE).then((cache) => cache.put(pedido, copia))
            }
            return resposta
          }),
      ),
    )
  }
})
