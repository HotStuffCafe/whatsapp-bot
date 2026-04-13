import os
import json
import random
import re
from openai import OpenAI
from sheet_update import save_order_to_sheet

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

ENABLE_PAYMENT = os.getenv("ENABLE_PAYMENT", "false").lower() == "true"


# =========================
# GENERATE ORDER ID
# =========================
def generate_order_id():
    return f"ORD{random.randint(1000,9999)}"


# =========================
# SIMPLE PARSER (FAST + RELIABLE)
# =========================
def parse_simple(message, menu):

    items = []
    address = None

    # Detect address
    if any(word in message.lower() for word in ["shop", "room", "flat", "office"]):
        address = message

    # Extract quantities + items
    words = message.lower().split()

    for i, word in enumerate(words):
        if word.isdigit():
            qty = int(word)

            if i + 1 < len(words):
                item_word = words[i + 1]

                for category in menu.values():
                    for item in category:
                        if item_word in item["item"].lower():
                            items.append({
                                "name": item["item"],
                                "quantity": qty
                            })

    return items, address


# =========================
# SHOW CART
# =========================
def show_cart(session, menu):
    if "order" not in session or not session["order"]["items"]:
        return "🛒 Your cart is empty."

    order = session["order"]

    total = 0
    text = "🧾 Your Order\n\n"

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
# MAIN ORDER HANDLER
# =========================
def handle_order(user_msg, session, menu):

    msg = user_msg.lower()

    # =========================
    # CART COMMANDS
    # =========================
    if msg in ["cart", "order", "show order", "show cart"]:
        return show_cart(session, menu)

    # =========================
    # INIT ORDER
    # =========================
    if "order" not in session:
        session["order"] = {
            "items": [],
            "address": None
        }

    order = session["order"]

    # =========================
    # PARSE MESSAGE
    # =========================
    items, address = parse_simple(user_msg, menu)

    # ADD ITEMS
    for new_item in items:
        found = False

        for item in order["items"]:
            if item["name"].lower() == new_item["name"].lower():
                item["quantity"] += new_item["quantity"]
                found = True
                break

        if not found:
            order["items"].append(new_item)

    # ADDRESS
    if address:
        order["address"] = address

    # =========================
    # VALIDATION
    # =========================
    if not order["items"]:
        return None  # IMPORTANT → let menu handle

    if not order["address"]:
        return "📍 Please share your delivery address."

    # =========================
    # BUILD ORDER SUMMARY
    # =========================
    total = 0
    text = "🧾 Your Order\n\n"

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
