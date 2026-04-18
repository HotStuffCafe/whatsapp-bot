import razorpay
import os

client = razorpay.Client(auth=(
    os.getenv("RAZORPAY_KEY_ID"),
    os.getenv("RAZORPAY_KEY_SECRET")
))

def create_payment_link(order_id, amount, customer_name, customer_phone):
    try:
        payment = client.payment_link.create({
            "amount": int(amount * 100),
            "currency": "INR",
            "description": f"Order #{order_id}",
            "customer": {
                "name": customer_name,
                "contact": customer_phone
            },
            "notify": {
                "sms": True,
                "email": False
            },
            "notes": {
                "order_id": str(order_id)
            },

            # 🔥 NEW ADDITION
            "callback_url": "https://whatsapp-bot-34e7.onrender.com/payment/redirect",
            "callback_method": "get"
        })

        return payment.get("short_url")

    except Exception as e:
        print("❌ Payment link error:", str(e))
        return None
