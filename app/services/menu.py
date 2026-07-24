import math
import re
from collections.abc import Callable
from urllib.parse import parse_qs

WELCOME_TEXT = (
    "ยินดีต้อนรับสู่ CoopWise AI\nเลือกบริการจากเมนูด้านล่าง แล้วกรอกข้อมูลตามแบบฟอร์ม ระบบจะคำนวณและส่งผลกลับในแชตนี้"
)

HELP_TEXT = (
    "วิธีใช้งาน CoopWise AI\n"
    "1. เลือกรายการจากเมนูด้านล่าง\n"
    "2. LINE จะเปิดแบบฟอร์มในช่องข้อความ\n"
    "3. กรอกตัวเลขหลังเครื่องหมาย : แล้วกดส่ง\n\n"
    "รองรับ: ค่างวดสินเชื่อ, ภาระหนี้, เงินปันผล, "
    "ดอกเบี้ยเงินฝาก และสรุปรายการ\n"
    "หมายเหตุ: ผลคำนวณเป็นข้อมูลเบื้องต้น ไม่ใช่การอนุมัติสินเชื่อ"
)

_POSTBACK_REPLIES = {
    "loan_payment": ("กรอกเงินต้น อัตราดอกเบี้ยต่อปี และจำนวนเดือนในแบบฟอร์มที่เปิดขึ้น จากนั้นกดส่งเพื่อคำนวณค่างวด"),
    "debt_capacity": ("กรอกรายได้ ค่าใช้จ่าย หนี้เดิม และค่างวดใหม่ จากนั้นกดส่งเพื่อประเมินภาระหนี้เบื้องต้น"),
    "dividend": ("กรอกทุนเรือนหุ้นเฉลี่ยและอัตราปันผล จากนั้นกดส่งเพื่อคำนวณเงินปันผล"),
    "deposit_interest": ("กรอกเงินต้น อัตราดอกเบี้ยต่อปี และจำนวนวัน จากนั้นกดส่งเพื่อคำนวณดอกเบี้ยเงินฝาก"),
    "summary": ("กรอกจำนวนเงินทีละบรรทัดในแบบฟอร์มที่เปิดขึ้น จากนั้นกดส่งเพื่อดูยอดรวมและค่าเฉลี่ย"),
    "help": HELP_TEXT,
}

_NUMBER_PATTERN = re.compile(r"-?\d[\d,]*(?:\.\d+)?")


class MenuInputError(ValueError):
    pass


def reply_for_postback(data: str) -> str:
    action = parse_qs(data, keep_blank_values=True).get("action", [""])[0]
    return _POSTBACK_REPLIES.get(action, HELP_TEXT)


def reply_for_text(text: str) -> str | None:
    stripped = text.strip()
    if not stripped:
        return None

    first_line = stripped.splitlines()[0].strip().lower()
    handlers: tuple[tuple[tuple[str, ...], Callable[[str], str]], ...] = (
        (("ค่างวด", "loan"), _loan_payment),
        (("ภาระหนี้", "debt"), _debt_capacity),
        (("ปันผล", "dividend"), _dividend),
        (("ดอกเบี้ยฝาก", "deposit"), _deposit_interest),
        (("สรุปรายการ", "summary"), _summary),
        (("ช่วยเหลือ", "help", "เมนู"), lambda _: HELP_TEXT),
    )

    for prefixes, handler in handlers:
        if any(first_line.startswith(prefix) for prefix in prefixes):
            try:
                return handler(stripped)
            except MenuInputError as exc:
                return f"ข้อมูลไม่ครบหรือรูปแบบไม่ถูกต้อง\n{exc}\n\nกดเมนูเดิมเพื่อเปิดแบบฟอร์มใหม่"
    return "ไม่พบรูปแบบคำสั่งนี้ กรุณาเลือกบริการจากเมนูด้านล่าง หรือพิมพ์ “ช่วยเหลือ”"


def _loan_payment(text: str) -> str:
    fields = _parse_fields(text)
    principal = _required(fields, "เงินต้น", "principal")
    annual_rate = _required(fields, "ดอกเบี้ยต่อปี", "ดอกเบี้ย", "rate")
    months = _required(fields, "จำนวนเดือน", "เดือน", "months")
    if principal <= 0 or annual_rate < 0 or months <= 0 or not months.is_integer():
        raise MenuInputError("เงินต้นและจำนวนเดือนต้องมากกว่า 0 และดอกเบี้ยต้องไม่ติดลบ")

    month_count = int(months)
    monthly_rate = annual_rate / 100 / 12
    if monthly_rate == 0:
        installment = principal / month_count
    else:
        installment = principal * monthly_rate / (1 - math.pow(1 + monthly_rate, -month_count))
    total = installment * month_count
    interest = total - principal
    return (
        "ผลคำนวณค่างวดโดยประมาณ\n"
        f"ค่างวดต่อเดือน: {_money(installment)} บาท\n"
        f"ยอดชำระรวม: {_money(total)} บาท\n"
        f"ดอกเบี้ยรวม: {_money(interest)} บาท\n\n"
        "คำนวณแบบลดต้นลดดอก ผลจริงขึ้นอยู่กับหลักเกณฑ์ของสหกรณ์"
    )


