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

    # Initialize session if not exists
    if user_number not in user_sessions:
        user_sessions[user_number] = {}

    session = user_sessions[user_number]

    # =========================
    # 1. GLOBAL MENU HANDLER (TOP PRIORITY)
    # =========================
    if user_msg in ["hi", "hello", "menu", "show menu", "back"]:
        text, categories = format_categories(menu)

        session.clear()
        session["categories"] = categories

        reply = text

    # =========================
    # 2. ALL ITEMS HANDLER
    # =========================
    elif user_msg == "all items":
        reply = format_all_items(menu)

    # =========================
    # 3. CATEGORY SELECTION (ONLY IF NOT IN ORDER FLOW)
    # =========================
    elif "order" not in session:
        categories = session.get("categories", [])

        selected_category = None

        # Case 1: number selection
        if user_msg.isdigit():
            index = int(user_msg) - 1
            if 0 <= index < len(categories):
                selected_category = categories[index]

        # Case 2: text selection
        else:
            for cat in categories:
                if user_msg == cat.lower():
                    selected_category = cat
                    break

        if selected_category:
            reply = format_items(menu, selected_category)

            # Start order session
            session["order"] = {
                "item": None,
                "quantity": None,
                "address": None
            }

        else:
            reply = "❌ Invalid option.\n\nType MENU to see options."

    # =========================
    # 4. ORDER HANDLER
    # =========================
    elif "order" in session:
        reply = handle_order(user_msg, session, menu)

    # =========================
    # 5. DEFAULT RESPONSE
    # =========================
    else:
        reply = "👋 Welcome! Type *menu* to see available options."

    # =========================
    # TWILIO XML RESPONSE
    # =========================
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>{reply}</Message>
</Response>"""

    return Response(content=twiml, media_type="application/xml")
