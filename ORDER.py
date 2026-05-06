import re
import os
from datetime import datetime
from sheet_update import update_google_sheet


# =========================+
# 🆔 ORDER ID GENERATOR
# =========================
def generate_order_id():
    now = datetime.now()
    return now.strftime("ORD%d%m%y%H%M%S")


def get_enable_payment_mode():
    return os.getenv("ENABLE_PAYMENT", "false").strip().lower()


# =========================
# 🧠 FIND EXACT ITEM
# =========================
def find_item(menu, item_name):
    item_name = item_name.lower().strip()

    for category in menu:
        for row in menu[category]:
            item = row.get("item", "").strip()
            price = row.get("price", 0)

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


def parse_actions(text, menu):
    actions = []
    normalized = text.lower()

    command_matches = list(re.finditer(r"\b(add|remove)\b", normalized))
    if not command_matches:
        return actions

    for i, match in enumerate(command_matches):
        action = match.group(1)
        start = match.end()
        end = command_matches[i + 1].start() if i + 1 < len(command_matches) else len(normalized)
        chunk = normalized[start:end].strip()

        chunk = chunk.replace("\n", ",")
        chunk = chunk.replace(" and ", ",")
        chunk = chunk.replace(".", ",")
        chunk = chunk.replace(";", ",")

        for part in [p.strip() for p in chunk.split(",") if p.strip()]:
            item_match = re.match(r"(\d+)\s+(.*)", part)
            if not item_match:
                continue

            qty = int(item_match.group(1))
            name = item_match.group(2).strip()
            item, price = find_item(menu, name)
            if item:
                actions.append((action, item, qty, price))

    return actions


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
        text += "\n\n✅ Reply YES to confirm or NO to clear order"
    else:
        text += "\n\n📍 Share address"

    text += """

👉 To add items: *add 2 chai, 1 cold coffee*
👉 To remove items: *remove 2 chai*
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

    if re.search(r"\b(add|remove)\b", msg):
        parsed_actions = parse_actions(user_msg, menu)

        if not parsed_actions:
            return "❌ Could not understand items."

        cart = session.setdefault("cart", {})

        for action, item, qty, price in parsed_actions:
            if action == "add":
                if item in cart:
                    cart[item]["qty"] += qty
                else:
                    cart[item] = {"qty": qty, "price": price}
            else:
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

        if not session.get("cart"):
            return "⚠️ Please add items before confirming your order."

        if not session.get("address"):
            return "Hey unable to confirm your order, please share *address* before confirming the order."

        enable_payment_mode = get_enable_payment_mode()

        if enable_payment_mode in ["payonly", "paycod"]:
            order_id = session.get("order_id") or generate_order_id()
            session["order_id"] = order_id
            session["awaiting_payment"] = True

            if enable_payment_mode == "paycod":
                return f"""🧾 Order almost done!

🆔 Order ID: {order_id}
💰 Total: ₹{session.get("total", 0)}

Reply *PAY* for online payment or *COD* for cash on delivery."""

            return f"""🧾 Order almost done!

🆔 Order ID: {order_id}
💰 Total: ₹{session.get("total", 0)}

Reply *PAY* to complete payment and confirm your order."""

        order_id = generate_order_id()

        # SAVE TO SHEET
        update_google_sheet(session, order_id, "COD", "Pending")

        from kot import send_kot_to_kitchen
        send_kot_to_kitchen(
            order_id, 
            session.get("cart", {}), 
            session.get("address", ""), 
            session.get("total", 0), 
            "CASH ON DELIVERY"
        )
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
