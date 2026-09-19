// 최소한의 오프라인 캐싱 서비스워커. 데이터가 빌드 시점에 이미 정적 JSON으로 고정돼
// 있는 대시보드라서, 앱 셸 + 데이터를 캐시해두면 네트워크 없이도(내부망/오프라인) 그대로
// 실행 가능하다.
const CACHE_NAME = "fg-dashboard-v1";
const PRECACHE_URLS = ["/", "/manifest.json", "/data/dashboard.json", "/icon-192.png", "/icon-512.png"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE_URLS)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;
  event.respondWith(
    caches.match(event.request).then((cached) => {
      const network = fetch(event.request)
        .then((response) => {
          if (response && response.status === 200) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
          }
          return response;
        })
        .catch(() => cached);
      return cached || network;
    })
  );
});
