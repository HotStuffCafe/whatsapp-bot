from fastapi import FastAPI, Request
from fastapi.responses import Response

from menu import get_menu_data, format_categories, format_items, format_all_items
from ORDER import handle_order
from sheet_update import test_connection

app = FastAPI()

user_sessions = {}


@app.get("/")
def root():
    return {"status": "running"}


@app.post("/webhook")
async def whatsapp_webhook(request: Request):
    data = await request.form()

    user_msg = data.get("Body", "").strip()
    user_msg_lower = user_msg.lower()
    user_number = data.get("From")

    menu = get_menu_data()

    if user_number not in user_sessions:
        user_sessions[user_number] = {}

    session = user_sessions[user_number]
    session["user_number"] = user_number

    categories = list(menu.keys())

    # =========================
    # 🔥 GLOBAL COMMANDS (TOP PRIORITY)
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
    # 🧠 ORDER FLOW (ALWAYS RUN)
    # =========================
    else:
        order_reply = handle_order(user_msg, session, menu)

        if order_reply:
            reply = order_reply
        else:
            reply = "❌ Invalid option.\n\nType MENU to see options."

    # =========================
    # RESPONSE
    # =========================
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>{reply}</Message>
</Response>"""

    return Response(content=twiml, media_type="application/xml")
