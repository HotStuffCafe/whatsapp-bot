import os
import re
from datetime import datetime
from sheet_update import save_order_to_sheet

ENABLE_PAYMENT = os.getenv("ENABLE_PAYMENT", "false").lower() == "true"


# =========================
# ORDER ID (WITH SECONDS)
# =========================
def generate_order_id():
    now = datetime.now()

    return "ORD" + now.strftime("%d%m%y%H%M%S")


# =========================
# SMART MATCH (FIXES CHAI ISSUE)
# =========================
def match_item(user_text, menu):

    user_text = user_text.lower().strip()
    matched_items = []

    for category in menu.values():
        for item in category:
            item_name = item["item"].lower()

            # Exact phrase match
            if item_name in user_text:
                matched_items.append(item)

    # Remove overlaps (chai vs cutting chai)
    final_items = []

    for item in matched_items:
        name = item["item"].lower()

        if not any(
            name != other["item"].lower() and name in other["item"].lower()
            for other in matched_items
        ):
            final_items.append(item)

    return final_items


# =========================
# EXTRACT ITEMS (MULTI SUPPORT)
# =========================
def extract_items(message, menu):

    message = message.lower()
    items = []

    # matches: "2 chai", "1 cold coffee"
    matches = re.findall(r'(\d+)\s*([a-zA-Z ]+)', message)

    for qty, text in matches:
        qty = int(qty)

        matched = match_item(text, menu)

        for item in matched:
            items.append({
                "name": item["item"],
                "quantity": qty
            })

    return items


# =========================
# ADDRESS DETECTION
# =========================
def extract_address(message):
    if any(word in message.lower() for word in ["shop", "room", "flat", "office"]):
        return message
    return None


# =========================
# UPDATE ORDER (ADD / REMOVE)
# =========================
def update_order(order, items, action):

    for new_item in items:
        found = False

        for item in order["items"]:
            if item["name"].lower() == new_item["name"].lower():
                found = True

                if action == "add":
                    item["quantity"] += new_item["quantity"]

                elif action == "remove":
                    item["quantity"] -= new_item["quantity"]

                    if item["quantity"] <= 0:
                        order["items"].remove(item)

                break

        if not found and action == "add":
            order["items"].append(new_item)


# =========================
# BUILD ORDER SUMMARY
# =========================
def build_summary(order, menu):

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

    text += f"\n💰 *Total*: ₹{total}"

    if order.get("address"):
        text += f"\n📍 Address: {order['address']}"

    text += "\n\n👉 To add items: *add* 2 chai, 1 cold coffee"
    text += "\n👉 To remove items: *remove* 2 chai, 1 cold coffee"
    text += "\n\n✅ Reply *YES* to confirm or *NO* to clear your order"

    return text


# =========================
# MAIN ORDER HANDLER
# =========================
def handle_order(user_msg, session, menu):

    msg = user_msg.lower()

    if "order" not in session:
        session["order"] = {"items": [], "address": None}

    order = session["order"]

    # =========================
    # SHOW CART
    # =========================
    if msg in ["cart", "order", "show order", "show cart"]:
        if not order["items"]:
            return "🛒 Your cart is empty."
        return build_summary(order, menu)

    # =========================
    # YES (CONFIRM ORDER)
    # =========================
    if msg == "yes":

        if not order["items"] or not order["address"]:
            return None

        order_id = generate_order_id()

        # SAVE TO GOOGLE SHEET
        save_order_to_sheet(
            order_id=order_id,
            order=order,
            user_number=session.get("user_number"),
            menu=menu,
            payment_mode="COD",
            payment_status="na"
        )

        # RESET SESSION
        session["order"] = {"items": [], "address": None}

        # PAYMENT TOGGLE
        if ENABLE_PAYMENT:
            return f"""✅ Your order has been received!

🆔 Order ID: {order_id}

💳 Kindly make payment to confirm your order"""
        else:
            return f"""✅ Your order has been received!

🆔 Order ID: {order_id}"""

    # =========================
    # NO (CANCEL)
    # =========================
    if msg == "no":
        session["order"] = {"items": [], "address": None}
        return "❌ Order cancelled."

    # =========================
    # DETECT ACTION
    # =========================
    action = "add"
    if "remove" in msg:
        action = "remove"

    # =========================
    # PARSE MESSAGE
    # =========================
    items = extract_items(user_msg, menu)
    address = extract_address(user_msg)

    if items:
        update_order(order, items, action)

    if address:
        order["address"] = address

    # =========================
    # VALIDATION
    # =========================
    if not order["items"]:
        return None

    if not order["address"]:
        return "📍 Please share your delivery address."

    return build_summary(order, menu)
