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
    parts = [p.strip() for p in msg.split("|")]
    command = parts[0].lower()
    
    try:
        ws = _get_worksheet("MENU") 
        records = ws.get_all_records()
        
        if command == "add item" and len(parts) == 4:
            cat, name, price = parts[1], parts[2], parts[3]
            ws.append_row([cat, name, price])
            return f"✅ Added {name} to {cat} for ₹{price}."
            
        elif command == "delete item" and len(parts) == 2:
            target_name = parts[1].lower()
            for i, row in enumerate(records, start=2): 
                if str(row.get("Item Name", "")).strip().lower() == target_name:
                    ws.delete_rows(i)
                    return f"🗑️ Deleted {parts[1]} from the menu."
            return "❌ Item not found."
            
        elif command == "update price" and len(parts) == 3:
            target_name, new_price = parts[1].lower(), parts[2]
            for i, row in enumerate(records, start=2):
                if str(row.get("Item Name", "")).strip().lower() == target_name:
                    ws.update_cell(i, 3, new_price) 
                    return f"✅ Updated {parts[1]} price to ₹{new_price}."
            return "❌ Item not found."
            
    except Exception as e:
        print("Menu Update Error:", e)
        return "❌ Failed to update menu. Please check format."
        
    return "❌ Invalid command format."

# ==========================================
# 🚀 BULK MENU OVERWRITE
# ==========================================
def handle_bulk_menu_update(user_msg):
    try:
        # Split message into lines, skip the first line ("update items" / "update menu")
        lines = user_msg.strip().split('\n')[1:]
        new_rows = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Strip out numbering (e.g., "1. ", "2. ")
            clean_line = re.sub(r'^\d+\.\s*', '', line)
            parts = [p.strip() for p in clean_line.split('|')]
            
            if len(parts) >= 3:
                cat = parts[0]
                name = parts[1]
                # Clean the price string of any currency symbols
                price = parts[2].replace('₹', '').replace('rs', '').replace('Rs', '').strip()
                new_rows.append([cat, name, price])
                
        if not new_rows:
            return "❌ No valid items found. Format must be: 1. Category | Name | Price"
            
        # Connect to sheet, clear it, and overwrite
        ws = _get_worksheet("MENU")
        ws.clear()
        
        # Add Headers back
        headers = ["Category", "Item Name", "Price"]
        ws.append_row(headers)
        
        # Add the new parsed rows
        ws.append_rows(new_rows)
        
        return f"✅ Menu successfully completely overwritten with {len(new_rows)} items!"
        
    except Exception as e:
        print("Bulk Update Error:", e)
        return "❌ Failed to overwrite menu. Check server logs."

