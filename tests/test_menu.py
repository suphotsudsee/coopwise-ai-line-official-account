from app.services.menu import reply_for_postback, reply_for_text


def test_loan_payment_calculation() -> None:
    result = reply_for_text("ค่างวด\nเงินต้น: 100,000\nดอกเบี้ยต่อปี: 6\nจำนวนเดือน: 12")
    assert result is not None
    assert "8,606.64" in result


def test_debt_capacity_calculation() -> None:
    result = reply_for_text(
        "ภาระหนี้\nรายได้ต่อเดือน: 30000\nค่าใช้จ่ายต่อเดือน: 10000\nหนี้เดิมต่อเดือน: 3000\nค่างวดใหม่: 5000"
    )
    assert result is not None
    assert "26.7%" in result
    assert "12,000.00" in result


def test_dividend_calculation() -> None:
    result = reply_for_text("ปันผล\nทุนเรือนหุ้นเฉลี่ย: 50000\nอัตราปันผล: 5")
    assert result is not None
    assert "2,500.00" in result


def test_deposit_interest_calculation() -> None:
    result = reply_for_text("ดอกเบี้ยฝาก\nเงินต้น: 100000\nดอกเบี้ยต่อปี: 2\nจำนวนวัน: 365")
    assert result is not None
    assert "2,000.00" in result


def test_summary_calculation() -> None:
    result = reply_for_text("สรุปรายการ\nรายการ:\n1200\n3,500\n800")
    assert result is not None
    assert "5,500.00" in result


def test_invalid_form_returns_guidance() -> None:
    result = reply_for_text("ค่างวด\nเงินต้น: 1000")
    assert result is not None
    assert "ข้อมูลไม่ครบ" in result


def test_postback_help() -> None:
    assert "วิธีใช้งาน" in reply_for_postback("action=help")
