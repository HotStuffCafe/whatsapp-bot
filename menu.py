import requests

# =========================
# GOOGLE SHEET CONFIG
# =========================
SHEET_URL = "https://opensheet.elk.sh/1HNU2ySZeqoSCZu3qHggLqGud4qbyPIlr12tj6xHNMnE/MENU"


# =========================
# LOAD MENU FROM SHEET
# =========================
def get_menu_data():
    try:
        response = requests.get(SHEET_URL)
        data = response.json()

        menu = {}

        for row in data:
            category = row.get("Category", "").strip()
            item = row.get("Item Name", "").strip()
            price = float(row.get("Price", 0))

            if not category or not item:
                continue

            if category not in menu:
                menu[category] = []

            menu[category].append({
                "item": item,
                "price": price
            })

        return menu

    except Exception as e:
        print("Menu Load Error:", e)
        return {}


# =========================
# FORMAT CATEGORY LIST
# =========================
def format_categories(menu):

    text = "📋 *Menu Categories*\n\n"
    categories = list(menu.keys())

    for i, cat in enumerate(categories, 1):
        text += f"{i}. {cat}\n"

    text += "\n👉 Reply with *number* or *category name*"
    text += "\n👉 To see all items, type *all items*"

    return text, categories


# =========================
# FORMAT ITEMS (SUB MENU)
# =========================
def format_items(menu, category):

    if category not in menu:
        return "❌ Category not found."

    text = f"🍽 {category}\n\n"

    items = menu[category]

    for i, item in enumerate(items, 1):
        text += f"{i}. {item['item']} - ₹{int(item['price'])}\n"

    text += "\n👉 Type *back* or *menu* to go to main menu"
    text += "\n👉 To see all items, type *all items*"
    text += "\n👉 To order, type: *add* 2 chai, 1 cold coffee"

    return text


# =========================
# FORMAT ALL ITEMS
# =========================
def format_all_items(menu):

    text = "📦 *All Menu Items*\n\n"

    count = 1

    for category, items in menu.items():
        for item in items:
            text += f"{count}. {category} | {item['item']} | ₹{int(item['price'])}\n"
            count += 1

    text += "\n👉 Type *menu* to go back"
    text += "\n👉 To order, type: *add* 2 chai, 1 cold coffee"

    return text
