from fastapi import FastAPI, Request
from fastapi.responses import Response, JSONResponse, HTMLResponse
import importlib.util
import os

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
    try:
        from menu import get_menu_data, format_categories, format_items, format_all_items
        from ORDER import handle_order
        from payment import handle_payment
        from sheet_update import test_connection

        data = await request.form()

        user_msg = data.get("Body", "").strip()
        user_msg_lower = user_msg.lower()
        user_number = data.get("From")

        menu = get_menu_data()

        if user_number not in user_sessions:
            user_sessions[user_number] = {}

        session = user_sessions[user_number]

        # ✅ IMPORTANT FIX
        session["user_number"] = user_number
        session["menu"] = menu   # 🔥 REQUIRED FOR SHEET PRICING

        # =========================
        # 👑 ADMIN INTERCEPT
        # =========================
        from admin import handle_admin_command
        admin_reply = handle_admin_command(user_msg, user_number)
        
        if admin_reply:
            twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
            <Response><Message>{admin_reply}</Message></Response>"""
            return Response(content=twiml, media_type="application/xml")

        # =========================
        # 👨‍🍳 KITCHEN (KOT) INTERCEPT (Add this new block!)
        # =========================
        from kot import is_kot, handle_kot_command
        if is_kot(user_number):
            kot_reply = handle_kot_command(user_msg, data) # 'data' contains the Twilio payload needed to read the quoted message
            if kot_reply:
                twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
                <Response><Message>{kot_reply}</Message></Response>"""
                return Response(content=twiml, media_type="application/xml")

        categories = list(menu.keys())

        # =========================
        # 🔥 GLOBAL COMMANDS
        # =========================
        if user_msg_lower in ["hi", "hello", "menu", "back", "show menu"]:
            session.clear()
            session["user_number"] = user_number
            session["menu"] = menu

            text, cats = format_categories(menu)
            session["categories"] = cats
            reply = text

        elif user_msg_lower == "all items":
            reply = format_all_items(menu)

        elif user_msg_lower == "test sheet":
            reply = test_connection()

        elif user_msg.isdigit() and 1 <= int(user_msg) <= len(categories):
            selected_category = categories[int(user_msg) - 1]
            reply = format_items(menu, selected_category)

        elif user_msg_lower in [cat.lower() for cat in categories]:
            selected_category = next(cat for cat in categories if cat.lower() == user_msg_lower)
            reply = format_items(menu, selected_category)

        # =========================
        # 💳 PAYMENT FLOW
        # =========================
        else:
            payment_reply = handle_payment(user_msg, session, menu)

            if payment_reply:
                reply = payment_reply
            else:
                # =========================
                # 🧠 ORDER FLOW
                # =========================
                order_reply = handle_order(user_msg, session, menu)

                if order_reply:
                    reply = order_reply
                else:
                    reply = "❌ Invalid option.\n\nType MENU to see options."
    except Exception as e:
        print("❌ Webhook Error:", str(e))
        reply = "⚠️ Temporary issue. Please type MENU again."

    # =========================
    # 📤 TWILIO RESPONSE
    # =========================
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>{reply}</Message>
</Response>"""

    return Response(content=twiml, media_type="application/xml")


# =========================
# 🔔 RAZORPAY CALLBACK
# =========================
@app.get("/payment/callback_uat1.1")
async def payment_callback_get(request: Request):
    from payload import save_payload_to_sheet

    params = dict(request.query_params)
    order_id = params.get("razorpay_payment_link_reference_id", "").strip()

    print("Razorpay GET callback:", params)
    payload_result = save_payload_to_sheet(params, str(request.url))

    callback_module_path = os.path.join(os.path.dirname(__file__), "CALLBACK ACITON.py")
    spec = importlib.util.spec_from_file_location("callback_aciton_module", callback_module_path)
    callback_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(callback_module)
    callback_result = callback_module.handle_callback_action(order_id)

    status = callback_result.get("status", "processed")
    html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; padding: 24px;">
        <h2>Payment callback received</h2>
        <p>Order ID: <b>{order_id or "N/A"}</b></p>
        <p>Status: <b>{status}</b></p>
        <p>You can close this page and return to WhatsApp.</p>
      </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.post("/payment/callback_uat1.1")
async def payment_callback(request: Request):
    from payment import handle_payment_callback

    data = await request.json()

    result = handle_payment_callback(data)

    return JSONResponse(content={"status": result})
