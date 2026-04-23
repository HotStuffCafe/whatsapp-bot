import re
from datetime import datetime
from sheet_update import update_google_sheet


# =========================
# 🆔 ORDER ID GENERATOR
# =========================
def generate_order_id():
    now = datetime.now()
    return now.strftime("ORD%d%m%y%H%M%S")


# =========================
# 🧠 FIND EXACT ITEM
# =========================
def find_item(menu, item_name):
    item_name = item_name.lower().strip()

    for category in menu:
        for item, price in menu[category].items():
            if item.lower() == item_name:
                return item, price

    return None, None


# =========================
# 🧠 PARSE ORDER TEXT
# =========================
def parse_order(text, menu):
    text = text.lower()

    # normalize
    text = text.replace("\n", ",")
    text = text.replace(" and ", ",")
    text = text.replace("add", "")
    text = text.replace("remove", "")

    parts = text.split(",")

    items = []

    for part in parts:
        part = part.strip()
        if not part:
            continue

        match = re.match(r"(\d+)\s+(.*)", part)

        if match:
            qty = int(match.group(1))
            name = match.group(2).strip()

            item, price = find_item(menu, name)

            if item:
                items.append((item, qty, price))

    return items


# =========================
# 🧾 BUILD CART MESSAGE
# =========================
def build_cart(session):
    cart = session.get("cart", {})
    total = 0

    if not cart:
        return "🛒 Your cart is empty."

    text = "🧾 Your Order\n\n"

    for item, data in cart.items():
        qty = data["qty"]
        price = data["price"]
        line_total = qty * price
        total += line_total

        text += f"{item} x {qty} = ₹{line_total}\n"

    text += f"\n💰 Total: ₹{total}"

    if session.get("address"):
        text += f"\n📍 Address: {session['address']}"

    text += """

👉 To add items: *add 2 chai, 1 cold coffee*
👉 To remove items: *remove 2 chai*

✅ Reply YES to confirm or NO to clear order
"""

    session["total"] = total

    return text


# =========================
# 🧠 MAIN ORDER HANDLER
# =========================
def handle_order(user_msg, session, menu):

    msg = user_msg.lower().strip()

    if "cart" in msg or "order" in msg:
        return build_cart(session)

    # =========================
    # ➕ ADD ITEMS
    # =========================
    if "add" in msg:
        items = parse_order(msg, menu)

        if not items:
            return "❌ Could not understand items."

        cart = session.setdefault("cart", {})

        for item, qty, price in items:
            if item in cart:
                cart[item]["qty"] += qty
            else:
                cart[item] = {"qty": qty, "price": price}

        return build_cart(session)

    # =========================
    # ➖ REMOVE ITEMS
    # =========================
    if "remove" in msg:
        items = parse_order(msg, menu)

        cart = session.get("cart", {})

        for item, qty, _ in items:
            if item in cart:
                cart[item]["qty"] -= qty

                if cart[item]["qty"] <= 0:
                    del cart[item]

        return build_cart(session)

    # =========================
    # 📍 ADDRESS DETECTION
    # =========================
    if any(word in msg for word in ["shop", "road", "street", "sector"]):
        session["address"] = user_msg
        return build_cart(session)

    # =========================
    # ✅ CONFIRM ORDER
    # =========================
    if msg in ["yes", "y"]:

        if not session.get("cart") or not session.get("address"):
            return "⚠️ Please complete your order (items + address)"

        order_id = generate_order_id()

        # SAVE TO SHEET
        update_google_sheet(session, order_id, "COD", "Success")

        session.clear()

        return f"""✅ Order Confirmed!

🆔 Order ID: {order_id}"""

    # =========================
    # ❌ CANCEL
    # =========================
    if msg in ["no", "cancel"]:
        session.clear()
        return "❌ Order cancelled."

    return None