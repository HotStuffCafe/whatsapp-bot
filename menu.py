def get_menu_data():
    menu = {}

    with open("menu.txt", "r") as file:
        lines = file.readlines()

    # 🔥 Skip first row (header)
    for line in lines[1:]:
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
