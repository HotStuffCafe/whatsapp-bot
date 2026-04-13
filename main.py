from fastapi import FastAPI, Request
from fastapi.responses import Response
from menu import get_menu_data, format_categories, format_items, format_all_items
from ORDER import handle_order

app = FastAPI()

user_sessions = {}


@app.get("/")
def root():
    return {"status": "running"}


@app.post("/webhook")
async def whatsapp_webhook(request: Request):
    data = await request.form()

    user_msg = data.get("Body", "").strip().lower()
    user_number = data.get("From")

    menu = get_menu_data()

    if user_number not in user_sessions:
        user_sessions[user_number] = {}

    session = user_sessions[user_number]

    categories = list(menu.keys())

    # =========================
    # 🔥 1. GLOBAL COMMANDS (TOP PRIORITY)
    # =========================

    if user_msg in ["hi", "hello", "menu", "back", "show menu"]:
        session.clear()
        text, categories = format_categories(menu)
        session["categories"] = categories
        reply = text

    elif user_msg == "all items":
        session.clear()
        reply = format_all_items(menu)

    # CATEGORY DIRECT ACCESS
    elif user_msg in [cat.lower() for cat in categories]:
        session.clear()
        selected_category = next(cat for cat in categories if cat.lower() == user_msg)
        reply = format_items(menu, selected_category)

    # =========================
    # 🧠 2. ORDER FLOW
    # =========================
    else:
        order_reply = handle_order(user_msg, session, menu)

        if not order_reply.startswith("❓"):
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
