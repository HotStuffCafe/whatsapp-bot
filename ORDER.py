import os
import json
import random
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

ENABLE_PAYMENT = os.getenv("ENABLE_PAYMENT", "false").lower() == "true"


def generate_order_id():
    return f"ORD{random.randint(1000,9999)}"


def get_all_item_names(menu):
    items = []
    for category in menu.values():
        for item in category:
            items.append(item["item"])
    return items


def parse_order_with_ai(message, menu_items):
    prompt = f"""
Extract order details.

Menu items:
{menu_items}

Message:
"{message}"

Return JSON:

{{
  "items": [{{"name": "", "quantity": 0}}],
  "address": "",
  "action": ""
}}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    try:
        return json.loads(response.choices[0].message.content)
    except:
        return {}


# =========================
# 🛒 SHOW CART
# =========================
def show_cart(session, menu):
    if "order" not in session or not session["order"]["items"]:
        return "🛒 Your cart is empty."

    order = session["order"]

    total = 0
    text = "🛒 *Your Cart*\n\n"

    for item in order["items"]:
        name = item["name"]
        qty = item["quantity"]

        price = 0
        for cat in menu.values():
            for i in cat:
                if i["item"].lower() == name.lower():
                    price = i["price"]

        item_total = price * qty
        total += item_total

        text += f"{name} x {qty} = ₹{item_total}\n"

    text += f"\n💰 Total: ₹{total}"

    if order.get("address"):
        text += f"\n📍 Address: {order['address']}"

    return text


# =========================
# MAIN HANDLER
# =========================
def handle_order(user_msg, session, menu):

    user_msg_lower = user_msg.lower()

    # =========================
    # 🛒 CART COMMANDS
    # =========================
    if user_msg_lower in ["cart", "order", "show cart", "show order", "kart"]:
        return show_cart(session, menu)

    # =========================
    # ✅ CONFIRM
    # =========================
    if user_msg_lower == "yes":
        if "order" not in session or not session["order"]["items"]:
            return "❌ No active order."

        order = session["order"]
        order_id = generate_order_id()

        # PAYMENT FLOW
        if ENABLE_PAYMENT:
            return f"""
🧾 Order ID: {order_id}

Your order has been received, kindly make payment to confirm your order.

💳 Payment Options:
1. UPI
2. COD

Reply with UPI or COD
"""

        # NO PAYMENT FLOW
        session.clear()
        return f"""
🎉 Order Confirmed!

🆔 Order ID: {order_id}

Your order has been received.
"""

    # =========================
    # ❌ CANCEL
    # =========================
    if user_msg_lower == "no":
        session.clear()
        return "❌ Your order has been cancelled."

    # =========================
    # SKIP MENU COMMANDS
    # =========================
    if user_msg_lower in ["menu", "back", "hi", "hello", "all items"]:
        return "❓"

    if "order" not in session:
        session["order"] = {"items": [], "address": None}

    order = session["order"]

    menu_items = get_all_item_names(menu)
    parsed = parse_order_with_ai(user_msg, menu_items)

    action = parsed.get("action", "add")

    # =========================
    # ADD / REMOVE
    # =========================
    if parsed.get("items"):
        for new_item in parsed["items"]:
            name = new_item.get("name")
            qty = int(new_item.get("quantity", 0))

            if not name or qty <= 0:
                continue

            if action == "remove":
                for item in order["items"]:
                    if item["name"].lower() == name.lower():
                        item["quantity"] -= qty
                        if item["quantity"] <= 0:
                            order["items"].remove(item)
                        break
            else:
                found = False
                for item in order["items"]:
                    if item["name"].lower() == name.lower():
                        item["quantity"] += qty
                        found = True
                        break

                if not found:
                    order["items"].append({"name": name, "quantity": qty})

    # =========================
    # ADDRESS
    # =========================
    if parsed.get("address"):
        order["address"] = parsed["address"]

    if not order["address"]:
        if any(w in user_msg_lower for w in ["shop", "room", "flat", "office", "sector"]):
            order["address"] = user_msg

    # =========================
    # VALIDATION
    # =========================
    if not order["items"]:
        return "❓ What would you like to order?"

    if not order["address"]:
        return "📍 Please share your delivery address."

    # =========================
    # RESPONSE
    # =========================
    total = 0
    text = "🧾 *Your Order*\n\n"

    for item in order["items"]:
        name = item["name"]
        qty = item["quantity"]

        price = 0
        for cat in menu.values():
            for i in cat:
                if i["item"].lower() == name.lower():
                    price = i["price"]

        item_total = price * qty
        total += item_total

        text += f"{name} x {qty} = ₹{item_total}\n"

    text += f"\n💰 Total: ₹{total}"
    text += f"\n📍 Address: {order['address']}"
    text += "\n\n✅ Reply YES to confirm or NO to cancel"

    return text
