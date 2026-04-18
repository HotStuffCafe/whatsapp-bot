import razorpay
import os

client = razorpay.Client(auth=(
    os.getenv("RAZORPAY_KEY_ID"),
    os.getenv("RAZORPAY_KEY_SECRET")
))


def calculate_total(order, menu):
    total = 0
    for item in order["items"]:
        for cat in menu.values():
            for i in cat:
                if i["item"].lower() == item["name"].lower():
                    total += i["price"] * item["quantity"]
    return total


def create_payment_link(order, menu, order_id, phone):

    amount = calculate_total(order, menu)

    data = {
        "amount": int(amount * 100),
        "currency": "INR",
        "description": f"Order {order_id}",
        "customer": {
            "contact": phone.replace("whatsapp:", "")
        },
        "notify": {"sms": True},
        "callback_url": "https://whatsapp-bot-34e7.onrender.com/payment/callback_uat1.1",
        "callback_method": "get"
    }

    link = client.payment_link.create(data)

    return link["short_url"]
