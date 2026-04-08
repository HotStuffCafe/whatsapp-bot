def get_menu_data():
    menu = {}

    with open("menu.txt", "r") as file:
        lines = file.readlines()

    for line in lines:
        parts = line.strip().split("|")

        if len(parts) < 3:
            continue

        category = parts[0].strip()
        item = parts[1].strip()
        price = parts[2].strip()

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
# FORMAT ITEMS
# =========================
def format_items(menu, selected_category):
    items = menu[selected_category]

    text = f"🍽 *{selected_category}*\n\n"

    for i, item in enumerate(items, start=1):
        text += f"{i}. {item['item']} - ₹{item['price']}\n"

    text += "\nType item name to order."

    return text
