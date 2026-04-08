from fastapi import FastAPI, Request
from fastapi.responses import Response
from menu import get_menu_data, format_categories, format_items

app = FastAPI()

# Simple in-memory session storage
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

    # =========================
    # STEP 1: SHOW MENU
    # =========================
    if any(keyword in user_msg for keyword in ["menu", "show menu", "hi", "hello"]):
        text, categories = format_categories(menu)

        # Save categories for this user
        user_sessions[user_number] = {
            "categories": categories
        }

        reply = text

    # =========================
    # STEP 2: CATEGORY SELECTION
    # =========================
    elif user_number in user_sessions:
        categories = user_sessions[user_number]["categories"]

        selected_category = None

        # Case 1: User enters number
        if user_msg.isdigit():
            index = int(user_msg) - 1
            if 0 <= index < len(categories):
                selected_category = categories[index]

        # Case 2: User types category name
        else:
            for cat in categories:
                if user_msg.lower() == cat.lower():
                    selected_category = cat
                    break

        if selected_category:
            reply = format_items(menu, selected_category)

            # Save selected category
            user_sessions[user_number]["selected_category"] = selected_category

        else:
            reply = "❌ Invalid option. Please select a valid category."

    # =========================
    # DEFAULT RESPONSE
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
