import razorpay
import os

client = razorpay.Client(auth=(
    os.getenv("RAZORPAY_KEY_ID"),
    os.getenv("RAZORPAY_KEY_SECRET")
))

def create_payment_link(order_id, amount, customer_name, customer_phone):
    try:
        payment = client.payment_link.create({
            "amount": int(amount * 100),  # convert to paise
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
                "order_id": order_id
            }
        })

        return payment["short_url"]

    except Exception as e:
        print("Payment link error:", str(e))
        return None
