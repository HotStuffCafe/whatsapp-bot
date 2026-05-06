import requests
import os
import importlib.util
from copy import deepcopy
from sheet_update import update_google_sheet, mark_order_payment_success


# =========================
# 🔑 ENV VARIABLES
# =========================
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")
RAZORPAY_CALLBACK_URL = os.getenv(
    "RAZORPAY_CALLBACK_URL",
    "https://whatsapp-bot-34e7.onrender.com/payment/callback_uat1.1"
)

# In-memory payment order map (replace with DB/Redis in production)
PENDING_PAYMENT_ORDERS = {}

# Keep track of orders we have already notified to prevent spam
NOTIFIED_ORDERS = set()

def get_enable_payment_mode():
    return os.getenv("ENABLE_PAYMENT", "false").strip().lower()


# =========================
# 💳 CREATE PAYMENT LINK
# =========================
def create_payment_link(amount, order_id, phone):

    url = "https://api.razorpay.com/v1/payment_links"

    payload = {
        "amount": int(amount * 100),  # convert to paisa
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
        "reference_id": order_id,
        "callback_url": RAZORPAY_CALLBACK_URL,
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

    # Only act if waiting for payment
    if not session.get("awaiting_payment"):
        return None

    order_id = session.get("order_id")
    total = session.get("total")

    # =========================
    # 💳 ONLINE PAYMENT
    # =========================
    if msg in ["pay", "upi"]:

        link = create_payment_link(
            total,
            order_id,
            session.get("user_number")
        )

        if link:
            PENDING_PAYMENT_ORDERS[order_id] = {
                "session": {
                    "cart": deepcopy(session.get("cart", {})),
                    "address": session.get("address", ""),
                    "user_number": session.get("user_number", ""),
                    "menu": deepcopy(menu)
                },
                "payment_mode": "UPI",
                "payment_status": "Pending"
            }

            # Persist pending row so callback can update even after process restart
            if session.get("pending_logged_order_id") != order_id:
                update_google_sheet(
                    session,
                    order_id,
                    "UPI",
                    "Pending"
                )
                session["pending_logged_order_id"] = order_id

            return f"""💳 Payment Link

Pay here:
{link}

👉 Complete payment to confirm your order"""
        else:
            return "❌ Payment link failed. Try again."

    # =========================
    # 💵 COD FLOW (only if enabled)
    # =========================
    if msg == "cod":
        enable_payment_mode = get_enable_payment_mode()
        if enable_payment_mode == "paycod":

            update_google_sheet(
                session,
                order_id,
                "COD",
                "Pending"
            )
            from kot import send_kot_to_kitchen
            send_kot_to_kitchen(
                order_id, 
                session.get("cart", {}), 
                session.get("address", ""), 
                session.get("total", 0), 
                "CASH ON DELIVERY"
            )
            session.clear()

            return f"""✅ Order Confirmed!

🆔 Order ID: {order_id}
💰 Payment Mode: COD"""

        else:
            return "❌ COD not available. Please type PAY to continue."

    return None


def finalize_paid_order(order_id, payment_id=""):
    # ==========================================
    # 🛑 NEW: DUPLICATE PREVENTION LOCK
    # ==========================================
    if order_id in NOTIFIED_ORDERS:
        print(f"⏩ Order {order_id} already confirmed and notified. Skipping duplicate.")
        return "already_processed"
        
    # Add to our memory bank so it doesn't get processed again!
    NOTIFIED_ORDERS.add(order_id)

    # ==========================================
    # 1. UPDATE GOOGLE SHEET
    # ==========================================
    order_data = PENDING_PAYMENT_ORDERS.pop(order_id, None)
    status_result = "error"

    if mark_order_payment_success(order_id):
        status_result = "success"
    elif not order_data:
        fallback_session = {
            "cart": {"ONLINE_PAYMENT": {"qty": 1, "price": 0}},
            "address": f"Razorpay Payment ID: {payment_id}" if payment_id else "Razorpay Payment",
            "user_number": "",
            "menu": {}
        }
        update_google_sheet(fallback_session, order_id, "UPI", "Success")
        status_result = "success_unreconciled_row_created"
    else:
        order_session = order_data["session"]
        update_google_sheet(order_session, order_id, "UPI", "Success")
        status_result = "success"

    # ==========================================
    # 2. LOAD YOUR WHATSAPP FUNCTIONS SAFELY
    # ==========================================
    callback_module_path = os.path.join(os.path.dirname(__file__), "CALLBACK ACITON.py")
    spec = importlib.util.spec_from_file_location("callback_action_module", callback_module_path)
    callback_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(callback_module)

    # ==========================================
    # 3. GET PHONE NUMBER
    # ==========================================
    phone = ""
    if order_data and order_data.get("session", {}).get("user_number"):
        phone = order_data["session"]["user_number"]
    else:
        phone, _ = callback_module._get_order_context(order_id)

    # ==========================================
    # 4. SEND THE SUCCESS NOTIFICATION
    # ==========================================
    if phone:
        # 1. Send the message to the customer (ONLY ONCE)
        success_msg = f"Order ID: {order_id}\nYour order is confirmed"
        callback_module.send_whatsapp_message(phone, success_msg)
        
        # 2. Trigger the KOT to the kitchen
        from kot import send_kot_to_kitchen
        if order_data and "session" in order_data:
            cart = order_data["session"].get("cart", {})
            address = order_data["session"].get("address", "")
            total = order_data["session"].get("total", 0)
            send_kot_to_kitchen(order_id, cart, address, total, "ONLINE PAID")
            
    else:
        print(f"⚠️ Could not find phone number to notify for Order: {order_id}")

    return status_result

# =========================
# 🔔 RAZORPAY WEBHOOK CALLBACK
# =========================
def handle_payment_callback(data):

    try:
        event = data.get("event")

        # Only process successful payment
        if event != "payment_link.paid":
            return "ignored"

        payload = data.get("payload", {})
        entity = payload.get("payment_link", {}).get("entity", {})

        order_id = (entity.get("notes", {}).get("order_id") or entity.get("reference_id") or "").strip()

        if not order_id:
            return "no order id"

        payment_id = payload.get("payment", {}).get("entity", {}).get("id", "")

        print(f"✅ Payment SUCCESS for Order: {order_id}")
        return finalize_paid_order(order_id, payment_id)

    except Exception as e:
        print("❌ Webhook Error:", str(e))
        return "error"


def handle_payment_callback_query(query_params):
    status = query_params.get("razorpay_payment_link_status", "")
    order_id = query_params.get("razorpay_payment_link_reference_id", "").strip()
    payment_id = query_params.get("razorpay_payment_id", "")

    if status != "paid":
        return "ignored"

    if not order_id:
        return "no order id"

    print(f"✅ Payment SUCCESS (GET callback) for Order: {order_id}")
    return finalize_paid_order(order_id, payment_id)
