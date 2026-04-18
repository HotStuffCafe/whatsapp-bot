import os
import requests
from sheet_update import save_order_to_sheet
from ORDER import order_store

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

PAYMENT_MODE = os.getenv("PAYMENT_MODE", "OFF")

# =========================
# 💳 CREATE RAZORPAY PAYMENT LINK
# =========================
def create_payment_link(order_id, amount, customer_phone):

    url = "https://api.razorpay.com/v1/payment_links"

    payload = {
        "amount": int(amount * 100),  # in paise
        "currency": "INR",
        "description": f"Order {order_id}",
        "customer": {
            "contact": customer_phone
        },
        "notify": {
            "sms": True,
            "email": False
        },
        "reminder_enable": True,
        "notes": {
            "order_id": order_id
        },
        "callback_url": "https://whatsapp-bot-34e7.onrender.com/payment/callback_uat1.1",
        "callback_method": "get"
    }

    response = requests.post(
        url,
        json=payload,
        auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)
    )

    if response.status_code == 200 or response.status_code == 201:
        return response.json().get("short_url")

    return None


# =========================
# 🧾 CALCULATE TOTAL
# =========================
def calculate_total(order, menu):
    total = 0

    for item in order["items"]:
        for category in menu.values():
            for m in category:
                if m["item"] == item["name"]:
                    total += m["price"] * item["quantity"]

    return total


# =========================
# 💰 HANDLE PAYMENT FLOW
# =========================
def handle_payment(user_msg, session, menu):

    msg = user_msg.lower().strip()

    if not session.get("awaiting_payment"):
        return None

    order_id = session.get("order_id")
    order = order_store.get(order_id)

    if not order:
        return "❌ Order not found. Please place order again."

    # =========================
    # 💳 PAY FLOW
    # =========================
    if msg == "pay":

        total = calculate_total(order, menu)

        payment_link = create_payment_link(
            order_id,
            total,
            session.get("user_number", "")
        )

        if not payment_link:
            return "❌ Payment link failed. Try again."

        session["payment_link"] = payment_link

        return f"""💳 Complete your payment:

{payment_link}

⚠️ After payment, you will receive confirmation."""

    # =========================
    # 💵 COD FLOW
    # =========================
    if msg == "cod":

        save_order_to_sheet(
            order_id,
            order,
            session["user_number"],
            menu,
            "COD",
            "Pending"
        )

        session.clear()

        return f"""✅ Order Confirmed!

🆔 Order ID: {order_id}

💵 Payment Mode: COD"""

    return None


# =========================
# 🔔 WEBHOOK HANDLER (IMPORTANT)
# =========================
def handle_payment_callback(data):

    try:
        event = data.get("event")

        if event != "payment_link.paid":
            return "ignored"

        payload = data.get("payload", {})
        payment_entity = payload.get("payment_link", {}).get("entity", {})

        order_id = payment_entity.get("notes", {}).get("order_id")

        if not order_id:
            return "no order id"

        order = order_store.get(order_id)

        if not order:
            return "order not found"

        # Save to Google Sheet
        save_order_to_sheet(
            order_id,
            order,
            "",  # phone not available here
            {},  # menu not needed here
            "UPI",
            "Success"
        )

        return "success"

    except Exception as e:
        print("Webhook Error:", str(e))
        return "error"
