import os
import json
import random
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def generate_order_id():
    return f"ORD{random.randint(1000,9999)}"


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
  "address": "",
  "action": "" 
}}

Actions:
- "add"
- "remove"
- "none"

Examples:
"add 2 chai" → add  
"remove 1 chai" → remove  
"2 pizza" → add  
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

    user_msg_lower = user_msg.lower()

    # =========================
    # ✅ CONFIRM ORDER
    # =========================
    if user_msg_lower == "yes":
        if "order" not in session or not session["order"]["items"]:
            return "❌ No active order."

        order = session["order"]
        order_id = generate_order_id()

        response = f"""
🎉 *Order Confirmed!*

🆔 Order ID: {order_id}

📦 Items:
"""

        for item in order["items"]:
            response += f"- {item['name']} x {item['quantity']}\n"

        response += f"""
📍 Address: {order['address']}

🙏 Thank you for your order!
"""

        # CLEAR SESSION
        session.clear()

        return response

    # =========================
    # ❌ CANCEL ORDER
    # =========================
    if user_msg_lower == "no":
        session.clear()
        return "❌ Your order has been cancelled."

    # =========================
    # SKIP FOR MENU COMMANDS
    # =========================
    if user_msg_lower in ["hi", "hello", "menu", "back", "show menu", "all items"]:
        return "❓"

    if "order" not in session:
        session["order"] = {
            "items": [],
            "address": None
        }

    order = session["order"]

    menu_items = get_all_item_names(menu)
    parsed = parse_order_with_ai(user_msg, menu_items)

    action = parsed.get("action", "add")

    # =========================
    # HANDLE ITEMS
    # =========================
    if parsed.get("items"):
        for new_item in parsed["items"]:
            name = new_item.get("name")
            qty = int(new_item.get("quantity", 0))

            if not name or qty <= 0:
                continue

            if action == "remove":
                for item in order["items"]:
                    if item["name"].lower() == name.lower():
                        item["quantity"] -= qty
                        if item["quantity"] <= 0:
                            order["items"].remove(item)
                        break

            else:  # ADD
                found = False
                for item in order["items"]:
                    if item["name"].lower() == name.lower():
                        item["quantity"] += qty
                        found = True
                        break

                if not found:
                    order["items"].append({
                        "name": name,
                        "quantity": qty
                    })

    # =========================
    # ADDRESS
    # =========================
    if parsed.get("address"):
        order["address"] = parsed["address"]

    if not order["address"]:
        if any(word in user_msg_lower for word in ["shop", "room", "flat", "office", "sector"]):
            order["address"] = user_msg

    # =========================
    # VALIDATION
    # =========================
    if not order["items"]:
        return "❓ What would you like to order?"

    if not order["address"]:
        return "📍 Please share your delivery address."

    # =========================
    # BUILD RESPONSE
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

    return f"""
🧾 *Your Order*

{breakdown}

💰 Total: ₹{total}

📍 Address: {order['address']}

✅ Reply YES to confirm or NO to cancel
"""
