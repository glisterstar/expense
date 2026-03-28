# Expense Tracker LINE Bot

ระบบบันทึกค่าใช้จ่ายผ่าน LINE Bot - รับรูปสลิป/บิล/Shopee อ่านด้วย OCR แล้วบันทึกลง Google Sheets

## สิ่งที่ต้องเตรียม

### 1. LINE Bot
1. ไปที่ [LINE Developers Console](https://developers.line.biz/)
2. สร้าง Provider + Channel (Messaging API)
3. เปิด **Webhook** ใส่ URL: `https://your-domain.com/webhook`
4. คัดลอก **Channel Secret** และ **Channel Access Token**

### 2. Google Cloud
1. ไปที่ [Google Cloud Console](https://console.cloud.google.com/)
2. สร้าง Project ใหม่
3. เปิด API:
   - **Cloud Vision API**
   - **Google Sheets API**
   - **Google Drive API**
4. สร้าง **Service Account** → ดาวน์โหลด JSON key เป็น `credentials.json`
5. สร้าง Google Sheet ใหม่ → คัดลอก Sheet ID จาก URL
6. แชร์ Google Sheet ให้ email ของ Service Account (Editor)

### 3. ตั้งค่า Environment

```bash
cp .env.example .env
```

แก้ไขค่าใน `.env`:
```
LINE_CHANNEL_SECRET=xxx
LINE_CHANNEL_ACCESS_TOKEN=xxx
GOOGLE_CREDENTIALS_PATH=credentials.json
GOOGLE_SHEET_ID=xxx
```

## ติดตั้งและรัน

```bash
# ติดตั้ง dependencies
pip install -r requirements.txt

# รันเซิร์ฟเวอร์
python app.py

# ทดสอบ local ด้วย ngrok
ngrok http 8000
```

## วิธีใช้งาน

### ส่งรูปสลิป/บิล
ส่งรูปภาพสลิป QR code, บิลร้านค้า, หรือ screenshot Shopee เข้ากลุ่มไลน์
Bot จะอ่านข้อมูลอัตโนมัติแล้วบันทึกลง Google Sheets

### คำสั่ง
| คำสั่ง | ผล |
|--------|-----|
| ส่งรูปสลิป/บิล | อ่าน OCR + บันทึกอัตโนมัติ |
| `/summary` | สรุปค่าใช้จ่ายเดือนนี้ |
| `/report 03/2026` | สรุปเดือนที่ระบุ |
| `/manual ร้าน\|สินค้า\|ราคา\|จำนวน` | บันทึกมือ |
| `/help` | แสดงคำสั่งทั้งหมด |

### ตัวอย่างบันทึกมือ
```
/manual 7-11|น้ำดื่ม|7|2
/manual โลตัส|ไข่ไก่|55|1
```

## โครงสร้าง Google Sheets

### Sheet "รายการ"
| วันที่ | ร้านค้า | สินค้า | ราคา | จำนวน | รวม | หมวดหมู่ | ช่องทาง | หมายเหตุ |
|--------|---------|--------|------|-------|-----|----------|---------|----------|

### Sheet "สรุปรายเดือน"
| เดือน | หมวดหมู่ | ยอดรวม | จำนวนรายการ |
|-------|----------|--------|-------------|

## หมวดหมู่อัตโนมัติ
- อาหาร, เครื่องดื่ม, ของใช้, เดินทาง, สุขภาพ, ช้อปปิ้ง, อื่นๆ

## ช่องทางที่รองรับ
- Shopee, Lazada, 7-Eleven, Lotus's, Big C, Makro, Tops, Grab, LINE Man, Foodpanda

## Deploy (Production)

แนะนำ deploy บน:
- **Google Cloud Run** (ฟรี tier เพียงพอ)
- **Railway.app**
- **Render.com**

ตั้งค่า environment variables บน platform ที่เลือก แทนการใช้ .env file
