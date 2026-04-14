import os
import random
import re
from sheet_update import save_order_to_sheet

ENABLE_PAYMENT = os.getenv("ENABLE_PAYMENT", "false").lower() == "true"


# =========================
# ORDER ID
# =========================
def generate_order_id():
    return f"ORD{random.randint(1000,9999)}"


# =========================
# EXTRACT ITEMS (MULTI SUPPORT)
# =========================
def extract_items(message, menu):
    message = message.lower()

    items_found = []

    # Pattern: "2 chai", "3 pizza"
    matches = re.findall(r'(\d+)\s*([a-zA-Z ]+)', message)

    for qty, name in matches:
        qty = int(qty)

        for category in menu.values():
            for item in category:
                if name.strip() in item["item"].lower():
                    items_found.append({
                        "name": item["item"],
                        "quantity": qty
                    })

    return items_found


# =========================
# DETECT ADDRESS
# =========================
def extract_address(message):
    if any(word in message.lower() for word in ["shop", "room", "flat", "office"]):
        return message
    return None


# =========================
# APPLY ADD / REMOVE
# =========================
def update_order(order, new_items, action="add"):

    for new_item in new_items:
        name = new_item["name"]
        qty = new_item["quantity"]

        found = False

        for item in order["items"]:
            if item["name"].lower() == name.lower():
                found = True

                if action == "add":
                    item["quantity"] += qty
                elif action == "remove":
                    item["quantity"] -= qty
                    if item["quantity"] <= 0:
                        order["items"].remove(item)
                break

        if not found and action == "add":
            order["items"].append(new_item)


# =========================
# BUILD SUMMARY
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

    text += f"\n💰 Total: ₹{total}"

    if order.get("address"):
        text += f"\n📍 Address: {order['address']}"

    text += "\n\n✅ Reply YES to confirm or NO to cancel"

    return text


# =========================
# MAIN HANDLER
# =========================
def handle_order(user_msg, session, menu):

    msg = user_msg.lower()

    # INIT ORDER
    if "order" not in session:
        session["order"] = {
            "items": [],
            "address": None,
            "confirmed": False
        }

    order = session["order"]

    # =========================
    # SHOW CART
    # =========================
    if msg in ["cart", "order", "show order", "show cart"]:
        if not order["items"]:
            return "🛒 Your cart is empty."
        return build_summary(order, menu)

    # =========================
    # YES / NO FLOW
    # =========================
    if msg == "yes":

        if not order["items"] or not order["address"]:
            return None

        order_id = generate_order_id()

        # SAVE TO SHEET
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

        return f"""✅ Your order has been received!

🆔 Order ID: {order_id}

💰 Kindly make payment to confirm your order"""

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
    # EXTRACT DATA
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
