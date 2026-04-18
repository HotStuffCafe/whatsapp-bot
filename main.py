from fastapi import FastAPI, Request
from fastapi.responses import Response, JSONResponse
import html

from menu import get_menu_data, format_categories, format_items, format_all_items
from ORDER import handle_order
from payment import handle_payment, handle_payment_callback
from sheet_update import test_connection

app = FastAPI()

user_sessions = {}


@app.get("/")
def root():
    return {"status": "running"}


# =========================
# 📩 WHATSAPP WEBHOOK
# =========================
@app.post("/webhook")
async def whatsapp_webhook(request: Request):
    data = await request.form()

    user_msg = (data.get("Body") or "").strip()
    user_msg_lower = user_msg.lower()
    user_number = data.get("From")

    if not user_number:
        return Response(content="OK", media_type="text/plain")

    menu = get_menu_data()

    if user_number not in user_sessions:
        user_sessions[user_number] = {}

    session = user_sessions[user_number]
    session["user_number"] = user_number

    categories = list(menu.keys())

    # =========================
    # 🔥 GLOBAL COMMANDS
    # =========================
    if user_msg_lower in ["hi", "hello", "menu", "back", "show menu"]:
        session.clear()
        session["user_number"] = user_number

        text, cats = format_categories(menu)
        session["categories"] = cats
        reply = text

    elif user_msg_lower == "all items":
        reply = format_all_items(menu)

    elif user_msg_lower == "test sheet":
        reply = test_connection()

    elif user_msg_lower in [cat.lower() for cat in categories]:
        selected_category = next(cat for cat in categories if cat.lower() == user_msg_lower)
        reply = format_items(menu, selected_category)

    # =========================
    # 💳 PAYMENT → ORDER
    # =========================
    else:
        # PAYMENT FIRST
        payment_reply = handle_payment(user_msg, session, menu)

        if payment_reply:
            reply = payment_reply

        else:
            # ORDER FALLBACK
            order_reply = handle_order(user_msg, session, menu)

            if order_reply:
                reply = order_reply
            else:
                reply = "❌ Invalid option.\n\nType MENU to see options."

    # =========================
    # 🛡️ SAFE XML RESPONSE
    # =========================
    safe_reply = html.escape(reply)

    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>{safe_reply}</Message>
</Response>"""

    return Response(content=twiml, media_type="application/xml")


# =========================
# 🔔 RAZORPAY WEBHOOK
# =========================
@app.post("/payment/callback_uat1.1")
async def payment_callback(request: Request):
    data = await request.json()

    result = handle_payment_callback(data)

    return JSONResponse(content={"status": result})
