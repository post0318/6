# Session 15 — PWA(설치형 앱) 지원 추가

## 요청

이 대시보드를 APK 등 독립 앱으로 만들어 내부망에서 쓸 수 있는지. 이 컴퓨터에는
Android 빌드 도구(Java/Android SDK/Gradle)가 없어 실제 APK 빌드는 별도 설치가
필요하다고 안내하고, 사용자가 더 가벼운 대안(PWA)을 선택.

## 왜 이 대시보드는 PWA/오프라인화에 잘 맞는가

`web/public/data/dashboard.json`이 빌드 시점에 이미 고정된 정적 파일이라, 실행 중
외부 API 호출이 전혀 없다. 즉 앱 셸(HTML/CSS/JS)과 이 JSON만 캐시해두면 네트워크
없이도(내부망/완전 오프라인) 그대로 동작한다.

## 구현

- `public/manifest.json`: 앱 이름·아이콘·`display: standalone`(주소창 없는 독립 앱
  화면) 등록.
- `public/icon-192.png`, `public/icon-512.png`: PIL로 생성한 간단한 "FG" 모노그램
  아이콘(blue `#2a78d6` 배경).
- `public/sw.js`: 최소 서비스워커 — 앱 셸/manifest/dashboard.json/아이콘을 캐시하고,
  네트워크 우선 시도 후 실패하면 캐시로 폴백(오프라인에서도 동작).
- `src/components/ServiceWorkerRegister.tsx`: 클라이언트에서 서비스워커 등록(실패해도
  무시).
- `layout.tsx`에 manifest 링크·아이콘·`appleWebApp`·`viewport.themeColor` 메타데이터
  추가.

## 사용 방법

Android/iOS 모두 크롬·사파리에서 사이트 접속 후 "홈 화면에 추가"를 누르면 아이콘이
생기고, 독립 앱처럼(주소창 없이) 실행된다. 한 번 열어서 캐시가 채워지면 이후로는
네트워크 없이도 실행 가능 — 내부망/오프라인 환경에서 바로 쓸 수 있는 목적에 부합.

## 이후 필요하면: 진짜 APK

지금 이 PWA를 그대로 Capacitor로 감싸면 서명된 실제 APK 파일도 만들 수 있다(정적
사이트라 큰 수정 없이 가능). 다만 Java JDK + Android SDK + Gradle(보통 Android Studio
통째로) 설치가 선행돼야 하고, 이 컴퓨터엔 현재 없다 — 필요해지면 그때 설치부터
진행하면 된다.
