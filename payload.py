import os
import json
import base64
import gspread
from datetime import datetime
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


def _connect_payload_sheet():
    creds = _load_google_creds()
    client = gspread.authorize(creds)

    sheet_id = os.getenv("ORDER_SHEET_ID")
    sheet_name = os.getenv("ORDER_SHEET_NAME", "ORDER")
    payload_ws_name = os.getenv("PAYLOAD_WORKSHEET", "PAYLOAD")

    spreadsheet = client.open_by_key(sheet_id) if sheet_id else client.open(sheet_name)

    try:
        worksheet = spreadsheet.worksheet(payload_ws_name)
    except Exception:
        worksheet = spreadsheet.add_worksheet(title=payload_ws_name, rows=2000, cols=20)
        worksheet.append_row([
            "timestamp",
            "order_id",
            "payment_id",
            "payment_link_id",
            "reference_id",
            "payment_link_status",
            "signature",
            "raw_url",
            "raw_params_json"
        ])

    return worksheet


def save_payload_to_sheet(query_params, raw_url=""):
    try:
        worksheet = _connect_payload_sheet()

        row = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            query_params.get("razorpay_payment_link_reference_id", ""),
            query_params.get("razorpay_payment_id", ""),
            query_params.get("razorpay_payment_link_id", ""),
            query_params.get("razorpay_payment_link_reference_id", ""),
            query_params.get("razorpay_payment_link_status", ""),
            query_params.get("razorpay_signature", ""),
            raw_url,
            json.dumps(query_params, ensure_ascii=False)
        ]

        worksheet.append_row(row)
        print("✅ Callback payload appended to PAYLOAD sheet")
        return "success"
    except Exception as e:
        print("❌ PAYLOAD sheet update error:", str(e))
        return "error"
