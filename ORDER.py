import os
import openai
import json

openai.api_key = os.getenv("OPENAI_API_KEY")


# =========================
# AI PARSER (MULTI ITEM)
# =========================
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
- Match item names closely with menu
- Quantity must be number
"""

    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    try:
        return json.loads(response.choices[0].message.content)
    except:
        return {}


# =========================
# GET ALL ITEM NAMES
# =========================
def get_all_item_names(menu):
    items = []
    for category in menu.values():
        for item in category:
            items.append(item["item"])
    return items


# =========================
# HANDLE ORDER
# =========================
def handle_order(user_msg, session, menu):

    if "order" not in session:
        session["order"] = {
            "items": [],
            "address": None
        }

    order = session["order"]

    menu_items = get_all_item_names(menu)
    parsed = parse_order_with_ai(user_msg, menu_items)

    # =========================
    # UPDATE ITEMS
    # =========================
    if parsed.get("items"):
        for new_item in parsed["items"]:
            name = new_item.get("name")
            qty = new_item.get("quantity")

            if not name or not qty:
                continue

            # Check if already exists → update qty
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

    # =========================
    # UPDATE ADDRESS
    # =========================
    if parsed.get("address"):
        order["address"] = parsed["address"]

    # =========================
    # VALIDATION
    # =========================
    if not order["items"]:
        return "❓ What would you like to order?"

    if not order["address"]:
        return "📍 Please share your delivery address."

    # =========================
    # CALCULATE TOTAL
    # =========================
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

    # =========================
    # FINAL CONFIRMATION
    # =========================
    return f"""
🧾 *Your Order*

{breakdown}

💰 Total: ₹{total}

📍 Address: {order['address']}

✅ Reply YES to confirm or NO to cancel
"""
