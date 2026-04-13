from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
import os

from menu import (
    load_menu,
    get_categories,
    get_items_by_category,
    get_all_items_text
)

from ORDER import handle_order
from sheet_update import save_order_to_sheet, test_connection

app = FastAPI()

# In-memory session store
sessions = {}

# Payment toggle
ENABLE_PAYMENT = os.getenv("ENABLE_PAYMENT", "false").lower() == "true"


# =========================
# WHATSAPP WEBHOOK
# =========================
@app.post("/")
async def whatsapp_webhook(request: Request):

    data = await request.form()

    user_msg = data.get("Body", "").strip()
    user_number = data.get("From", "")

    user_msg_lower = user_msg.lower()

    # Load menu dynamically
    menu = load_menu()

    # Get user session
    session = sessions.get(user_number, {
        "stage": "menu",
        "order": {"items": [], "address": None}
    })

    # =========================
    # GLOBAL COMMANDS (WORK ANYTIME)
    # =========================

    # MENU / BACK
    if user_msg_lower in ["menu", "back"]:
        categories = get_categories(menu)

        text = "📋 Menu Categories\n\n"
        for i, cat in enumerate(categories, 1):
            text += f"{i}. {cat}\n"

        text += "\n👉 Reply with number or category name"
        text += "\n👉 To see all items, type all items"

        session["stage"] = "menu"
        sessions[user_number] = session

        return PlainTextResponse(text)

    # ALL ITEMS
    if user_msg_lower == "all items":
        return PlainTextResponse(get_all_items_text(menu))

    # SHOW ORDER / CART
    if user_msg_lower in ["order", "cart", "kart", "show order", "show cart"]:
        order = session.get("order", {"items": []})

        if not order["items"]:
            return PlainTextResponse("🛒 Your cart is empty")

        text = "🧾 Your Order\n\n"
        total = 0

        for item in order["items"]:
            name = item["name"]
            qty = item["quantity"]

            price = 0
            for category in menu.values():
                for m in category:
                    if m["item"].lower() == name.lower():
                        price = m["price"]

            item_total = price * qty
            total += item_total

            text += f"{name} x {qty} = ₹{item_total}\n"

        text += f"\n💰 Total: ₹{total}"

        if order.get("address"):
            text += f"\n📍 Address: {order['address']}"

        return PlainTextResponse(text)

    # TEST SHEET
    if user_msg_lower == "test sheet":
        return PlainTextResponse(test_connection())

    # =========================
    # ORDER FLOW (AI HANDLING)
    # =========================

    order_reply = handle_order(user_msg, session, menu)

    if order_reply:
        sessions[user_number] = session
        return PlainTextResponse(order_reply)

    # =========================
    # MENU FLOW
    # =========================

    categories = get_categories(menu)

    # Number selection
    if user_msg.isdigit():
        index = int(user_msg) - 1

        if 0 <= index < len(categories):
            category = categories[index]
        else:
            return PlainTextResponse("❌ Invalid option.\n\nType MENU to see options.")
    else:
        # Match category name
        category = None
        for cat in categories:
            if cat.lower() == user_msg_lower:
                category = cat

    if category:
        items = get_items_by_category(menu, category)

        text = f"🍽 {category}\n\n"

        for i, item in enumerate(items, 1):
            text += f"{i}. {item['item']} - ₹{item['price']}\n"

        text += "\n👉 Type back or menu to go to main menu"
        text += "\n👉 To see all items, type all items"

        return PlainTextResponse(text)

    # =========================
    # DEFAULT FALLBACK
    # =========================

    return PlainTextResponse("❌ Invalid option.\n\nType MENU to see options.")


# =========================
# ORDER CONFIRMATION HANDLER
# =========================

def confirm_order(session, user_number, menu):

    order = session["order"]

    import random
    order_id = random.randint(1000, 9999)

    # PAYMENT FLOW
    if ENABLE_PAYMENT:
        return (
            f"🧾 Order ID: {order_id}\n\n"
            f"💳 Please complete payment via UPI\n"
            f"(Payment module coming next)"
        )

    # COD FLOW → SAVE TO SHEET
    save_order_to_sheet(
        order_id=order_id,
        order=order,
        user_number=user_number,
        menu=menu,
        payment_mode="COD",
        payment_status="na"
    )

    # CLEAR SESSION
    session["order"] = {"items": [], "address": None}
    session["stage"] = "menu"

    return (
        f"✅ Your order has been received!\n\n"
        f"🆔 Order ID: {order_id}\n"
        f"💰 Please keep cash ready (COD)"
    )
