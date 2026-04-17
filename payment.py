import razorpay
import os
from sheet_update import save_order_to_sheet

client = razorpay.Client(auth=(
    os.getenv("RAZORPAY_KEY_ID"),
    os.getenv("RAZORPAY_KEY_SECRET")
))


# =========================
# CALCULATE TOTAL
# =========================
def calculate_total(order, menu):

    total = 0

    for item in order["items"]:
        name = item["name"]
        qty = item["quantity"]

        for cat in menu.values():
            for i in cat:
                if i["item"].lower() == name.lower():
                    total += i["price"] * qty

    return total


# =========================
# CREATE PAYMENT LINK
# =========================
def create_payment_link(amount, user_number, order_id):

    data = {
        "amount": int(amount * 100),  # in paisa
        "currency": "INR",
        "accept_partial": False,
        "description": f"Order {order_id}",
        "customer": {
            "contact": user_number.replace("whatsapp:", "")
        },
        "notify": {
            "sms": True,
            "email": False
        },
        "reminder_enable": True
    }

    link = client.payment_link.create(data)

    return link["short_url"]


# =========================
# PAYMENT HANDLER
# =========================
def handle_payment(user_msg, session, menu):

    msg = user_msg.lower()

    if not session.get("awaiting_payment"):
        return None

    order = session.get("order")
    order_id = session.get("order_id")

    # =========================
    # PAYMENT LINK FLOW
    # =========================
    if msg == "upi":

        total_amount = calculate_total(order, menu)

        payment_link = create_payment_link(
            total_amount,
            session.get("user_number"),
            order_id
        )

        session["payment_mode"] = "UPI"

        return f"""💳 Payment Link

Pay here:
{payment_link}

After payment, type *PAID*
"""

    # =========================
    # COD FLOW
    # =========================
    if msg == "cod":

        save_order_to_sheet(
            order_id=order_id,
            order=order,
            user_number=session.get("user_number"),
            menu=menu,
            payment_mode="COD",
            payment_status="na"
        )

        session.clear()

        return f"""✅ Order Confirmed!

🆔 Order ID: {order_id}

💰 Payment Mode: COD
"""

    # =========================
    # CONFIRM PAYMENT
    # =========================
    if msg == "paid":

        if session.get("payment_mode") != "UPI":
            return "❌ Please choose UPI first."

        save_order_to_sheet(
            order_id=order_id,
            order=order,
            user_number=session.get("user_number"),
            menu=menu,
            payment_mode="UPI",
            payment_status="Success"
        )

        session.clear()

        return f"""✅ Payment Received!

🆔 Order ID: {order_id}

🎉 Your order is confirmed!"""

    return "👉 Please choose payment method: *UPI* or *COD*"
