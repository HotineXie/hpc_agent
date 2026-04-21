// Service Worker for HPC Agent PWA notifications
self.addEventListener('install', (e) => self.skipWaiting());
self.addEventListener('activate', (e) => e.waitUntil(self.clients.claim()));

// Listen for push events from server
self.addEventListener('push', (event) => {
  const data = event.data ? event.data.json() : { title: 'HPC Agent', body: 'New event' };
  // Check detailed preference from IndexedDB or just show all
  // (filtering is done server-side in a future version; for now show all push events)
  event.waitUntil(
    self.registration.showNotification(data.title || 'HPC Agent', {
      body: data.body,
      tag: data.tag || 'hpc-agent-notification',
      icon: '/icon-192.png',
      data: { detailed: data.detailed },
    })
  );
});

// Click notification to open/focus the app and open notification center
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  event.waitUntil(
    self.clients.matchAll({ type: 'window' }).then((clients) => {
      if (clients.length > 0) {
        clients[0].postMessage({ action: 'openNotifCenter' });
        return clients[0].focus();
      }
      return self.clients.openWindow('/?notif=1');
    })
  );
});