# ==========================================
# 📈 SALES SUMMARY
# ==========================================
def handle_sales_summary(msg):
    try:
        ws_order = _get_worksheet(os.getenv("ORDER_WORKSHEET", "ORDER"))
        raw_rows = ws_order.get_all_records()
        
        # 0. NORMALIZE HEADERS: Make all keys lowercase and replace underscores with spaces
        # e.g., 'item_name' becomes 'item name', 'payment_status' becomes 'payment status'
        rows = []
        for r in raw_rows:
            normalized_row = {str(k).strip().lower().replace("_", " "): v for k, v in r.items()}
            rows.append(normalized_row)
        
        # 1. Fetch current menu to map Items to Categories
        try:
            ws_menu = _get_worksheet("MENU")
            menu_records = ws_menu.get_all_records()
            item_details = {}
            for r in menu_records:
                name = str(r.get("Item Name", "")).strip().lower()
                cat = str(r.get("Category", "Uncategorized")).strip()
                item_details[name] = {"category": cat}
        except:
            item_details = {} 

        # 2. Setup Target Dates
        today_date = datetime.now().date()
        period_name = "Custom Range"
        filtered_rows = []
        
        match = re.search(r"(\d{2}[-/]\d{2}[-/]\d{2,4}).*to.*(\d{2}[-/]\d{2}[-/]\d{2,4})", msg)
        start_date = None
        end_date = None
        
        if match:
            def parse_user_date(d_str):
                d_str = d_str.replace("-", "/")
                if len(d_str.split("/")[-1]) == 4:
                    return datetime.strptime(d_str, "%d/%m/%Y").date()
                else:
                    return datetime.strptime(d_str, "%d/%m/%y").date()
            try:
                start_date = parse_user_date(match.group(1))
                end_date = parse_user_date(match.group(2))
                period_name = f"{match.group(1)} to {match.group(2)}"
            except:
                return "❌ Invalid date format in range."
        elif "today" in msg:
            period_name = "Today"
        elif "month" in msg:
            period_name = "This Month"
        else:
            return "❌ Invalid format. Use: sales summary today, month, or DD/MM/YY to DD/MM/YY"

        # 3. Filter Rows by Date robustly (Looking at the 'today' column)
        for row in rows:
            # Your sheet uses the header "today" for dates
            raw_date = str(row.get("today", "")).strip()
            if not raw_date: 
                continue
            
            # Parse DD-MM-YYYY format from your sheet
            try:
                # Standardize to hyphens just in case
                clean_date_str = raw_date.replace("/", "-").split()[0] 
                r_date = datetime.strptime(clean_date_str, "%d-%m-%Y").date()
            except:
                continue 
                
            # Do the matching
            if "today" in msg:
                if r_date == today_date: filtered_rows.append(row)
            elif "month" in msg:
                if r_date.month == today_date.month and r_date.year == today_date.year: filtered_rows.append(row)
            elif match:
                if start_date <= r_date <= end_date: filtered_rows.append(row)

        # 4. Tally Sales & Items (Based on 1 row per item structure)
        sales = {"Online payment": 0, "COD": 0, "Pending": 0}
        item_tally = {} 

        for row in filtered_rows:
            status = str(row.get("payment status", "")).strip().lower()
            mode = str(row.get("payment mode", "")).strip().upper()
            
            total_raw = str(row.get("total", "0"))
            total_clean = re.sub(r'[^\d.]', '', total_raw)
            total = float(total_clean) if total_clean else 0.0
            
            # Tally Revenue Types
            if status in ["success", "paid", "received"]:
                if mode in ["UPI", "NET BANKING", "NB", "ONLINE"]: 
                    sales["Online payment"] += total
                elif mode in ["COD", "CASH ON DELIVERY", "CASH"]: 
                    sales["COD"] += total
                else: 
                    sales["Online payment"] += total # Fallback successful payments
            else:
                sales["Pending"] += total

            # Tally Items (Only for successful orders)
            if status in ["success", "paid", "received"]:
                raw_name = str(row.get("item name", "")).strip()
                name_lower = raw_name.lower()
                
                qty_raw = str(row.get("qty", "0"))
                qty_clean = re.sub(r'[^\d]', '', qty_raw)
                qty = int(qty_clean) if qty_clean else 0
                
                if raw_name and qty > 0:
                    cat = item_details.get(name_lower, {}).get("category", "Other")
                    
                    if name_lower not in item_tally:
                        item_tally[name_lower] = {
                            "display_name": raw_name,
                            "category": cat,
                            "count": 0,
                            "amount": 0
                        }
                        
                    item_tally[name_lower]["count"] += qty
                    item_tally[name_lower]["amount"] += total

        # 5. Build Report
        total_sales = sales["Online payment"] + sales["COD"]
        
        report = f"📊 *Sales Summary: {period_name}*\n\n"
        report += f"Total Sales : ₹{total_sales}\n"
        report += f"Online payment : ₹{sales['Online payment']}\n"
        report += f"COD : ₹{sales['COD']}\n"
        report += f"Pending : ₹{sales['Pending']}\n\n"
        
        report += "📋 *Category wise Summary*\n"
        report += "Item Name | Total Count | Total Amount\n"
        
        # Group by Category for formatting
        categories = {}
        for data in item_tally.values():
            cat = data["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(data)
            
        for cat, items in categories.items():
            report += f"\n📁 *{cat}*\n"
            for item in sorted(items, key=lambda x: x["count"], reverse=True):
                report += f"• {item['display_name']} | {item['count']} | ₹{item['amount']}\n"

        if not item_tally:
            report += "\nNo items sold in this period."

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
Reply: `update menu` (followed by your list of items)
Or use singular commands: `add item`, `delete item`, `update price`

*3. Reports:*
`sales summary today`
`sales summary month`
`sales summary DD/MM/YYYY to DD/MM/YYYY`

ℹ️ Type *get commands* for a detailed explanation."""

    if msg == "get commands":
        return """📖 *Admin Commands Cheat Sheet*

📋 *MENU MANAGEMENT*
• *view items* : Shows the complete active menu.
• *update menu* : Start your message with this, then paste your entire menu list on the following lines to overwrite the menu. (Format: `1. Cat | Name | Price`)
• *add item | Cat | Name | Price* : Instantly adds a single new item.
• *delete item | Name* : Removes a single item.
• *update price | Name | Price* : Changes a single price.

📊 *SALES & REPORTS*
• *sales summary today* : Shows total revenue and a category-wise breakdown of items sold today.
• *sales summary month* : Tally for the entire current month.
• *sales summary DD/MM/YYYY to DD/MM/YYYY* : Generates a report for a specific date range."""

    if msg == "view items":
        from menu import format_all_items, get_menu_data
        return format_all_items(get_menu_data())

    # 2. Update Commands (Bulk & Singular)
    if msg.startswith("update menu\n") or msg.startswith("update items\n") or (msg.startswith("update menu") and "\n" in msg) or (msg.startswith("update items") and "\n" in msg):
        return handle_bulk_menu_update(user_msg)

    if msg.startswith("add item") or msg.startswith("delete item") or msg.startswith("update price"):
        return handle_menu_updates(user_msg)

    # 3. Report Commands
    if msg.startswith("sales summary"):
        return handle_sales_summary(msg)

    return None
