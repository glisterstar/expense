import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from config import GOOGLE_CREDENTIALS_PATH, GOOGLE_SHEET_ID, SHEET_EXPENSES, SHEET_MONTHLY

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

_client = None


def _get_client() -> gspread.Client:
    """Get or create authenticated gspread client."""
    global _client
    if _client is None:
        creds = Credentials.from_service_account_file(
            GOOGLE_CREDENTIALS_PATH, scopes=SCOPES
        )
        _client = gspread.authorize(creds)
    return _client


def _get_sheet(sheet_name: str) -> gspread.Worksheet:
    """Get worksheet by name, create if not exists."""
    client = _get_client()
    spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)

    try:
        return spreadsheet.worksheet(sheet_name)
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=10)
        if sheet_name == SHEET_EXPENSES:
            worksheet.append_row([
                "วันที่", "ร้านค้า", "สินค้า", "ราคา", "จำนวน",
                "รวม", "หมวดหมู่", "ช่องทาง", "หมายเหตุ",
            ])
            worksheet.format("A1:I1", {
                "textFormat": {"bold": True},
                "backgroundColor": {"red": 0.2, "green": 0.6, "blue": 0.9},
            })
        elif sheet_name == SHEET_MONTHLY:
            worksheet.append_row([
                "เดือน", "หมวดหมู่", "ยอดรวม", "จำนวนรายการ",
            ])
            worksheet.format("A1:D1", {
                "textFormat": {"bold": True},
                "backgroundColor": {"red": 0.9, "green": 0.7, "blue": 0.2},
            })
        return worksheet


def append_expense(data: dict) -> int:
    """Append expense items to the sheet. Returns number of rows added."""
    sheet = _get_sheet(SHEET_EXPENSES)

    rows_added = 0
    for item in data.get("items", []):
        row = [
            data.get("date", datetime.now().strftime("%d/%m/%Y")),
            data.get("store", "ไม่ระบุ"),
            item.get("name", ""),
            item.get("price", 0),
            item.get("quantity", 1),
            item.get("total", item.get("price", 0) * item.get("quantity", 1)),
            item.get("category", "อื่นๆ"),
            data.get("channel", "อื่นๆ"),
            data.get("note", ""),
        ]
        sheet.append_row(row, value_input_option="USER_ENTERED")
        rows_added += 1

    return rows_added


def append_manual_expense(
    date: str, store: str, item_name: str,
    price: float, quantity: int, category: str, channel: str,
) -> None:
    """Manually add a single expense row."""
    sheet = _get_sheet(SHEET_EXPENSES)
    row = [
        date, store, item_name, price, quantity,
        price * quantity, category, channel, "บันทึกมือ",
    ]
    sheet.append_row(row, value_input_option="USER_ENTERED")


def get_monthly_data(year: int, month: int) -> list[dict]:
    """Get all expenses for a specific month."""
    sheet = _get_sheet(SHEET_EXPENSES)
    all_rows = sheet.get_all_records()

    monthly_data = []
    for row in all_rows:
        try:
            date_str = str(row.get("วันที่", ""))
            if not date_str:
                continue
            parts = date_str.split("/")
            if len(parts) == 3:
                row_month = int(parts[1])
                row_year = int(parts[2])
                if row_month == month and row_year == year:
                    monthly_data.append(row)
        except (ValueError, IndexError):
            continue

    return monthly_data


def get_all_expenses() -> list[dict]:
    """Get all expense records."""
    sheet = _get_sheet(SHEET_EXPENSES)
    return sheet.get_all_records()


def update_monthly_summary(year: int, month: int, summary: list[dict]) -> None:
    """Update monthly summary sheet."""
    sheet = _get_sheet(SHEET_MONTHLY)
    month_str = f"{month:02d}/{year}"

    # Remove old rows for this month
    all_rows = sheet.get_all_values()
    rows_to_delete = []
    for i, row in enumerate(all_rows):
        if i == 0:
            continue
        if row and row[0] == month_str:
            rows_to_delete.append(i + 1)

    for row_idx in reversed(rows_to_delete):
        sheet.delete_rows(row_idx)

    # Add new summary rows
    for entry in summary:
        sheet.append_row([
            month_str,
            entry["category"],
            entry["total"],
            entry["count"],
        ], value_input_option="USER_ENTERED")
