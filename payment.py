import os
from sheet_update import save_order_to_sheet


# =========================
# PAYMENT HANDLER
# =========================
def handle_payment(user_msg, session, menu):

    msg = user_msg.lower()

    # Check if waiting for payment choice
    if not session.get("awaiting_payment"):
        return None

    order = session.get("order")
    order_id = session.get("order_id")

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
    # UPI FLOW
    # =========================
    if msg == "upi":

        # Example UPI link (replace later with real one)
        upi_link = "upi://pay?pa=yourupi@bank&pn=YourStore&am=0&cu=INR"

        session["payment_mode"] = "UPI"

        return f"""💳 UPI Payment

Click below to pay:

{upi_link}

After payment, type *PAID*
"""

    # =========================
    # PAYMENT CONFIRMATION
    # =========================
    if msg == "paid":

        if session.get("payment_mode") != "UPI":
            return "❌ Please select UPI first."

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

🎉 Your order is confirmed!
"""

    return "❓ Please choose: UPI or COD"
