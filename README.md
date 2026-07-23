# CoopWise AI — LINE Gateway (Phase 1)

บริการ FastAPI สำหรับรับ LINE webhook และส่งข้อความจาก CoopWise AI ผ่าน LINE
Messaging API โดยเน้นการแยก secret, ตรวจสอบลายเซ็น และไม่เปิด endpoint ภายในสู่
อินเทอร์เน็ตโดยตรง

## สิ่งที่มีใน Phase 1

- ตรวจสอบ `X-Line-Signature` จาก raw request body
- ส่งข้อความแบบ Text และ Flex
- ป้องกัน send endpoint ด้วย `X-API-Key`
- ใช้ `X-Line-Retry-Key` ค่าเดิมเมื่อ retry เพื่อลดความเสี่ยงข้อความซ้ำ
- Liveness และ readiness endpoints
- Docker Compose, Nginx และ systemd templates
- ตัวอย่าง Flex Message ที่ไม่แสดงข้อมูลการเงินอ่อนไหวใน notification
- ชุดทดสอบสำหรับ signature, routes และ LINE client

> LINE Bot MCP Server ถูกเก็บเป็น integration เสริมสำหรับ AI Agent ใน
> `config/line-bot-mcp.example.json` ไม่ได้อยู่บนเส้นทางหลักของ webhook หรือ scheduled
> notification เนื่องจากตัว MCP server ยังเป็น Preview

## เริ่มใช้งานในเครื่อง

ต้องมี Python 3.12 ขึ้นไป หรือ Docker

```bash
cp .env.example .env
```

แก้ `.env` โดยสร้าง `INTERNAL_API_KEY` แบบสุ่มอย่างน้อย 32 ตัวอักษร แล้วใส่ค่า LINE
จริง ห้าม commit ไฟล์นี้

### ใช้ Python

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

บน PowerShell ใช้:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

เปิด `http://127.0.0.1:8000/docs` ใน development

### ใช้ Docker

```bash
docker compose up --build
```

บริการจะรับเฉพาะที่ `127.0.0.1:8000` เพื่อให้ Nginx เป็น public entrypoint

## ตั้งค่า LINE Developers Console

1. เปิด Messaging API ของ LINE Official Account
2. ออก Channel Access Token และบันทึกใน `.env`
3. บันทึก Channel Secret ใน `.env`
4. ตั้ง Webhook URL เป็น `https://YOUR_DOMAIN/webhooks/line`
5. กด Verify และเปิด `Use webhook`

`userId` สำหรับ push message ควรมาจาก `source.userId` ของ webhook หรือกระบวนการ
เชื่อมบัญชีที่ได้รับความยินยอม ไม่ควรรับ ID ที่ผู้ใช้พิมพ์เอง

## เรียกส่งข้อความ

Text:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/messages/text \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_INTERNAL_API_KEY" \
  -d '{"user_id":"Uxxxxxxxx","text":"สวัสดีสมาชิก"}'
```

Flex:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/messages/flex \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_INTERNAL_API_KEY" \
  --data-binary @examples/flex-debt-reminder.json
```

ถ้าไม่ส่ง `user_id` ระบบจะใช้ `LINE_DEFAULT_DESTINATION_USER_ID`; หากไม่มีทั้งคู่จะตอบ
`422`

## Deploy บน Ubuntu VPS

1. ติดตั้ง Docker Engine, Docker Compose plugin, Nginx และ Certbot
2. วางโปรเจกต์ที่ `/opt/coopwise-ai-line`
3. สร้าง `/opt/coopwise-ai-line/.env` และจำกัดสิทธิ์เป็น `chmod 600`
4. ทดสอบด้วย `docker compose up -d --build`
5. เปลี่ยน `line.example.com` ใน `deploy/nginx/coopwise-ai-line.conf`
6. ขอ TLS certificate ด้วย Certbot แล้วติดตั้ง Nginx config
7. คัดลอก systemd unit:

```bash
sudo cp deploy/systemd/coopwise-ai-line.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now coopwise-ai-line
```

ตรวจสอบ:

```bash
docker compose ps
curl https://YOUR_DOMAIN/health/live
sudo journalctl -u coopwise-ai-line -n 100 --no-pager
```

Nginx template เปิดจากภายนอกเฉพาะ webhook และ liveness เท่านั้น ส่วน
`/api/v1/messages/*` ต้องเรียกผ่าน loopback หรือ private network

## ทดสอบและตรวจคุณภาพ

```bash
pytest
ruff check .
ruff format --check .
docker compose config
```

## ข้อกำหนดก่อน production

- เปลี่ยน placeholder ทุกค่าและปิด docs ด้วย `APP_DOCS_ENABLED=false`
- จำกัดผู้ที่เรียก send endpoint และหมุน API key ตามรอบ
- เก็บ mapping ระหว่างสมาชิกกับ LINE user ID แบบเข้ารหัส พร้อม consent/audit trail
- ไม่ใส่ยอดหนี้ เลขสมาชิก หรือข้อมูลส่วนบุคคลในข้อความแจ้งเตือนโดยไม่จำเป็น
- เพิ่ม persistent queue/outbox ก่อนใช้งานแจ้งเตือนจำนวนมาก
- สำรองและทดสอบขั้นตอน revoke/rotate Channel Access Token

