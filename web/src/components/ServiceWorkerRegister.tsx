"use client";

import { useEffect } from "react";

/** PWA 오프라인 캐싱용 서비스워커를 등록한다. 실패해도 앱 동작에는 영향 없음. */
export function ServiceWorkerRegister() {
  useEffect(() => {
    if (typeof window === "undefined" || !("serviceWorker" in navigator)) return;
    navigator.serviceWorker.register("/sw.js").catch(() => {
      // 오프라인 캐싱은 선택 기능이라 실패해도 조용히 무시
    });
  }, []);

  return null;
}
