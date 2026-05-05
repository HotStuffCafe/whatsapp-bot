import os
import re
import json
import base64
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# ==========================================
# 🔐 ADMIN AUTHENTICATION
# ==========================================
def get_admin_numbers():
    numbers_str = os.getenv("ADMIN_NUMBERS", "")
    return [n.strip() for n in numbers_str.split(",") if n.strip()]

def is_admin(user_number):
    if not user_number:
        return False
    admins = get_admin_numbers()
    user_num_clean = user_number.replace("whatsapp:", "").strip()
    admin_clean = [a.replace("whatsapp:", "").strip() for a in admins]
    return user_num_clean in admin_clean

# ==========================================
# 📊 GOOGLE SHEETS CONNECTION
# ==========================================
def _get_worksheet(worksheet_name):
    creds_json = os.getenv("GOOGLE_CREDS_JSON")
    try:
        creds_dict = json.loads(creds_json)
    except:
        creds_dict = json.loads(base64.b64decode(creds_json).decode("utf-8"))
        
    if "private_key" in creds_dict:
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        
    creds = Credentials.from_service_account_info(creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    client = gspread.authorize(creds)
    sheet_id = os.getenv("ORDER_SHEET_ID")
    return client.open_by_key(sheet_id).worksheet(worksheet_name)

# ==========================================
# 🛠️ MENU MANAGEMENT
# ==========================================
def handle_menu_updates(msg):
    # Command examples: 
    # add item | Pizza | Margherita | 199
    # delete item | Margherita
    # update price | Margherita | 249
    
    parts = [p.strip() for p in msg.split("|")]
    command = parts[0].lower()
    
    try:
        ws = _get_worksheet("MENU") # Ensure your menu sheet is exactly named "MENU"
        records = ws.get_all_records()
        
        if command == "add item" and len(parts) == 4:
            cat, name, price = parts[1], parts[2], parts[3]
            ws.append_row([cat, name, price])
            return f"✅ Added {name} to {cat} for ₹{price}."
            
        elif command == "delete item" and len(parts) == 2:
            target_name = parts[1].lower()
            for i, row in enumerate(records, start=2): # +2 for header and 0-index offset
                if str(row.get("Item Name", "")).strip().lower() == target_name:
                    ws.delete_rows(i)
                    return f"🗑️ Deleted {parts[1]} from the menu."
            return "❌ Item not found."
            
        elif command == "update price" and len(parts) == 3:
            target_name, new_price = parts[1].lower(), parts[2]
            for i, row in enumerate(records, start=2):
                if str(row.get("Item Name", "")).strip().lower() == target_name:
                    ws.update_cell(i, 3, new_price) # Assuming Price is column 3 (C)
                    return f"✅ Updated {parts[1]} price to ₹{new_price}."
            return "❌ Item not found."
            
    except Exception as e:
        print("Menu Update Error:", e)
        return "❌ Failed to update menu. Please check format."
        
    return "❌ Invalid command format.\nUse:\nadd item | Cat | Name | Price\ndelete item | Name\nupdate price | Name | Price"

# ==========================================
# 📈 SALES SUMMARY
# ==========================================
def handle_sales_summary(msg):
    try:
        ws = _get_worksheet(os.getenv("ORDER_WORKSHEET", "ORDER"))
        rows = ws.get_all_records()
        
        filtered_rows = []
        today_str = datetime.now().strftime("%d/%m/%Y") # Make sure your order sheet date matches this format!
        month_str = datetime.now().strftime("/%m/%Y")
        
        period_name = "Custom Range"
        
        if "today" in msg:
            filtered_rows = [r for r in rows if today_str in str(r.get("Date", ""))]
            period_name = "Today"
        elif "month" in msg:
            filtered_rows = [r for r in rows if month_str in str(r.get("Date", ""))]
            period_name = "This Month"
        else:
            # Extract dates: sales summary 01/05/2026 to 10/05/2026
            match = re.search(r"(\d{2}[-/]\d{2}[-/]\d{4}).*to.*(\d{2}[-/]\d{2}[-/]\d{4})", msg)
            if match:
                start_date = datetime.strptime(match.group(1).replace("-", "/"), "%d/%m/%Y")
                end_date = datetime.strptime(match.group(2).replace("-", "/"), "%d/%m/%Y")
                period_name = f"{match.group(1)} to {match.group(2)}"
                
                for r in rows:
                    try:
                        row_date_str = str(r.get("Date", "")).split()[0].replace("-", "/")
                        row_date = datetime.strptime(row_date_str, "%d/%m/%Y")
                        if start_date <= row_date <= end_date:
                            filtered_rows.append(r)
                    except: continue
            else:
                return "❌ Invalid date format. Use: sales summary DD/MM/YYYY to DD/MM/YYYY"

        # Tally Sales & Items
        sales = {"UPI": 0, "Net Banking": 0, "COD": 0, "Pending": 0}
        item_counts = {}

        for row in filtered_rows:
            status = str(row.get("Payment Status", "")).strip().lower()
            mode = str(row.get("Payment Mode", "")).strip().upper()
            total = float(row.get("Total Amount", 0) or 0)
            
            # Tally Revenue
            if status in ["success", "paid"]:
                if mode == "UPI": sales["UPI"] += total
                elif mode in ["NET BANKING", "NB"]: sales["Net Banking"] += total
                elif mode == "COD": sales["COD"] += total
                else: sales["UPI"] += total # Fallback
            else:
                sales["Pending"] += total

            # Tally Items (Only for successful orders)
            if status in ["success", "paid"]:
                cart_raw = str(row.get("Cart", "") or row.get("Items", "")) # Assumes items are comma separated
                items_list = cart_raw.split(",")
                for item_str in items_list:
                    match = re.search(r"(.*?)\s*[xX*]\s*(\d+)", item_str.strip())
                    if match:
                        name = match.group(1).strip()
                        qty = int(match.group(2))
                        item_counts[name] = item_counts.get(name, 0) + qty

        # Build Report
        total_revenue = sales["UPI"] + sales["Net Banking"] + sales["COD"]
        
        report = f"📊 *Sales Summary: {period_name}*\n\n"
        
        report += "💰 *Revenue by Mode:*\n"
        report += f"• UPI: ₹{sales['UPI']}\n"
        report += f"• Net Banking: ₹{sales['Net Banking']}\n"
        report += f"• COD: ₹{sales['COD']}\n"
        report += f"✅ *Total Received:* ₹{total_revenue}\n"
        report += f"⏳ *Pending Payments:* ₹{sales['Pending']}\n\n"
        
        report += "🍔 *Item-Wise Sales:*\n"
        sorted_items = sorted(item_counts.items(), key=lambda x: x[1], reverse=True)
        for name, qty in sorted_items:
            report += f"• {name} | Qty: {qty}\n"
            
        if not sorted_items:
            report += "No items sold in this period."

        return report

    except Exception as e:
        print("Summary Error:", e)
        return "❌ Failed to generate report. Check logs."

# ==========================================
# 🧠 MAIN ADMIN ROUTER
# ==========================================
def handle_admin_command(user_msg, user_number):
    if not is_admin(user_number):
        return None

    msg = user_msg.lower().strip()

    # 1. View Commands
    if msg in ["admin menu", "admin"]:
        return """👨‍💻 *Admin Dashboard*

*1. View Menu:*
Reply: `view items`

*2. Update Menu:*
`add item | Category | Name | Price`
`delete item | Name`
`update price | Name | NewPrice`

*3. Reports:*
`sales summary today`
`sales summary month`
`sales summary DD/MM/YYYY to DD/MM/YYYY`

ℹ️ Type *get commands* for a detailed explanation of what each command does."""

    if msg == "get commands":
        return """📖 *Admin Commands Cheat Sheet*

📋 *MENU MANAGEMENT*
• *view items* : Shows the complete active menu with Categories, Names, and Prices.
• *add item | Cat | Name | Price* : Instantly adds a new item to the Google Sheet. (e.g., `add item | Pizza | Paneer Tikka | 250`)
• *delete item | Name* : Removes an item entirely from the menu. (e.g., `delete item | Paneer Tikka`)
• *update price | Name | Price* : Changes the price of an existing item. (e.g., `update price | Margherita | 299`)

📊 *SALES & REPORTS*
• *sales summary today* : Shows total revenue (split by UPI, Net Banking, COD, Pending) and a list of items sold today.
• *sales summary month* : Shows the exact same report, but tallied for the entire current month.
• *sales summary DD/MM/YYYY to DD/MM/YYYY* : Generates a report for a specific date range. (e.g., `sales summary 01/05/2026 to 10/05/2026`)

*(Note: Menu updates may take 5-10 minutes to reflect for normal customers due to caching).*"""

    if msg == "view items":
        from menu import format_all_items, get_menu_data
        return format_all_items(get_menu_data())

    # 2. Update Commands
    if msg.startswith("add item") or msg.startswith("delete item") or msg.startswith("update price"):
        return handle_menu_updates(user_msg) # Pass original case for exact naming

    # 3. Report Commands
    if msg.startswith("sales summary"):
        return handle_sales_summary(msg)

    return None
