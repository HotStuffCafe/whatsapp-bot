# main.py

from flask import Flask, request, jsonify
import os

app = Flask(__name__)


# ================================
# 🔥 EXISTING ROUTES (UNCHANGED)
# ================================
# Your WhatsApp webhook / bot logic remains exactly same
# DO NOT TOUCH EXISTING MESSAGE HANDLER


# ================================
# 💳 PAYMENT WEBHOOK (NEW ADDITION)
# ================================
@app.route('/payment/callback', methods=['POST'])
def payment_callback():
    data = request.json

    print("🔔 Razorpay Webhook Received:", data)

    event = data.get("event")

    try:
        payment = data["payload"]["payment"]["entity"]

        razorpay_payment_id = payment.get("id")
        order_id = payment.get("notes", {}).get("order_id")

        if not order_id:
            print("❌ No order_id found in webhook")
            return jsonify({"status": "ignored"})

        if event == "payment.captured":
            print(f"✅ Payment SUCCESS for order {order_id}")

            update_order_status(order_id, "CONFIRMED")

            phone = get_user_phone(order_id)

            send_whatsapp_message(
                phone,
                "✅ Payment received! Your order is confirmed and being prepared."
            )

        elif event == "payment.failed":
            print(f"❌ Payment FAILED for order {order_id}")

            update_order_status(order_id, "FAILED")

            phone = get_user_phone(order_id)

            send_whatsapp_message(
                phone,
                "❌ Payment failed. Please try again."
            )

    except Exception as e:
        print("Webhook error:", str(e))

    return jsonify({"status": "ok"})


# ================================
# ⚠️ EXISTING FUNCTIONS (REUSE)
# ================================

def update_order_status(order_id, status):
    # your existing implementation
    pass


def get_user_phone(order_id):
    # fetch from your DB / sheet
    return "user_phone_here"


def send_whatsapp_message(phone, message):
    # your existing Twilio / WhatsApp logic
    pass


# ================================
# 🚀 RUN APP
# ================================
if __name__ == "__main__":
    app.run(debug=True)
