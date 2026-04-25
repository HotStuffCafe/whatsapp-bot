import os
import json
import base64
import gspread
from datetime import datetime
from google.oauth2.service_account import Credentials


# =========================
# 🔐 CONNECT TO GOOGLE SHEET
# =========================
def connect_sheet():
    try:
        creds_json = os.getenv("GOOGLE_CREDS_JSON")
        creds_path = os.getenv("GOOGLE_CREDS_FILE") or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        sheet_name = os.getenv("ORDER_SHEET_NAME", "ORDER")
        worksheet_name = os.getenv("ORDER_WORKSHEET", "ORDER")
        sheet_id = os.getenv("ORDER_SHEET_ID")

        creds_dict = None

        if creds_json:
            try:
                creds_dict = json.loads(creds_json)
            except json.JSONDecodeError:
                decoded = base64.b64decode(creds_json).decode("utf-8")
                creds_dict = json.loads(decoded)
        elif creds_path and os.path.exists(creds_path):
            with open(creds_path, "r", encoding="utf-8") as f:
                creds_dict = json.load(f)
        else:
            print("❌ GOOGLE_CREDS_JSON / GOOGLE_CREDS_FILE not found")
            return None

        if "private_key" in creds_dict:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)

        client = gspread.authorize(creds)
        if sheet_id:
            spreadsheet = client.open_by_key(sheet_id)
        else:
            spreadsheet = client.open(sheet_name)

        try:
            sheet = spreadsheet.worksheet(worksheet_name)
        except Exception:
            sheet = spreadsheet.add_worksheet(title=worksheet_name, rows=2000, cols=20)
            sheet.append_row([
                "today",
                "order_id",
                "phone",
                "item_name",
                "qty",
                "price",
                "total",
                "address",
                "payment_mode",
                "payment_status"
            ])

        print("✅ Google Sheet Connected")

        return sheet

    except Exception as e:
        print("❌ Sheet connection error:", str(e))
        return None


# =========================
# 🧾 UPDATE ORDER IN SHEET
# =========================
def update_google_sheet(session, order_id, payment_mode, payment_status):
    sheet = connect_sheet()

    if not sheet:
        print("❌ Sheet not available")
        return

    try:
        cart = session.get("cart", {})
        address = session.get("address", "")
        phone = session.get("user_number", "")

        today = datetime.now().strftime("%d-%m-%Y")

        for item_name, data in cart.items():
            qty = data.get("qty", 0)
            price = data.get("price", get_item_price(session.get("menu"), item_name))
            total = price * qty

            row = [
                today,
                order_id,
                phone,
                item_name,
                qty,
                price,
                total,
                address,
                payment_mode,
                payment_status
            ]

            sheet.append_row(row)

        print("✅ Order pushed to sheet")

    except Exception as e:
        print("❌ Sheet update error:", str(e))


def mark_order_payment_success(order_id, payment_mode=None):
    sheet = connect_sheet()

    if not sheet:
        print("❌ Sheet not available for payment status update")
        return False

    try:
        rows = sheet.get_all_values()
        updated = 0

        for i, row in enumerate(rows[1:], start=2):  # skip header
            if len(row) < 10:
                continue

            row_order_id = row[1].strip()
            row_payment_mode = row[8].strip().upper() if len(row) > 8 else ""
            mode_matches = True if payment_mode is None else row_payment_mode == payment_mode.upper()

            if row_order_id == order_id and mode_matches:
                sheet.update_cell(i, 9, "UPI")
                sheet.update_cell(i, 10, "Success")
                updated += 1

        print(f"✅ Updated payment status to Success for {updated} row(s) of order {order_id}")
        return updated > 0

    except Exception as e:
        print("❌ Payment status update error:", str(e))
        return False


# =========================
# 🔍 GET PRICE
# =========================
def get_item_price(menu, item_name):
    if not menu:
        return 0

    for category in menu:
        for item in menu[category]:
            if item["item"].lower() == item_name.lower():
                return item["price"]
    return 0


# =========================
# 🧪 TEST CONNECTION
# =========================
def test_connection():
    sheet = connect_sheet()

    if sheet:
        return "✅ Google Sheet Connected"
    else:
        return "❌ Connection Failed"
