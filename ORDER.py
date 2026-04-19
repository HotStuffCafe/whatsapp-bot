import re
import os
from datetime import datetime
from sheet_update import update_google_sheet
from payment import create_payment_link


# =========================
# 🧠 SMART PARSER
# =========================
def smart_parse_order(message, menu):
    message = message.lower()

    cart = {}
    address = None

    # Address extraction
    address_match = re.search(r"(shop\s*\d+|room\s*\d+|flat\s*\d+|house\s*\d+)", message)
    if address_match:
        address = address_match.group(0)

    # Match longest names first (fix chai issue)
    all_items = []
    for category in menu:
        for item in menu[category]:
            all_items.append(item["name"])

    all_items = sorted(all_items, key=lambda x: len(x), reverse=True)

    for item_name in all_items:
        pattern = rf"(\d+)\s*{item_name.lower()}"
        match = re.search(pattern, message)

        if match:
            qty = int(match.group(1))
            cart[item_name] = cart.get(item_name, 0) + qty

    return cart, address


# =========================
# 🧾 SUMMARY
# =========================
def generate_order_summary(session, menu):
    cart = session.get("cart", {})
    address = session.get("address")

    if not cart:
        return "🛒 Your cart is empty."

    total = 0
    lines = ["🧾 Your Order\n"]

    for item_name, qty in cart.items():
        price = get_item_price(menu, item_name)
        item_total = price * qty
        total += item_total
        lines.append(f"{item_name} x {qty} = ₹{item_total}")

    lines.append(f"\n💰 Total: ₹{total}")

    if address:
        lines.append(f"📍 Address: {address}")

    lines.append("\n👉 To add items: *add 2 chai, 1 cold coffee*")
    lines.append("👉 To remove items: *remove 2 chai*")
    lines.append("\n✅ Reply *YES* to confirm or *NO* to clear order")

    session["total"] = total

    return "\n".join(lines)


# =========================
# 🔍 PRICE
# =========================
def get_item_price(menu, item_name):
    for category in menu:
        for item in menu[category]:
            if item["name"].lower() == item_name.lower():
                return item["price"]
    return 0


# =========================
# 🆔 ORDER ID
# =========================
def generate_order_id():
    now = datetime.now()
    return now.strftime("ORD%d%m%y%H%M%S")


# =========================
# 🧠 HANDLE ORDER
# =========================
def handle_order(user_msg, session, menu):
    user_msg_lower = user_msg.lower()
    payment_mode = os.getenv("ENABLE_PAYMENT", "false").lower()

    if "cart" not in session:
        session["cart"] = {}

    # =========================
    # ADD
    # =========================
    if user_msg_lower.startswith("add"):
        parsed_cart, parsed_address = smart_parse_order(user_msg, menu)

        for item, qty in parsed_cart.items():
            session["cart"][item] = session["cart"].get(item, 0) + qty

        if parsed_address:
            session["address"] = parsed_address

        return generate_order_summary(session, menu)

    # =========================
    # REMOVE
    # =========================
    elif user_msg_lower.startswith("remove"):
        parsed_cart, _ = smart_parse_order(user_msg, menu)

        for item, qty in parsed_cart.items():
            if item in session["cart"]:
                session["cart"][item] -= qty
                if session["cart"][item] <= 0:
                    del session["cart"][item]

        return generate_order_summary(session, menu)

    # =========================
    # DIRECT ORDER
    # =========================
    parsed_cart, parsed_address = smart_parse_order(user_msg, menu)

    if parsed_cart:
        for item, qty in parsed_cart.items():
            session["cart"][item] = session["cart"].get(item, 0) + qty

        if parsed_address:
            session["address"] = parsed_address

        return generate_order_summary(session, menu)

    # =========================
    # ADDRESS INPUT
    # =========================
    if any(word in user_msg_lower for word in ["shop", "room", "flat", "house"]):
        session["address"] = user_msg
        return generate_order_summary(session, menu)

    # =========================
    # CONFIRM
    # =========================
    elif user_msg_lower in ["yes", "y", "yeah", "yea", "ok", "confirm"]:

        if not session.get("cart") or not session.get("address"):
            return "⚠️ Please complete your order (items + address)"

        order_id = generate_order_id()
        total = session.get("total", 0)

        # NO PAYMENT
        if payment_mode == "false":
            update_google_sheet(session, order_id, "COD", "Success")
            session.clear()

            return f"""✅ Your order has been received!

🆔 Order ID: {order_id}"""

        # ONLINE ONLY
        elif payment_mode == "true":
            session["order_id"] = order_id

            link = create_payment_link(total, order_id, session.get("user_number"))

            if link:
                return f"""🆔 Order ID: {order_id}

💳 Pay here:
{link}"""
            else:
                return "❌ Payment link failed. Try again."

        # PAY + COD
        elif payment_mode == "paycod":
            session["order_id"] = order_id

            return f"""🆔 Order ID: {order_id}

Choose payment option:
👉 PAY (Online)
👉 COD (Cash on Delivery)"""

    # =========================
    # PAY
    # =========================
    elif user_msg_lower == "pay":
        order_id = session.get("order_id")
        total = session.get("total")

        link = create_payment_link(total, order_id, session.get("user_number"))

        if link:
            return f"""💳 Pay here:
{link}"""
        else:
            return "❌ Payment link failed. Try again."

    # =========================
    # COD
    # =========================
    elif user_msg_lower == "cod":
        order_id = session.get("order_id")

        update_google_sheet(session, order_id, "COD", "Success")

        session.clear()

        return f"""✅ Order Confirmed!

🆔 Order ID: {order_id}
💰 Payment Mode: COD"""

    # =========================
    # CANCEL
    # =========================
    elif user_msg_lower == "no":
        session.clear()
        return "🗑️ Order cancelled."

    return None