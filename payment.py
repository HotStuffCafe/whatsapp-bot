import os
from sheet_update import save_order_to_sheet


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
# GENERATE UPI LINK
# =========================
def generate_upi_link(amount):

    upi_id = "vyapar.175692980981@hdfcbank"
    name = "HOT%20STUFF"

    return f"upi://pay?pa={upi_id}&pn={name}&am={amount}&cu=INR"


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
    # SEND PAYMENT LINK
    # =========================
    if msg in ["upi", "pay", "payment"]:

        total_amount = calculate_total(order, menu)

        upi_link = generate_upi_link(total_amount)

        session["payment_mode"] = "UPI"

        return f"""💳 *UPI Payment*

Click below to pay:

{upi_link}

👉 After payment, type *PAID*
"""

    # =========================
    # CONFIRM PAYMENT
    # =========================
    if msg == "paid":

        if session.get("payment_mode") != "UPI":
            return "❌ Please click payment link first."

        save_order_to_sheet(
            order_id=order_id,
            order=order,
            user_number=session.get("user_number"),
            menu=menu,
            payment_mode="UPI",
            payment_status="Success"
        )

        session.clear()

        return f"""✅ *Payment Received!*

🆔 Order ID: {order_id}

🎉 Your order is confirmed!"""

    # =========================
    # FALLBACK MESSAGE
    # =========================
    return "👉 Please type *UPI* to make payment"
