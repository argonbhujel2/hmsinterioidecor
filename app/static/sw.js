/* Urlabari Interior Decor — Staff PWA */
const CACHE = "uid-staff-v2";
const SHELL = ["/", "/dashboard", "/static/css/admin.css", "/pwa-logo", "/manifest.webmanifest"];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(SHELL).catch(() => {})).then(() => self.skipWaiting())
  );
});
self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});
self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (url.pathname.startsWith("/static/") || url.pathname === "/pwa-logo" || url.pathname === "/manifest.webmanifest") {
    e.respondWith(
      caches.match(e.request).then((r) => r || fetch(e.request).then((res) => {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(e.request, copy)).catch(() => {});
        return res;
      }).catch(() => r))
    );
  }
});
self.addEventListener("push", (e) => {
  let data = { title: "Urlabari Interior", body: "New update", url: "/dashboard", tag: "uid" };
  try {
    if (e.data) data = Object.assign(data, e.data.json());
  } catch (err) {}
  e.waitUntil(
    self.registration.showNotification(data.title || "Urlabari Interior", {
      body: data.body || "",
      icon: data.icon || "/pwa-logo",
      badge: data.badge || "/pwa-logo",
      tag: data.tag || "uid",
      data: { url: data.url || "/dashboard" },
      vibrate: [120, 60, 120],
    })
  );
});
self.addEventListener("notificationclick", (e) => {
  e.notification.close();
  const target = (e.notification.data && e.notification.data.url) || "/dashboard";
  e.waitUntil(
    clients.matchAll({ type: "window", includeUncontrolled: true }).then((list) => {
      for (const c of list) {
        if (c.url.includes(self.location.origin) && "focus" in c) {
          c.navigate(target);
          return c.focus();
        }
      }
      if (clients.openWindow) return clients.openWindow(target);
    })
  );
});
