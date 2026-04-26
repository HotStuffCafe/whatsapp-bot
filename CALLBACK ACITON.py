import os
import json
import base64
import requests
import gspread
from google.oauth2.service_account import Credentials


def _load_google_creds():
    creds_json = os.getenv("GOOGLE_CREDS_JSON")
    creds_path = os.getenv("GOOGLE_CREDS_FILE") or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    if creds_json:
        try:
            creds_dict = json.loads(creds_json)
        except json.JSONDecodeError:
            decoded = base64.b64decode(creds_json).decode("utf-8")
            creds_dict = json.loads(decoded)
    elif creds_path and os.path.exists(creds_path):
        with open(creds_path, "r", encoding="utf-8") as f:
            creds_dict = json.load(f)
    else:
        raise ValueError("GOOGLE_CREDS_JSON / GOOGLE_CREDS_FILE not found")

    if "private_key" in creds_dict:
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    return Credentials.from_service_account_info(creds_dict, scopes=scopes)


def _open_spreadsheet():
    creds = _load_google_creds()
    client = gspread.authorize(creds)
    sheet_id = os.getenv("ORDER_SHEET_ID")
    sheet_name = os.getenv("ORDER_SHEET_NAME", "ORDER")
    return client.open_by_key(sheet_id) if sheet_id else client.open(sheet_name)


def _get_latest_payment_status(order_id):
    spreadsheet = _open_spreadsheet()
    payload_ws = os.getenv("PAYLOAD_WORKSHEET", "PAYLOAD")
    worksheet = spreadsheet.worksheet(payload_ws)
    rows = worksheet.get_all_values()

    # Header format:
    # timestamp, order_id, payment_id, payment_link_id, reference_id, payment_link_status, ...
    latest_status = ""
    latest_payment_id = ""
    for row in reversed(rows[1:]):
        if len(row) < 6:
            continue
        if row[1].strip() == order_id:
            latest_payment_id = row[2].strip() if len(row) > 2 else ""
            latest_status = row[5].strip().lower()
            break

    return latest_status, latest_payment_id


def _get_order_context(order_id):
    spreadsheet = _open_spreadsheet()
    order_ws = os.getenv("ORDER_WORKSHEET", "ORDER")
    worksheet = spreadsheet.worksheet(order_ws)
    rows = worksheet.get_all_values()

    phone = ""
    total = 0.0

    for row in rows[1:]:
        if len(row) < 7:
            continue
        if row[1].strip() != order_id:
            continue

        phone = phone or row[2].strip()
        try:
            total += float(row[6] or 0)
        except Exception:
            pass

    return phone, total


def send_whatsapp_message(to_number, message):
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_WHATSAPP_NUMBER")

    if not (account_sid and auth_token and from_number and to_number):
        print("⚠️ Missing Twilio env vars or target number. Skipping WhatsApp notify.")
        return False

    to_formatted = to_number if to_number.startswith("whatsapp:") else f"whatsapp:{to_number}"
    from_formatted = from_number if from_number.startswith("whatsapp:") else f"whatsapp:{from_number}"

    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
    payload = {
        "From": from_formatted,
        "To": to_formatted,
        "Body": message
    }

    try:
        resp = requests.post(url, data=payload, auth=(account_sid, auth_token), timeout=15)
        if 200 <= resp.status_code < 300:
            return True
        print("❌ Twilio send failed:", resp.status_code, resp.text)
        return False
    except Exception as e:
        print("❌ Twilio send exception:", str(e))
        return False


def handle_callback_action(order_id):
    if not order_id:
        return {"status": "no_order_id"}

    status, payment_id = _get_latest_payment_status(order_id)
    if not status:
        return {"status": "no_payload_status"}

    phone, total = _get_order_context(order_id)

    from payment import finalize_paid_order, create_payment_link, get_enable_payment_mode

    mode = get_enable_payment_mode()

    if status == "paid":
        finalize_paid_order(order_id, payment_id)
        send_whatsapp_message(
            phone,
            f"✅ Payment received.\n🆔 Order ID: {order_id}\nYour order is confirmed."
        )
        return {"status": "success_notified"}

    payment_link = create_payment_link(total, order_id, phone) if total > 0 else None

    if mode == "paycod":
        msg = (
            f"⚠️ Payment is not completed for Order ID {order_id} (status: {status}).\n"
            "Your order confirmation is pending.\n"
            "You can still confirm by replying *COD*."
        )
        if payment_link:
            msg += f"\n\nOr pay now using this link:\n{payment_link}"
        send_whatsapp_message(phone, msg)
        return {"status": "pending_notified_paycod"}

    # payonly / others
    msg = (
        f"⚠️ Payment is not completed for Order ID {order_id} (status: {status}).\n"
        "Your order confirmation is pending.\n"
        "Please complete payment to confirm your order."
    )
    if payment_link:
        msg += f"\n\nFresh payment link:\n{payment_link}"

    send_whatsapp_message(phone, msg)
    return {"status": "pending_notified_payonly"}
