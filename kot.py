import os
import importlib.util

def get_whatsapp_sender():
    # Safely load the module where your send_whatsapp_message function lives
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

def send_kot_to_kitchen(order_id, cart, address, total, payment_mode):
    kot_numbers = get_kot_numbers()
    if not kot_numbers:
        print("⚠️ No KOT numbers found in environment variables. Skipping kitchen notification.")
        return

    # Format the items list cleanly
    items_text = ""
    for item, data in cart.items():
        qty = data.get("qty", 1)
        items_text += f"🔸 {qty} x {item}\n"

    # Build the WhatsApp KOT Message
    kot_msg = (
        f"👨‍🍳 *NEW KITCHEN ORDER* 👨‍🍳\n\n"
        f"🆔 *Order ID:* {order_id}\n"
        f"💰 *Mode:* {payment_mode}\n"
        f"💵 *Value:* ₹{total}\n\n"
        f"🧾 *Items:*\n{items_text}\n"
        f"📍 *Address:*\n{address}"
    )

    send_msg = get_whatsapp_sender()
    
    # Broadcast to all KOT numbers
    for number in kot_numbers:
        target = number if number.startswith("whatsapp:") else f"whatsapp:{number}"
        success = send_msg(target, kot_msg)
        if success:
            print(f"✅ KOT sent to {target}")
        else:
            print(f"❌ Failed to send KOT to {target}")
