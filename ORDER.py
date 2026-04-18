import re
import os
from datetime import datetime
from sheet_update import save_order_to_sheet

# Temporary order storage (for webhook future use)
order_store = {}

PAYMENT_MODE = os.getenv("PAYMENT_MODE", "OFF")


# =========================
# 🧾 GENERATE ORDER ID
# =========================
def generate_order_id():
    now = datetime.now()
    return now.strftime("ORD%d%m%y%H%M%S")


# =========================
# 🔍 FIND ITEM EXACT MATCH
# =========================
def find_item(menu, item_name):
    item_name = item_name.lower().strip()

    for category in menu.values():
        for item in category:
            if item["item"].lower() == item_name:
                return item

    return None


# =========================
# 🧠 PARSE ORDER TEXT
# =========================
def parse_order_text(text):
    text = text.lower()

    # supports: "2 chai, 1 cold coffee"
    parts = re.split(r",|\n", text)

    parsed = []

    for part in parts:
        match = re.search(r"(\d+)\s+(.+)", part.strip())
        if match:
            qty = int(match.group(1))
            name = match.group(2).strip()
            parsed.append((name, qty))

    return parsed


# =========================
# ➕ ADD ITEMS
# =========================
def add_items(order, parsed_items, menu):
    for name, qty in parsed_items:

        item = find_item(menu, name)

        if not item:
            continue

        existing = next((i for i in order["items"] if i["name"] == item["item"]), None)

        if existing:
            existing["quantity"] += qty
        else:
            order["items"].append({
                "name": item["item"],
                "quantity": qty
            })


# =========================
# ➖ REMOVE ITEMS
# =========================
def remove_items(order, parsed_items, menu):
    for name, qty in parsed_items:

        item = find_item(menu, name)

        if not item:
            continue

        existing = next((i for i in order["items"] if i["name"] == item["item"]), None)

        if existing:
            existing["quantity"] -= qty

            if existing["quantity"] <= 0:
                order["items"].remove(existing)


# =========================
# 🧾 CALCULATE TOTAL
# =========================
def calculate_total(order, menu):
    total = 0

    for item in order["items"]:
        for category in menu.values():
            for m in category:
                if m["item"] == item["name"]:
                    total += m["price"] * item["quantity"]

    return total


# =========================
# 🧾 FORMAT CART
# =========================
def format_order(order, menu):

    if not order["items"]:
        return "🛒 Your cart is empty."

    text = "🧾 *Your Order*\n\n"

    for item in order["items"]:
        for category in menu.values():
            for m in category:
                if m["item"] == item["name"]:
                    price = m["price"]
                    total = price * item["quantity"]
                    text += f"{item['name']} x {item['quantity']} = ₹{int(total)}\n"

    total_amt = calculate_total(order, menu)

    text += f"\n💰 *Total:* ₹{int(total_amt)}"

    if order.get("address"):
        text += f"\n📍 Address: {order['address']}"

    text += """

👉 To add items: *add 2 chai, 1 cold coffee*
👉 To remove items: *remove 2 chai*

✅ Reply *YES* to confirm or *NO* to clear order
"""

    return text


# =========================
# 🧠 MAIN ORDER HANDLER
# =========================
def handle_order(user_msg, session, menu):

    msg = user_msg.lower().strip()

    if "order" not in session:
        session["order"] = {
            "items": [],
            "address": None
        }

    order = session["order"]

    # =========================
    # 🛒 SHOW ORDER
    # =========================
    if msg in ["order", "cart", "show order", "show cart"]:
        return format_order(order, menu)

    # =========================
    # ➕ ADD
    # =========================
    if msg.startswith("add"):
        parsed = parse_order_text(msg.replace("add", ""))
        add_items(order, parsed, menu)
        return format_order(order, menu)

    # =========================
    # ➖ REMOVE
    # =========================
    if msg.startswith("remove"):
        parsed = parse_order_text(msg.replace("remove", ""))
        remove_items(order, parsed, menu)
        return format_order(order, menu)

    # =========================
    # 📍 ADDRESS DETECTION
    # =========================
    if "shop" in msg or "road" in msg or "street" in msg:
        order["address"] = user_msg
        return format_order(order, menu)

    # =========================
    # 🧾 DIRECT ORDER (NO ADD WORD)
    # =========================
    parsed = parse_order_text(msg)

    if parsed:
        add_items(order, parsed, menu)
        return format_order(order, menu)

    # =========================
    # ✅ CONFIRM ORDER
    # =========================
    if msg == "yes":

        if not order["items"] or not order["address"]:
            return "⚠️ Please complete your order (items + address)"

        order_id = generate_order_id()

        # Save for webhook usage
        order_store[order_id] = order

        # =========================
        # 💵 PAYMENT MODE LOGIC
        # =========================

        if PAYMENT_MODE == "OFF":

            save_order_to_sheet(
                order_id, order, session["user_number"], menu, "COD", "na"
            )

            session.clear()

            return f"""✅ Your order has been received!

🆔 Order ID: {order_id}"""

        elif PAYMENT_MODE == "RAZORPAY":

            session["order_id"] = order_id
            session["awaiting_payment"] = True

            return f"""🧾 Order ID: {order_id}

💳 Payment required

👉 Type *PAY* to proceed"""

        elif PAYMENT_MODE == "PAYCOD":

            session["order_id"] = order_id
            session["awaiting_payment"] = True

            return f"""🧾 Order ID: {order_id}

Choose payment option:

👉 *PAY* (Online)
👉 *COD* (Cash on Delivery)
"""

    # =========================
    # ❌ CANCEL ORDER
    # =========================
    if msg == "no":
        session.clear()
        return "❌ Order cancelled."

    return None
