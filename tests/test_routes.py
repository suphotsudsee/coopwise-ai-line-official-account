import base64
import hashlib
import hmac
import json

API_KEY = "test-api-key-that-is-at-least-32-chars"


def _signature(body: bytes) -> str:
    digest = hmac.new(b"test-secret", body, hashlib.sha256).digest()
    return base64.b64encode(digest).decode()


def test_health(client) -> None:
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_webhook_requires_valid_signature(client) -> None:
    response = client.post("/webhooks/line", json={"events": []})
    assert response.status_code == 401


def test_webhook_accepts_valid_signature(client) -> None:
    body = json.dumps({"events": []}, separators=(",", ":")).encode()
    response = client.post(
        "/webhooks/line",
        content=body,
        headers={"X-Line-Signature": _signature(body), "Content-Type": "application/json"},
    )
    assert response.status_code == 200


def test_webhook_replies_to_rich_menu_postback(client, fake_line_service) -> None:
    payload = {
        "events": [
            {
                "type": "postback",
                "replyToken": "reply-token",
                "source": {"type": "user", "userId": "U123"},
                "postback": {"data": "action=loan_payment"},
            }
        ]
    }
    body = json.dumps(payload, separators=(",", ":")).encode()
    response = client.post(
        "/webhooks/line",
        content=body,
        headers={"X-Line-Signature": _signature(body), "Content-Type": "application/json"},
    )
    assert response.status_code == 200
    assert fake_line_service.replies[0]["reply_token"] == "reply-token"
    assert "ค่างวด" in fake_line_service.replies[0]["text"]


def test_webhook_processes_loan_payment_form(client, fake_line_service) -> None:
    payload = {
        "events": [
            {
                "type": "message",
                "replyToken": "reply-token",
                "source": {"type": "user", "userId": "U123"},
                "message": {
                    "type": "text",
                    "text": "ค่างวด\nเงินต้น: 100000\nดอกเบี้ยต่อปี: 6\nจำนวนเดือน: 12",
                },
            }
        ]
    }
    body = json.dumps(payload, separators=(",", ":")).encode()
    response = client.post(
        "/webhooks/line",
        content=body,
        headers={"X-Line-Signature": _signature(body), "Content-Type": "application/json"},
    )
    assert response.status_code == 200
    assert "ค่างวดต่อเดือน" in fake_line_service.replies[0]["text"]


def test_text_message_requires_api_key(client) -> None:
    response = client.post("/api/v1/messages/text", json={"text": "Hello"})
    assert response.status_code == 401


def test_text_message_uses_default_destination(client, fake_line_service) -> None:
    response = client.post(
        "/api/v1/messages/text",
        json={"text": "สวัสดีสมาชิก"},
        headers={"X-API-Key": API_KEY},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "sent"
    assert fake_line_service.last_text["user_id"] == "Udefault"


def test_flex_message_validates_container_type(client) -> None:
    response = client.post(
        "/api/v1/messages/flex",
        json={
            "alt_text": "รายงาน",
            "contents": {"type": "invalid"},
        },
        headers={"X-API-Key": API_KEY},
    )
    assert response.status_code == 422
