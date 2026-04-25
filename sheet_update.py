import os
import json
import gspread
from datetime import datetime
from google.oauth2.service_account import Credentials


# =========================
# 🔐 CONNECT TO GOOGLE SHEET
# =========================
def connect_sheet():
    try:
        creds_json = os.getenv("GOOGLE_CREDS_JSON")

        if not creds_json:
            print("❌ GOOGLE_CREDS_JSON not found")
            return None

        creds_dict = json.loads(creds_json)

        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)

        client = gspread.authorize(creds)

        sheet = client.open("ORDER").sheet1

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
