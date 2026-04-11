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

    # =========================
    # 🔥 1. ORDER FIRST (TOP PRIORITY)
    # =========================
    order_reply = handle_order(user_msg, session, menu)

    # If meaningful order response → return immediately
    if not order_reply.startswith("❓"):
        reply = order_reply

    # =========================
    # 2. GLOBAL MENU HANDLER
    # =========================
    elif user_msg in ["hi", "hello", "menu", "show menu", "back"]:
        text, categories = format_categories(menu)

        session.clear()
        session["categories"] = categories

        reply = text

    # =========================
    # 3. ALL ITEMS
    # =========================
    elif user_msg == "all items":
        reply = format_all_items(menu)

    # =========================
    # 4. CATEGORY SELECTION
    # =========================
    else:
        categories = session.get("categories", [])

        selected_category = None

        if user_msg.isdigit():
            index = int(user_msg) - 1
            if 0 <= index < len(categories):
                selected_category = categories[index]

        else:
            for cat in categories:
                if user_msg == cat.lower():
                    selected_category = cat
                    break

        if selected_category:
            reply = format_items(menu, selected_category)
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
