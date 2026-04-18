# ORDER.py

import os
from payment import create_payment_link

ENABLE_PAYMENT = os.getenv("ENABLE_PAYMENT", "false").lower() == "true"


def process_order(order_id, user_name, user_phone, total_amount):
    """
    This function should be called after order is created.
    Keep your existing order creation logic untouched.
    """

    try:
        # 🔥 PAYMENT FLOW
        if ENABLE_PAYMENT:
            payment_link = create_payment_link(
                order_id=order_id,
                amount=total_amount,
                customer_name=user_name,
                customer_phone=user_phone
            )

            # 👉 DO NOT confirm yet
            update_order_status(order_id, "PENDING_PAYMENT")

            send_whatsapp_message(
                user_phone,
                f"""🧾 Order Created!

To confirm your order, please complete payment:
{payment_link}

Once paid, your order will be confirmed automatically."""
            )

        else:
            # ✅ OLD FLOW (UNCHANGED)
            update_order_status(order_id, "CONFIRMED")

            send_whatsapp_message(
                user_phone,
                "✅ Order confirmed! Preparing your food."
            )

    except Exception as e:
        print("Order processing error:", str(e))


# ⚠️ KEEP THESE FUNCTIONS AS-IS (already exist in your system)
def update_order_status(order_id, status):
    # existing implementation
    pass


def send_whatsapp_message(phone, message):
    # existing implementation
    pass