def _debt_capacity(text: str) -> str:
    fields = _parse_fields(text)
    income = _required(fields, "รายได้ต่อเดือน", "รายได้", "income")
    expenses = _required(fields, "ค่าใช้จ่ายต่อเดือน", "ค่าใช้จ่าย", "expenses")
    existing_debt = _required(fields, "หนี้เดิมต่อเดือน", "หนี้เดิม", "existing debt")
    new_payment = _required(fields, "ค่างวดใหม่", "new payment")
    if income <= 0 or min(expenses, existing_debt, new_payment) < 0:
        raise MenuInputError("รายได้ต้องมากกว่า 0 และรายการค่าใช้จ่ายต้องไม่ติดลบ")

    total_debt = existing_debt + new_payment
    dsr = total_debt / income * 100
    remaining = income - expenses - total_debt
    if dsr <= 40 and remaining >= 0:
        assessment = "อยู่ในเกณฑ์เบื้องต้น"
    elif dsr <= 50 and remaining >= 0:
        assessment = "ควรพิจารณารายละเอียดเพิ่มเติม"
    else:
        assessment = "ภาระหนี้ค่อนข้างสูง"
    return (
        "ผลประเมินภาระหนี้เบื้องต้น\n"
        f"ภาระหนี้รวมต่อเดือน: {_money(total_debt)} บาท\n"
        f"สัดส่วนหนี้ต่อรายได้ (DSR): {dsr:.1f}%\n"
        f"เงินคงเหลือหลังหักรายการ: {_money(remaining)} บาท\n"
        f"ผลเบื้องต้น: {assessment}\n\n"
        "ผลนี้ไม่ใช่การอนุมัติสินเชื่อ ต้องตรวจสอบตามระเบียบสหกรณ์อีกครั้ง"
    )


def _dividend(text: str) -> str:
    fields = _parse_fields(text)
    average_shares = _required(
        fields,
        "ทุนเรือนหุ้นเฉลี่ย",
        "ทุนเรือนหุ้น",
        "shares",
    )
    rate = _required(fields, "อัตราปันผล", "ปันผล", "rate")
    if average_shares < 0 or rate < 0:
        raise MenuInputError("ทุนเรือนหุ้นและอัตราปันผลต้องไม่ติดลบ")
    dividend = average_shares * rate / 100
    return (
        "ผลคำนวณเงินปันผลโดยประมาณ\n"
        f"ทุนเรือนหุ้นเฉลี่ย: {_money(average_shares)} บาท\n"
        f"อัตราปันผล: {rate:g}%\n"
        f"เงินปันผล: {_money(dividend)} บาท\n\n"
        "ยอดจริงขึ้นอยู่กับมติจัดสรรกำไรและวิธีคิดของสหกรณ์"
    )


def _deposit_interest(text: str) -> str:
    fields = _parse_fields(text)
    principal = _required(fields, "เงินต้น", "principal")
    rate = _required(fields, "ดอกเบี้ยต่อปี", "ดอกเบี้ย", "rate")
    days = _required(fields, "จำนวนวัน", "วัน", "days")
    if principal < 0 or rate < 0 or days <= 0 or not days.is_integer():
        raise MenuInputError("จำนวนวันต้องเป็นจำนวนเต็มมากกว่า 0 และข้อมูลอื่นต้องไม่ติดลบ")
    interest = principal * rate / 100 * int(days) / 365
    return (
        "ผลคำนวณดอกเบี้ยเงินฝากโดยประมาณ\n"
        f"ระยะเวลา: {int(days):,} วัน\n"
        f"ดอกเบี้ย: {_money(interest)} บาท\n"
        f"ยอดรวม: {_money(principal + interest)} บาท\n\n"
        "คำนวณแบบดอกเบี้ยอย่างง่าย 365 วัน ยังไม่รวมภาษีหรือเงื่อนไขบัญชี"
    )


def _summary(text: str) -> str:
    values: list[float] = []
    for line in text.splitlines()[1:]:
        candidate = line.split(":", 1)[-1].strip()
        if not candidate:
            continue
        match = _NUMBER_PATTERN.search(candidate)
        if match:
            values.append(_to_number(match.group()))
    if not values:
        raise MenuInputError("กรุณากรอกจำนวนเงินอย่างน้อย 1 รายการ ทีละบรรทัด")
    total = sum(values)
    average = total / len(values)
    return (
        "ผลสรุปรายการ\n"
        f"จำนวนรายการ: {len(values):,}\n"
        f"ยอดรวม: {_money(total)} บาท\n"
        f"ค่าเฉลี่ย: {_money(average)} บาท\n"
        f"ค่าสูงสุด: {_money(max(values))} บาท\n"
        f"ค่าต่ำสุด: {_money(min(values))} บาท"
    )


def _parse_fields(text: str) -> dict[str, float]:
    fields: dict[str, float] = {}
    for line in text.splitlines()[1:]:
        if ":" not in line:
            continue
        key, raw_value = line.split(":", 1)
        match = _NUMBER_PATTERN.search(raw_value)
        if match:
            fields[_normalize_key(key)] = _to_number(match.group())
    return fields


def _required(fields: dict[str, float], *aliases: str) -> float:
    for alias in aliases:
        value = fields.get(_normalize_key(alias))
        if value is not None:
            return value
    raise MenuInputError(f"กรุณากรอก {aliases[0]}")


def _normalize_key(value: str) -> str:
    return re.sub(r"\s+", "", value.strip().lower())


def _to_number(value: str) -> float:
    return float(value.replace(",", ""))


def _money(value: float) -> str:
    return f"{value:,.2f}"
