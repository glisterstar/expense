from collections import defaultdict
from datetime import datetime
from sheets_manager import get_monthly_data, update_monthly_summary


def generate_monthly_report(year: int = None, month: int = None) -> str:
    """Generate monthly expense summary report as formatted text."""
    now = datetime.now()
    if year is None:
        year = now.year
    if month is None:
        month = now.month

    data = get_monthly_data(year, month)

    if not data:
        return f"ไม่มีข้อมูลค่าใช้จ่ายเดือน {month:02d}/{year}"

    # Aggregate by category
    by_category = defaultdict(lambda: {"total": 0.0, "count": 0})
    by_channel = defaultdict(lambda: {"total": 0.0, "count": 0})
    all_items = []

    for row in data:
        total = float(row.get("รวม", 0) or 0)
        category = row.get("หมวดหมู่", "อื่นๆ") or "อื่นๆ"
        channel = row.get("ช่องทาง", "อื่นๆ") or "อื่นๆ"
        item_name = row.get("สินค้า", "")

        by_category[category]["total"] += total
        by_category[category]["count"] += 1
        by_channel[channel]["total"] += total
        by_channel[channel]["count"] += 1
        all_items.append({"name": item_name, "total": total})

    grand_total = sum(v["total"] for v in by_category.values())
    total_items = sum(v["count"] for v in by_category.values())

    # Update summary sheet
    summary_data = [
        {"category": cat, "total": info["total"], "count": info["count"]}
        for cat, info in sorted(by_category.items(), key=lambda x: x[1]["total"], reverse=True)
    ]
    update_monthly_summary(year, month, summary_data)

    # Build report text
    thai_months = [
        "", "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน",
        "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม",
        "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม",
    ]
    month_name = thai_months[month] if 1 <= month <= 12 else str(month)

    lines = [
        f"{'='*30}",
        f"  สรุปค่าใช้จ่าย {month_name} {year}",
        f"{'='*30}",
        f"  ยอดรวมทั้งหมด: {grand_total:,.2f} บาท",
        f"  จำนวนรายการ: {total_items} รายการ",
        "",
        "--- แยกตามหมวดหมู่ ---",
    ]

    for cat, info in sorted(by_category.items(), key=lambda x: x[1]["total"], reverse=True):
        pct = (info["total"] / grand_total * 100) if grand_total > 0 else 0
        lines.append(f"  {cat}: {info['total']:,.2f} บาท ({info['count']} รายการ, {pct:.1f}%)")

    lines.append("")
    lines.append("--- แยกตามช่องทาง ---")
    for ch, info in sorted(by_channel.items(), key=lambda x: x[1]["total"], reverse=True):
        lines.append(f"  {ch}: {info['total']:,.2f} บาท ({info['count']} รายการ)")

    # Top 5 expensive items
    top_items = sorted(all_items, key=lambda x: x["total"], reverse=True)[:5]
    if top_items:
        lines.append("")
        lines.append("--- Top 5 ค่าใช้จ่ายสูงสุด ---")
        for i, item in enumerate(top_items, 1):
            lines.append(f"  {i}. {item['name']}: {item['total']:,.2f} บาท")

    lines.append(f"\n{'='*30}")

    return "\n".join(lines)
