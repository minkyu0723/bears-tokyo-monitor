# BEARS' TOKYO New Arrivals Monitor

Shopify 컬렉션의 첫 페이지를 5분 간격으로 확인하고, 새 상품이 나타나면 네이버 메일로 알립니다.

## 감시 설정
- 컬렉션: `https://bears-tokyo.myshopify.com/collections/new-item-restock?sort_by=created-descending`
- 정렬: Date / New to Old (`created-descending`)
- 범위: 첫 페이지 20개
- 최초 실행: 현재 상품 ID를 기준 목록으로 저장하며 알림은 보내지 않음
- 이후 실행: 기준 목록에 없던 상품만 메일 발송
- 메일 발송 성공 후 상품 ID 목록 갱신

## GitHub 저장소에 올릴 파일
다음 구조 그대로 올립니다.

```text
bears-tokyo-monitor/
├── monitor.py
├── requirements.txt
├── state.json          # 최초 실행 시 자동 생성
└── .github/
    └── workflows/
        └── monitor.yml
```

## GitHub Secrets 등록
Repository → Settings → Secrets and variables → Actions → New repository secret에서 아래 3개를 등록합니다.

| Name | Value |
|---|---|
| `NAVER_EMAIL` | 발신용 네이버 이메일 주소 |
| `NAVER_APP_PASSWORD` | 네이버에서 발급한 앱 비밀번호 |
| `ALERT_TO` | 알림을 받을 이메일 주소 |

비밀번호를 코드, README, 일반 파일에 넣지 마세요.

## 실행
Actions 탭에서 `BEARS TOKYO New Arrivals Monitor`를 선택하고 `Run workflow`를 누릅니다.
첫 실행은 기준 상품 목록을 저장합니다. `send_test_email`을 체크하면 테스트 메일도 발송합니다.
이후 자동 실행이 시작됩니다.

## 주의
- GitHub의 예약 실행은 최소 5분 간격을 지원하지만, 서버 부하에 따라 지연될 수 있습니다.
- 공개 저장소의 코드와 state.json은 다른 사람도 볼 수 있습니다. 이메일 비밀번호는 반드시 GitHub Secrets에만 저장하세요.
- GitHub Actions 예약 작업은 공개 저장소가 60일간 활동이 없으면 자동 비활성화될 수 있습니다.
- Shopify의 공개 상품 JSON 접근이 쇼핑몰 설정에 의해 차단되거나 응답 구조가 바뀌면 실행이 실패할 수 있습니다. Actions의 실행 로그에서 오류를 확인해야 합니다.
- 첫 페이지 20개만 확인합니다. 짧은 시간에 20개보다 많은 상품이 등록되면 일부를 놓칠 수 있습니다.
