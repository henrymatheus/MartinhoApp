{% load static %}// Service worker do Martinho: permite instalar o site como app e mostra
// uma página amigável quando o celular está sem internet.
// Páginas sempre vêm da internet (a agenda precisa estar atualizada).
// CSS, fontes e imagens ficam guardados no celular depois da primeira visita.
const CACHE = 'martinho-{{ versao }}';
const OFFLINE = '{% url "publico:offline" %}';
const ESSENCIAIS = [
  OFFLINE,
  '{% static "css/tokens.css" %}',
  '{% static "css/martinho.css" %}',
  '{% static "img/martinho-simbolo.svg" %}',
];

self.addEventListener('install', (evento) => {
  evento.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(ESSENCIAIS)));
  self.skipWaiting();
});

self.addEventListener('activate', (evento) => {
  evento.waitUntil(
    caches.keys().then((nomes) => Promise.all(nomes.filter((n) => n !== CACHE).map((n) => caches.delete(n))))
  );
  self.clients.claim();
});

// Aviso de novo agendamento: mostra a notificação no celular.
self.addEventListener('push', (evento) => {
  let dados = { titulo: 'Martinho', corpo: 'Você tem uma novidade na agenda.', url: '/' };
  try { dados = Object.assign(dados, evento.data.json()); } catch (e) {}
  evento.waitUntil(self.registration.showNotification(dados.titulo, {
    body: dados.corpo,
    icon: '{% static "img/icone-192.png" %}',
    badge: '{% static "img/icone-192.png" %}',
    data: { url: dados.url },
  }));
});

// Toque na notificação: abre a agenda naquele dia.
self.addEventListener('notificationclick', (evento) => {
  evento.notification.close();
  const url = (evento.notification.data && evento.notification.data.url) || '/';
  evento.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((janelas) => {
      for (const janela of janelas) {
        if ('focus' in janela) { janela.navigate(url); return janela.focus(); }
      }
      return self.clients.openWindow(url);
    })
  );
});

self.addEventListener('fetch', (evento) => {
  const pedido = evento.request;
  if (pedido.method !== 'GET') return;

  if (pedido.mode === 'navigate') {
    evento.respondWith(fetch(pedido).catch(() => caches.match(OFFLINE)));
    return;
  }

  const url = new URL(pedido.url);
  if (url.pathname.startsWith('{% get_static_prefix %}') || url.hostname.endsWith('gstatic.com')) {
    evento.respondWith(
      caches.match(pedido).then((guardado) =>
        guardado ||
        fetch(pedido).then((resposta) => {
          const copia = resposta.clone();
          caches.open(CACHE).then((cache) => cache.put(pedido, copia));
          return resposta;
        })
      )
    );
  }
});
