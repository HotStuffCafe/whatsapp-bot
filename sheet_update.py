import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime


# =========================
# CONNECT TO GOOGLE SHEET
# =========================
def connect_sheet():
    creds_json = os.getenv("GOOGLE_CREDS_JSON")

    if not creds_json:
        raise Exception("❌ GOOGLE_CREDS_JSON not found in environment")

    try:
        creds_dict = json.loads(creds_json)
    except Exception as e:
        raise Exception(f"❌ Invalid JSON in GOOGLE_CREDS_JSON: {str(e)}")

    # 🔥 FIX PRIVATE KEY FORMAT (VERY IMPORTANT)
    if "private_key" in creds_dict:
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)

    client = gspread.authorize(creds)

    sheet = client.open_by_key("1HNU2ySZeqoSCZu3qHggLqGud4qbyPIlr12tj6xHNMnE")
    return sheet.worksheet("ORDER")


# =========================
# SAVE ORDER (LINE-WISE)
# =========================
def save_order_to_sheet(order_id, order, user_number, menu, payment_mode="COD", payment_status="na"):

    sheet = connect_sheet()

    date = datetime.now().strftime("%d-%m-%Y")

    rows = []

    for order_item in order["items"]:
        name = order_item["name"]
        qty = order_item["quantity"]

        price = 0

        # Fetch price from menu
        for category in menu.values():
            for item in category:
                if item["item"].lower() == name.lower():
                    price = item["price"]

        total = price * qty

        row = [
            date,                   # Date
            order_id,               # Order ID
            user_number,            # Customer Mobile Number
            name,                   # Item Name
            qty,                    # Quantity
            price,                  # Per item cost
            total,                  # Total
            order.get("address"),   # Address
            payment_mode,           # Payment Mode
            payment_status          # Payment Status
        ]

        rows.append(row)

    # Bulk insert rows
    sheet.append_rows(rows)

    return True


# =========================
# OPTIONAL TEST FUNCTION
# =========================
def test_connection():
    try:
        sheet = connect_sheet()
        sheet.append_row(["TEST", "CONNECTED"])
        return "✅ Google Sheet Connected"
    except Exception as e:
        return f"❌ Error: {str(e)}"
