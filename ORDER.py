import os
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")


# =========================
# AI PARSER
# =========================
def parse_order_with_ai(message, menu_items):
    prompt = f"""
You are an order parser.

Extract:
- item (must match menu items)
- quantity (number)
- address (text)

Menu Items:
{menu_items}

User message:
"{message}"

Return ONLY JSON like:
{{
  "item": "",
  "quantity": "",
  "address": ""
}}
"""

    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    text = response.choices[0].message.content.strip()

    try:
        import json
        return json.loads(text)
    except:
        return {}
    

# =========================
# BUILD MENU ITEM LIST
# =========================
def get_all_item_names(menu):
    items = []

    for category in menu.values():
        for item in category:
            items.append(item["item"])

    return items


# =========================
# ORDER HANDLER
# =========================
def handle_order(user_msg, session, menu):
    
    if "order" not in session:
        session["order"] = {
            "item": None,
            "quantity": None,
            "address": None
        }

    order = session["order"]

    # Get menu items list
    menu_items = get_all_item_names(menu)

    # AI PARSE
    parsed = parse_order_with_ai(user_msg, menu_items)

    # UPDATE ORDER
    if parsed.get("item"):
        order["item"] = parsed["item"]

    if parsed.get("quantity"):
        try:
            order["quantity"] = int(parsed["quantity"])
        except:
            pass

    if parsed.get("address"):
        order["address"] = parsed["address"]

    # =========================
    # CHECK MISSING
    # =========================
    if not order["item"]:
        return "❓ Which item would you like to order?"

    if not order["quantity"]:
        return "❓ Please tell me the quantity."

    if not order["address"]:
        return "📍 Please share your delivery address."

    # =========================
    # ALL DATA AVAILABLE → CONFIRM
    # =========================
    # Get price
    price = None

    for category in menu.values():
        for item in category:
            if item["item"].lower() == order["item"].lower():
                price = item["price"]

    total = price * order["quantity"] if price else 0

    confirmation = f"""
🧾 *Your Order*

Item: {order['item']}
Qty: {order['quantity']}
Price: ₹{price}
Total: ₹{total}

📍 Address: {order['address']}

✅ Reply YES to confirm or NO to cancel
"""

    return confirmation
