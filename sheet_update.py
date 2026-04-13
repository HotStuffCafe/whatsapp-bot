import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime


# =========================
# CONNECT TO GOOGLE SHEET
# =========================
def connect_sheet():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = ServiceAccountCredentials.from_json_keyfile_name(
        "service_account.json", scope
    )

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

        # Get price from menu
        for category in menu.values():
            for item in category:
                if item["item"].lower() == name.lower():
                    price = item["price"]

        total = price * qty

        row = [
            date,                  # Date
            order_id,              # Order ID
            user_number,           # Customer Mobile
            name,                  # Item Name
            qty,                   # Quantity
            price,                 # Per item cost
            total,                 # Total
            order.get("address"),  # Address
            payment_mode,          # Payment Mode
            payment_status         # Payment Status
        ]

        rows.append(row)

    # Bulk insert (faster)
    sheet.append_rows(rows)

    return True
