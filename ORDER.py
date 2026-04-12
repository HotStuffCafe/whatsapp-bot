import os
import json
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def get_all_item_names(menu):
    items = []
    for category in menu.values():
        for item in category:
            items.append(item["item"])
    return items


def parse_order_with_ai(message, menu_items):
    prompt = f"""
Extract order details.

Menu items:
{menu_items}

User message:
"{message}"

Return JSON ONLY:

{{
  "items": [
    {{"name": "", "quantity": 0}}
  ],
  "address": ""
}}

Rules:
- Multiple items allowed
- Match item names with menu
- Quantity must be number
- Address includes shop, room, flat, office, etc.
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    try:
        return json.loads(response.choices[0].message.content)
    except:
        return {}


def handle_order(user_msg, session, menu):

    if user_msg in ["hi", "hello", "menu", "back", "show menu"]:
        return "❓"

    if "order" not in session:
        session["order"] = {
            "items": [],
            "address": None
        }

    order = session["order"]

    menu_items = get_all_item_names(menu)
    parsed = parse_order_with_ai(user_msg, menu_items)

    # Update items
    if parsed.get("items"):
        for new_item in parsed["items"]:
            name = new_item.get("name")
            qty = new_item.get("quantity")

            if not name or not qty:
                continue

            found = False
            for item in order["items"]:
                if item["name"].lower() == name.lower():
                    item["quantity"] += int(qty)
                    found = True
                    break

            if not found:
                order["items"].append({
                    "name": name,
                    "quantity": int(qty)
                })

    # Update address (AI)
    if parsed.get("address"):
        order["address"] = parsed["address"]

    # Fallback address detection
    if not order["address"]:
        if any(word in user_msg.lower() for word in ["shop", "room", "flat", "office", "sector"]):
            order["address"] = user_msg

    # Validation
    if not order["items"]:
        return "❓ What would you like to order?"

    if not order["address"]:
        return "📍 Please share your delivery address."

    # Calculate total
    total = 0
    breakdown = ""

    for order_item in order["items"]:
        name = order_item["name"]
        qty = order_item["quantity"]

        price = 0
        for category in menu.values():
            for item in category:
                if item["item"].lower() == name.lower():
                    price = item["price"]

        item_total = price * qty
        total += item_total

        breakdown += f"{name} x {qty} = ₹{item_total}\n"

    return f"""
🧾 *Your Order*

{breakdown}

💰 Total: ₹{total}

📍 Address: {order['address']}

✅ Reply YES to confirm or NO to cancel
"""
