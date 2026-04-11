import requests

# 🔗 Your Google Sheet API
MENU_API = "https://opensheet.elk.sh/1HNU2ySZeqoSCZu3qHggLqGud4qbyPIlr12tj6xHNMnE/MENU"


# =========================
# SAFE INTEGER CONVERSION
# =========================
def safe_int(value):
    try:
        return int(value)
    except:
        return 0


# =========================
# FETCH MENU FROM GOOGLE SHEET
# =========================
def get_menu_data():
    response = requests.get(MENU_API)
    data = response.json()

    menu = {}

    for row in data:
        category = row.get("Category", "").strip()
        item = row.get("Item Name", "").strip()

        price = safe_int(row.get("Price"))
        discount = safe_int(row.get("Discount"))

        if not category or not item:
            continue

        if category not in menu:
            menu[category] = []

        menu[category].append({
            "item": item,
            "price": price,
            "discount": discount
        })

    return menu


# =========================
# FORMAT CATEGORY LIST
# =========================
def format_categories(menu):
    categories = list(menu.keys())

    text = "📋 *Menu Categories*\n\n"

    for i, cat in enumerate(categories, start=1):
        text += f"{i}. {cat}\n"

    text += "\n👉 Reply with number or category name"

    return text, categories


# =========================
# FORMAT ITEMS (WITH DISCOUNT)
# =========================
def format_items(menu, selected_category):
    items = menu.get(selected_category)

    if not items:
        return "❌ Category not found.\n\nType MENU to go back."

    text = f"🍽 *{selected_category}*\n\n"

    for i, item in enumerate(items, start=1):
        price = item["price"]
        discount = item["discount"]

        if discount > 0:
            original = price + discount
            text += f"{i}. {item['item']} - ₹{price} (₹{original})\n"
        else:
            text += f"{i}. {item['item']} - ₹{price}\n"

    text += "\n🔙 Type BACK or MENU"

    return text
