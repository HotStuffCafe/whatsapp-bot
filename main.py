from fastapi import FastAPI, Request
from fastapi.responses import Response
from menu import get_menu_data, format_categories, format_items, format_all_items
from ORDER import handle_order

app = FastAPI()

# In-memory session store
user_sessions = {}


@app.get("/")
def root():
    return {"status": "running"}


@app.post("/webhook")
async def whatsapp_webhook(request: Request):
    data = await request.form()

    user_msg = data.get("Body", "").strip().lower()
    user_number = data.get("From")

    # Load menu
    menu = get_menu_data()
    categories = list(menu.keys())

    # Initialize session
    if user_number not in user_sessions:
        user_sessions[user_number] = {}

    session = user_sessions[user_number]

    # Store user number for sheet logging
    session["user_number"] = user_number

    # =========================
    # 🔥 1. GLOBAL COMMANDS (TOP PRIORITY)
    # =========================

    # MENU / BACK / GREETING
    if user_msg in ["hi", "hello", "menu", "back", "show menu"]:
        session.clear()
        session["user_number"] = user_number

        text, cats = format_categories(menu)
        session["categories"] = cats

        reply = text

    # ALL ITEMS
    elif user_msg == "all items":
        reply = format_all_items(menu)

    # DIRECT CATEGORY ACCESS
    elif user_msg in [cat.lower() for cat in categories]:
        selected_category = next(cat for cat in categories if cat.lower() == user_msg)
        reply = format_items(menu, selected_category)

    # =========================
    # 🧠 2. ORDER FLOW (AI)
    # =========================
    else:
        order_reply = handle_order(user_msg, session, menu)

        if order_reply and not order_reply.startswith("❓"):
            reply = order_reply
        else:
            reply = "❌ Invalid option.\n\nType MENU to see options."

    # =========================
    # 📩 TWILIO RESPONSE
    # =========================
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>{reply}</Message>
</Response>"""

    return Response(content=twiml, media_type="application/xml")
