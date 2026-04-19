import os
import requests
from sheet_update import update_google_sheet


# =========================
# 🔑 ENV VARIABLES
# =========================
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")


# =========================
# 💳 CREATE PAYMENT LINK
# =========================
def create_payment_link(amount, order_id, phone):

    url = "https://api.razorpay.com/v1/payment_links"

    payload = {
        "amount": int(amount * 100),  # paisa
        "currency": "INR",
        "description": f"Order {order_id}",
        "customer": {
            "contact": phone.replace("whatsapp:", "") if phone else ""
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

    try:
        response = requests.post(
            url,
            json=payload,
            auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)
        )

        data = response.json()

        if "short_url" in data:
            return data["short_url"]
        else:
            print("❌ Razorpay Error:", data)
            return None

    except Exception as e:
        print("❌ Payment Link Exception:", str(e))
        return None


# =========================
# 💳 HANDLE PAYMENT FLOW
# =========================
def handle_payment(user_msg, session, menu):

    msg = user_msg.lower().strip()

    if not session.get("awaiting_payment"):
        return None

    order_id = session.get("order_id")
    total = session.get("total")

    # =========================
    # 💳 PAY ONLINE
    # =========================
    if msg in ["pay", "upi"]:

        link = create_payment_link(
            total,
            order_id,
            session.get("user_number")
        )

        if link:
            return f"""💳 Payment Link

Pay here:
{link}

👉 Complete payment to confirm order"""
        else:
            return "❌ Payment link failed. Try again."

    # =========================
    # 💵 COD OPTION
    # =========================
    if msg == "cod":

        update_google_sheet(
            session,
            order_id,
            "COD",
            "Success"
        )

        session.clear()

        return f"""✅ Order Confirmed!

🆔 Order ID: {order_id}
💰 Payment Mode: COD"""

    return None


# =========================
# 🔔 HANDLE WEBHOOK CALLBACK
# =========================
def handle_payment_callback(data):

    try:
        event = data.get("event")

        # Only process successful payment
        if event != "payment_link.paid":
            return "ignored"

        payload = data.get("payload", {})
        entity = payload.get("payment_link", {}).get("entity", {})

        order_id = entity.get("notes", {}).get("order_id")

        if not order_id:
            return "no order id"

        print(f"✅ Payment Success for Order: {order_id}")

        # ⚠️ IMPORTANT:
        # We currently DON'T have session here
        # So we only log success
        # Next step → persistent storage (we’ll fix later)

        return "success"

    except Exception as e:
        print("❌ Webhook Error:", str(e))
        return "error"