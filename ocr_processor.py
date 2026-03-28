import re
from datetime import datetime
from google.cloud import vision
from config import CATEGORY_KEYWORDS, CHANNEL_KEYWORDS


def extract_text_from_image(image_bytes: bytes) -> str:
    """Use Google Vision API to extract text from receipt image."""
    client = vision.ImageAnnotatorClient()
    image = vision.Image(content=image_bytes)
    response = client.text_detection(image=image)

    if response.error.message:
        raise Exception(f"Vision API error: {response.error.message}")

    texts = response.text_annotations
    if not texts:
        return ""

    return texts[0].description


def parse_receipt(text: str) -> dict:
    """Parse extracted text into structured expense data."""
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    result = {
        "date": _extract_date(lines, text),
        "store": _extract_store(lines, text),
        "items": _extract_items(lines),
        "total": _extract_total(lines),
        "channel": _detect_channel(text),
    }

    # Categorize items
    for item in result["items"]:
        item["category"] = categorize_item(item["name"])

    return result


def _extract_date(lines: list, full_text: str) -> str:
    """Extract date from receipt text, supporting multiple formats."""
    patterns = [
        # DD/MM/YYYY or DD-MM-YYYY
        r"(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})",
        # YYYY-MM-DD
        r"(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})",
        # DD/MM/YY
        r"(\d{1,2})[/\-](\d{1,2})[/\-](\d{2})\b",
        # Thai date: 28 มี.ค. 2569
        r"(\d{1,2})\s*(ม\.ค\.|ก\.พ\.|มี\.ค\.|เม\.ย\.|พ\.ค\.|มิ\.ย\.|ก\.ค\.|ส\.ค\.|ก\.ย\.|ต\.ค\.|พ\.ย\.|ธ\.ค\.)\s*(\d{4})",
    ]

    thai_months = {
        "ม.ค.": 1, "ก.พ.": 2, "มี.ค.": 3, "เม.ย.": 4,
        "พ.ค.": 5, "มิ.ย.": 6, "ก.ค.": 7, "ส.ค.": 8,
        "ก.ย.": 9, "ต.ค.": 10, "พ.ย.": 11, "ธ.ค.": 12,
    }

    for line in lines:
        # DD/MM/YYYY
        match = re.search(patterns[0], line)
        if match:
            day, month, year = match.groups()
            year_int = int(year)
            if year_int > 2500:
                year_int -= 543
            return f"{int(day):02d}/{int(month):02d}/{year_int}"

        # YYYY-MM-DD
        match = re.search(patterns[1], line)
        if match:
            year, month, day = match.groups()
            year_int = int(year)
            if year_int > 2500:
                year_int -= 543
            return f"{int(day):02d}/{int(month):02d}/{year_int}"

        # DD/MM/YY
        match = re.search(patterns[2], line)
        if match:
            day, month, year = match.groups()
            year_int = int(year)
            if year_int < 100:
                year_int += 2000 if year_int < 70 else 1900
            return f"{int(day):02d}/{int(month):02d}/{year_int}"

        # Thai date
        match = re.search(patterns[3], line)
        if match:
            day, thai_month, year = match.groups()
            year_int = int(year)
            if year_int > 2500:
                year_int -= 543
            month_num = thai_months.get(thai_month, 1)
            return f"{int(day):02d}/{month_num:02d}/{year_int}"

    return datetime.now().strftime("%d/%m/%Y")


def _extract_store(lines: list, full_text: str) -> str:
    """Extract store name - usually in first few lines."""
    # Check known channels first
    for channel, keywords in CHANNEL_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in full_text.lower():
                return channel

    # First non-date, non-numeric meaningful line is likely the store
    for line in lines[:5]:
        if len(line) > 2 and not re.match(r"^[\d/\-.:]+$", line):
            cleaned = line.strip()
            if cleaned and not any(
                skip in cleaned.lower()
                for skip in ["receipt", "ใบเสร็จ", "tax invoice", "ใบกำกับภาษี"]
            ):
                return cleaned

    return "ไม่ระบุ"


def _extract_items(lines: list) -> list:
    """Extract item name, quantity, and price from receipt lines."""
    items = []

    # Pattern: item_name quantity x price or item_name price
    item_patterns = [
        # "สินค้า 2 x 50.00" or "สินค้า 2x50"
        r"(.+?)\s+(\d+)\s*[xX×]\s*([\d,]+\.?\d*)",
        # "สินค้า   50.00   2   100.00" (name, unit_price, qty, total)
        r"(.+?)\s+([\d,]+\.?\d*)\s+(\d+)\s+([\d,]+\.?\d*)",
        # "สินค้า   2   100.00" (name, qty, total)
        r"(.+?)\s+(\d+)\s+([\d,]+\.?\d+)",
        # "สินค้า   100.00" (name, price - qty=1)
        r"(.+?)\s{2,}([\d,]+\.?\d+)$",
    ]

    skip_keywords = [
        "total", "รวม", "ส่วนลด", "discount", "vat", "ภาษี",
        "เงินทอน", "change", "cash", "เงินสด", "credit",
        "บัตร", "card", "สุทธิ", "net", "จำนวน", "qty",
        "ราคา", "price", "receipt", "ใบเสร็จ", "thank",
        "ขอบคุณ", "tel", "โทร", "tax",
    ]

    for line in lines:
        line_lower = line.lower().strip()

        if any(kw in line_lower for kw in skip_keywords):
            continue

        if len(line_lower) < 3:
            continue

        for i, pattern in enumerate(item_patterns):
            match = re.match(pattern, line.strip())
            if match:
                groups = match.groups()
                name = groups[0].strip()

                if len(name) < 2 or name.replace(".", "").replace(",", "").isdigit():
                    continue

                if i == 0:  # qty x price
                    qty = int(groups[1])
                    price = float(groups[2].replace(",", ""))
                elif i == 1:  # name, unit_price, qty, total
                    qty = int(groups[2])
                    price = float(groups[1].replace(",", ""))
                elif i == 2:  # name, qty, total
                    qty = int(groups[1])
                    total = float(groups[2].replace(",", ""))
                    price = total / qty if qty > 0 else total
                else:  # name, price only
                    qty = 1
                    price = float(groups[1].replace(",", ""))

                items.append({
                    "name": name,
                    "price": price,
                    "quantity": qty,
                    "total": price * qty,
                    "category": "",
                })
                break

    return items


def _extract_total(lines: list) -> float:
    """Extract total amount from receipt."""
    total_patterns = [
        r"(?:รวม|total|สุทธิ|net|ยอด|amount)[:\s]*([\d,]+\.?\d*)",
        r"([\d,]+\.?\d*)\s*(?:บาท|baht|thb)",
    ]

    candidates = []
    for line in lines:
        for pattern in total_patterns:
            match = re.search(pattern, line.lower())
            if match:
                amount = float(match.group(1).replace(",", ""))
                candidates.append(amount)

    return max(candidates) if candidates else 0.0


def _detect_channel(text: str) -> str:
    """Detect purchase channel from receipt text."""
    text_lower = text.lower()
    for channel, keywords in CHANNEL_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text_lower:
                return channel
    return "อื่นๆ"


def categorize_item(item_name: str) -> str:
    """Auto-categorize item based on keywords."""
    name_lower = item_name.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in name_lower:
                return category
    return "อื่นๆ"
