import gspread
from oauth2client.service_account import ServiceAccountCredentials

# =========================
# GOOGLE SHEETS CONNECTION
# =========================
def get_menu_data():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = ServiceAccountCredentials.from_json_keyfile_name(
        "credentials.json", scope
    )

    client = gspread.authorize(creds)

    # 🔁 Change "Menu" to your actual sheet name
    sheet = client.open("Menu").sheet1

    records = sheet.get_all_records()

    menu = {}

    for row in records:
        category = row["Category"]
        item = row["Item Name"]
        price = row["Price"]

        if category not in menu:
            menu[category] = []

        menu[category].append({
            "item": item,
            "price": price
        })

    return menu


# =========================
# FORMAT CATEGORY LIST
# =========================
def format_categories(menu):
    categories = list(menu.keys())

    text = "🍽 *HotStuffCafe Menu*\n\n"

    for i, cat in enumerate(categories, start=1):
        text += f"{i}. {cat}\n"

    text += "\nReply with number or category name."

    return text, categories


# =========================
# FORMAT ITEMS IN CATEGORY
# =========================
def format_items(menu, selected_category):
    items = menu[selected_category]

    text = f"🍽 *{selected_category}*\n\n"

    for i, item in enumerate(items, start=1):
        text += f"{i}. {item['item']} - ₹{item['price']}\n"

    text += "\nType item name to order."

    return text
