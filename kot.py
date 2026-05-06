import os
import importlib.util
import re
import json
import base64
import requests
import gspread
from google.oauth2.service_account import Credentials

# ==========================================
# 👨‍🍳 KOT CONFIG & ALERTS
# ==========================================
def get_whatsapp_sender():
    module_path = os.path.join(os.path.dirname(__file__), "CALLBACK ACITON.py")
    spec = importlib.util.spec_from_file_location("callback_module", module_path)
    callback_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(callback_module)
    return callback_module.send_whatsapp_message

def get_kot_numbers():
    numbers_str = os.getenv("KOT_NUMBERS", "")
    if not numbers_str:
        return []
    return [n.strip() for n in numbers_str.split(",") if n.strip()]

def is_kot(user_number):
    if not user_number:
        return False
    kot_nums = get_kot_numbers()
    user_clean = user_number.replace("whatsapp:", "").strip()
    kot_clean = [n.replace("whatsapp:", "").strip() for n in kot_nums]
    return user_clean in kot_clean

def send_kot_to_kitchen(order_id, cart, address, total, payment_mode):
    kot_numbers = get_kot_numbers()
    if not kot_numbers:
        print("⚠️ No KOT numbers found in environment variables. Skipping kitchen notification.")
        return

    items_text = ""
    for item, data in cart.items():
        qty = data.get("qty", 1)
        items_text += f"🔸 {qty} x {item}\n"

    kot_msg = (
        f"👨‍🍳 *NEW KITCHEN ORDER* 👨‍🍳\n\n"
        f"🆔 *Order ID:* {order_id}\n"
        f"💰 *Mode:* {payment_mode}\n"
        f"💵 *Value:* ₹{total}\n\n"
        f"🧾 *Items:*\n{items_text}\n"
        f"📍 *Address:*\n{address}"
    )
    
    # Add a helpful hint for COD orders
    if payment_mode.upper() in ["CASH ON DELIVERY", "COD"]:
        kot_msg += "\n\n*(Reply to this message with 'R' or 'Payment received' to confirm payment)*"

    send_msg = get_whatsapp_sender()
    
    for number in kot_numbers:
        target = number if number.startswith("whatsapp:") else f"whatsapp:{number}"
        success = send_msg(target, kot_msg)
        if success:
            print(f"✅ KOT sent to {target}")
        else:
            print(f"❌ Failed to send KOT to {target}")


# ==========================================
# 🔄 KOT STATUS UPDATE HANDLER
# ==========================================
def _get_order_worksheet():
    creds_json = os.getenv("GOOGLE_CREDS_JSON")
    try:
        creds_dict = json.loads(creds_json)
    except:
        creds_dict = json.loads(base64.b64decode(creds_json).decode("utf-8"))
    if "private_key" in creds_dict:
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
    creds = Credentials.from_service_account_info(creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    client = gspread.authorize(creds)
    return client.open_by_key(os.getenv("ORDER_SHEET_ID")).worksheet(os.getenv("ORDER_WORKSHEET", "ORDER"))

def get_replied_message_body(message_sid):
    # Uses Twilio API to pull the text of the message the user swipe-replied to
    sid = os.getenv("TWILIO_ACCOUNT_SID")
    token = os.getenv("TWILIO_AUTH_TOKEN")
    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages/{message_sid}.json"
    try:
        resp = requests.get(url, auth=(sid, token), timeout=10)
        if resp.status_code == 200:
            return resp.json().get("body", "")
    except Exception as e:
        print("Twilio fetch error:", e)
    return ""

def handle_kot_command(user_msg, request_data):
    msg_lower = user_msg.lower().strip()

    # Define acceptable triggers
    is_received = msg_lower in ["r", "payment received", "received"] or msg_lower.startswith("r ")
    is_pending = msg_lower in ["p", "payment pending", "pending"] or msg_lower.startswith("p ")

    if not (is_received or is_pending):
        return None # Ignore normal chatter from KOT numbers

    # 1. Check if they typed the Order ID directly (e.g., "R ORD12345")
    match = re.search(r"(ord\d+)", msg_lower)
    order_id = match.group(1).upper() if match else None

    # 2. If not typed, check if they used WhatsApp's "Swipe to Reply" feature
    if not order_id:
        replied_sid = request_data.get("OriginalRepliedMessageSid")
        if replied_sid:
            original_text = get_replied_message_body(replied_sid)
            match = re.search(r"(ORD\d+)", original_text)
            if match:
                order_id = match.group(1).upper()

    if not order_id:
        return "⚠️ Could not detect Order ID. Please swipe-reply directly to the specific order ticket, or type it like: *R ORD123456*"

    new_status = "Success" if is_received else "Pending"

    # 3. Update the Google Sheet
    try:
        ws = _get_order_worksheet()
        records = ws.get_all_records()
        header = ws.row_values(1)
        
        try:
            status_col = header.index("Payment Status") + 1
        except ValueError:
            return "❌ 'Payment Status' column missing in sheet."

        updated_count = 0
        for i, row in enumerate(records, start=2):
            if str(row.get("Order ID", "")).strip().upper() == order_id:
                # Update the cell specifically in the status column
                ws.update_cell(i, status_col, new_status)
                updated_count += 1
        
        if updated_count > 0:
            return f"✅ COD Payment for {order_id} marked as *{new_status}*."
        else:
            return f"❌ Order {order_id} not found."
            
    except Exception as e:
        print("KOT Update Error:", e)
        return "❌ Failed to update status in Google Sheets."
