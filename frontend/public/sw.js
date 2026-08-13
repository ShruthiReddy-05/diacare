import { precacheAndRoute, cleanupOutdatedCaches } from 'workbox-precaching'
import { registerRoute, NavigationRoute } from 'workbox-routing'
import { createHandlerBoundToURL } from 'workbox-precaching'

precacheAndRoute(self.__WB_MANIFEST)
cleanupOutdatedCaches()

registerRoute(new NavigationRoute(createHandlerBoundToURL('index.html')))

self.addEventListener('push', (event) => {
  let data = { title: 'DiaFit Coach', body: '', url: '/home', tag: 'diafit', eventId: '' }
  try {
    if (event.data) {
      const parsed = event.data.json()
      data = { ...data, ...parsed }
    }
  } catch {}
  const deliveryPromise = data.eventId
    ? fetch(`/api/notifications/events/${data.eventId}/delivered`, { method: 'POST' }).catch(() => {})
    : Promise.resolve()
  event.waitUntil(
    Promise.all([
      self.registration.showNotification(data.title, {
        body: data.body,
        icon: '/favicon.ico',
        badge: '/favicon.ico',
        data: { url: data.url, eventId: data.eventId },
        tag: data.tag,
        renotify: true,
        requireInteraction: true,
        vibrate: [200, 100, 200],
      }),
      deliveryPromise,
    ])
  )
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const data = event.notification.data || {}
  if (data.eventId) {
    fetch(`/api/notifications/events/${data.eventId}/opened`, { method: 'POST' }).catch(() => {})
  }
  let urlToOpen = data.url || '/home'
  if (data.eventId) {
    const sep = urlToOpen.includes('?') ? '&' : '?'
    urlToOpen = `${urlToOpen}${sep}notifEventId=${data.eventId}`
  }
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((windowClients) => {
      for (const client of windowClients) {
        if (client.url === urlToOpen && 'focus' in client) return client.focus()
      }
      return clients.openWindow(urlToOpen)
    })
  )
})
