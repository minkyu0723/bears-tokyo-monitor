import json
import os
import smtplib
import sys
from email.message import EmailMessage
from pathlib import Path
from urllib.parse import urljoin

import requests

BASE_URL = "https://bears-tokyo.myshopify.com"
COLLECTION_HANDLE = "new-item-restock"
COLLECTION_URL = f"{BASE_URL}/collections/{COLLECTION_HANDLE}?sort_by=created-descending"
JSON_URL = f"{BASE_URL}/collections/{COLLECTION_HANDLE}/products.json"
STATE_FILE = Path("state.json")
LIMIT = 20  # 첫 페이지에 해당하는 상품만 확인

def fetch_products():
    params = {"limit": LIMIT, "sort_by": "created-descending"}
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; BearsTokyoNewArrivalMonitor/1.0)",
        "Accept": "application/json",
    }
    response = requests.get(JSON_URL, params=params, headers=headers, timeout=25)
    response.raise_for_status()
    payload = response.json()
    products = payload.get("products", [])
    if not isinstance(products, list) or not products:
        raise RuntimeError(
            "Shopify 상품 목록을 읽지 못했거나 비어 있습니다. "
            "컬렉션 주소/공개 JSON 접근 가능 여부를 확인해야 합니다."
        )

    # Shopify 응답을 최신 등록순으로 한 번 더 정렬하고 첫 페이지 분량만 사용
    products.sort(
        key=lambda p: p.get("published_at") or p.get("created_at") or "",
        reverse=True,
    )
    return products[:LIMIT]

def product_url(product):
    handle = product.get("handle")
    if not handle:
        return COLLECTION_URL
    return urljoin(BASE_URL, f"/products/{handle}")

def product_price(product):
    variants = product.get("variants") or []
    prices = [str(v.get("price")) for v in variants if v.get("price") is not None]
    return prices[0] if prices else "가격 정보 확인 필요"

def send_email(products, test=False):
    smtp_user = os.environ.get("NAVER_EMAIL", "").strip()
    smtp_password = os.environ.get("NAVER_APP_PASSWORD", "").strip()
    recipient = os.environ.get("ALERT_TO", "").strip()

    missing = [
        name for name, value in [
            ("NAVER_EMAIL", smtp_user),
            ("NAVER_APP_PASSWORD", smtp_password),
            ("ALERT_TO", recipient),
        ] if not value
    ]
    if missing:
        raise RuntimeError("GitHub Secrets 누락: " + ", ".join(missing))

    msg = EmailMessage()
    msg["Subject"] = "[BEARS' TOKYO] 신규 상품 등록 알림" if not test else "[BEARS' TOKYO] 메일 설정 테스트"
    msg["From"] = smtp_user
    msg["To"] = recipient

    if test:
        msg.set_content(
            "BEARS' TOKYO 상품 감시 프로그램의 이메일 테스트입니다.\n"
            "이 메일을 받았다면 네이버 SMTP 설정이 정상적으로 작동합니다.\n\n"
            f"감시 목록: {COLLECTION_URL}"
        )
    else:
        lines = [
            "BEARS' TOKYO New Arrivals에서 새 상품을 발견했습니다.",
            "",
        ]
        for p in products:
            lines.extend([
                f"상품명: {p.get('title', '상품명 확인 필요')}",
                f"가격: {product_price(p)}",
                f"상품 페이지: {product_url(p)}",
                "",
            ])
        lines.append(f"정렬 기준: Date / New to Old")
        lines.append(f"목록 주소: {COLLECTION_URL}")
        msg.set_content("\n".join(lines))

    # Naver SMTP: STARTTLS 587
    with smtplib.SMTP("smtp.naver.com", 587, timeout=30) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)

def load_state():
    if not STATE_FILE.exists():
        return None
    return json.loads(STATE_FILE.read_text(encoding="utf-8"))

def save_state(ids):
    STATE_FILE.write_text(
        json.dumps({"product_ids": ids}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

def main():
    products = fetch_products()
    current_ids = [str(p["id"]) for p in products if p.get("id") is not None]
    if not current_ids:
        raise RuntimeError("상품 ID가 응답에 없습니다. 안전을 위해 상태를 변경하지 않습니다.")

    # 최초 실행은 현재 상품을 기준 목록으로 저장하고 알림은 보내지 않음
    previous = load_state()
    if previous is None:
        save_state(current_ids)
        print(f"최초 기준 목록 저장 완료: {len(current_ids)}개 상품. 신규 알림은 보내지 않았습니다.")
    else:
        old_ids = set(previous.get("product_ids", []))
        new_products = [p for p in products if str(p.get("id")) not in old_ids]

        if new_products:
            # 메일 발송에 성공한 뒤에만 상태를 갱신해 메일 실패 시 재시도 가능
            send_email(new_products)
            print(f"신규 상품 {len(new_products)}개 이메일 발송 완료.")
        else:
            print("신규 상품이 없습니다.")

        save_state(current_ids)

    if os.environ.get("SEND_TEST_EMAIL", "").lower() == "true":
        send_email([], test=True)
        print("테스트 이메일 발송 완료.")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"오류: {exc}", file=sys.stderr)
        raise
