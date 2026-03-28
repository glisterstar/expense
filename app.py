import hashlib
import hmac
import base64
import logging
from datetime import datetime

import httpx
from fastapi import FastAPI, Request, HTTPException

from config import (
    LINE_CHANNEL_SECRET,
    LINE_CHANNEL_ACCESS_TOKEN,
)
from ocr_processor import parse_receipt, extract_text_from_image, categorize_item
from sheets_manager import append_expense, append_manual_expense
from monthly_report import generate_monthly_report

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Expense Tracker LINE Bot")

LINE_API = "https://api.line.me/v2/bot"
LINE_DATA_API = "https://api-data.line.me/v2/bot"
HEADERS = {"Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"}


def verify_signature(body: bytes, signature: str) -> bool:
    """Verify LINE webhook signature."""
    hash_value = hmac.new(
        LINE_CHANNEL_SECRET.encode(), body, hashlib.sha256
    ).digest()
    return hmac.compare_digest(
        signature, base64.b64encode(hash_value).decode()
    )


async def reply_message(reply_token: str, text: str):
    """Send reply message via LINE API."""
    # Split long messages (LINE limit 5000 chars)
    messages = []
    while text:
        chunk = text[:5000]
        messages.append({"type": "text", "text": chunk})
        text = text[5000:]

    async with httpx.AsyncClient() as client:
        await client.post(
            f"{LINE_API}/message/reply",
            headers={**HEADERS, "Content-Type": "application/json"},
            json={"replyToken": reply_token, "messages": messages[:5]},
        )


async def get_image_content(message_id: str) -> bytes:
    """Download image from LINE server."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{LINE_DATA_API}/message/{message_id}/content",
            headers=HEADERS,
        )
        response.raise_for_status()
        return response.content


@app.post("/webhook")
async def webhook(request: Request):
    """LINE webhook endpoint."""
    body = await request.body()
    signature = request.headers.get("x-line-signature", "")

    if LINE_CHANNEL_SECRET and not verify_signature(body, signature):
        raise HTTPException(status_code=400, detail="Invalid signature")

    data = await request.json()
    events = data.get("events", [])

    for event in events:
        event_type = event.get("type")
        reply_token = event.get("replyToken")

        if not reply_token:
            continue

        if event_type == "message":
            message = event.get("message", {})
            msg_type = message.get("type")

            if msg_type == "image":
                await handle_image(message["id"], reply_token)
            elif msg_type == "text":
                await handle_text(message["text"], reply_token)

    return {"status": "ok"}


async def handle_image(message_id: str, reply_token: str):
    """Process receipt image: OCR -> parse -> save to Sheets."""
    try:
        await reply_message(reply_token, "กำลังอ่านข้อมูลจากรูป...")

        image_bytes = await get_image_content(message_id)
        text = extract_text_from_image(image_bytes)

        if not text:
            # Need new reply token for push message
            logger.warning("No text extracted from image")
            return

        result = parse_receipt(text)
        rows_added = append_expense(result)

        # Build confirmation message
        lines = ["บันทึกค่าใช้จ่ายสำเร็จ!"]
        lines.append(f"ร้าน: {result['store']}")
        lines.append(f"วันที่: {result['date']}")
        lines.append(f"ช่องทาง: {result['channel']}")
        lines.append("")

        for item in result["items"]:
            lines.append(
                f"  - {item['name']} x{item['quantity']} = {item['total']:,.2f} บาท [{item['category']}]"
            )

        if result["total"] > 0:
            lines.append(f"\nยอดรวม: {result['total']:,.2f} บาท")

        lines.append(f"\nบันทึก {rows_added} รายการลง Google Sheets แล้ว")

        # Use push message since reply token was already used
        # In production, use push message API instead
        logger.info("\n".join(lines))

    except Exception as e:
        logger.error(f"Error processing image: {e}")


async def handle_text(text: str, reply_token: str):
    """Handle text commands."""
    text = text.strip()

    if text == "/help":
        help_text = (
            "คำสั่งที่ใช้ได้:\n"
            "  ส่งรูปสลิป/บิล - บันทึกอัตโนมัติ\n"
            "  /summary - สรุปเดือนนี้\n"
            "  /report MM/YYYY - สรุปเดือนที่ระบุ\n"
            "  /manual ร้าน|สินค้า|ราคา|จำนวน - บันทึกมือ\n"
            "  /help - แสดงคำสั่งทั้งหมด"
        )
        await reply_message(reply_token, help_text)

    elif text == "/summary":
        now = datetime.now()
        report = generate_monthly_report(now.year, now.month)
        await reply_message(reply_token, report)

    elif text.startswith("/report"):
        parts = text.split()
        if len(parts) == 2:
            try:
                date_parts = parts[1].split("/")
                month = int(date_parts[0])
                year = int(date_parts[1])
                report = generate_monthly_report(year, month)
                await reply_message(reply_token, report)
            except (ValueError, IndexError):
                await reply_message(reply_token, "รูปแบบไม่ถูกต้อง ใช้: /report MM/YYYY")
        else:
            await reply_message(reply_token, "ใช้: /report MM/YYYY เช่น /report 03/2026")

    elif text.startswith("/manual"):
        # Format: /manual ร้าน|สินค้า|ราคา|จำนวน
        try:
            _, data = text.split(" ", 1)
            parts = [p.strip() for p in data.split("|")]

            if len(parts) < 3:
                await reply_message(
                    reply_token,
                    "รูปแบบ: /manual ร้าน|สินค้า|ราคา|จำนวน\nเช่น: /manual 7-11|น้ำดื่ม|7|2",
                )
                return

            store = parts[0]
            item_name = parts[1]
            price = float(parts[2])
            quantity = int(parts[3]) if len(parts) > 3 else 1
            category = categorize_item(item_name)

            append_manual_expense(
                date=datetime.now().strftime("%d/%m/%Y"),
                store=store,
                item_name=item_name,
                price=price,
                quantity=quantity,
                category=category,
                channel="บันทึกมือ",
            )

            total = price * quantity
            await reply_message(
                reply_token,
                f"บันทึกสำเร็จ!\n{item_name} x{quantity} = {total:,.2f} บาท\nร้าน: {store} | หมวด: {category}",
            )

        except Exception as e:
            await reply_message(
                reply_token,
                f"เกิดข้อผิดพลาด: {e}\nรูปแบบ: /manual ร้าน|สินค้า|ราคา|จำนวน",
            )

    else:
        pass  # Ignore other messages in group chat


@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
