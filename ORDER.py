 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a/ORDER.py b/ORDER.py
index e4694cbbb5f8df9a072fd1e5c90267383c534d7b..3573df88bbf374fdbf7a5b43043f87d29de43651 100644
--- a/ORDER.py
+++ b/ORDER.py
@@ -1,46 +1,50 @@
 import re
+import os
 from datetime import datetime
 from sheet_update import update_google_sheet
 
 
 # =========================
 # 🆔 ORDER ID GENERATOR
 # =========================
 def generate_order_id():
     now = datetime.now()
     return now.strftime("ORD%d%m%y%H%M%S")
 
 
 # =========================
 # 🧠 FIND EXACT ITEM
 # =========================
 def find_item(menu, item_name):
     item_name = item_name.lower().strip()
 
     for category in menu:
-        for item, price in menu[category].items():
+        for row in menu[category]:
+            item = row.get("item", "").strip()
+            price = row.get("price", 0)
+
             if item.lower() == item_name:
                 return item, price
 
     return None, None
 
 
 # =========================
 # 🧠 PARSE ORDER TEXT
 # =========================
 def parse_order(text, menu):
     text = text.lower()
 
     # normalize
     text = text.replace("\n", ",")
     text = text.replace(" and ", ",")
     text = text.replace("add", "")
     text = text.replace("remove", "")
 
     parts = text.split(",")
 
     items = []
 
     for part in parts:
         part = part.strip()
         if not part:
@@ -134,47 +138,72 @@ def handle_order(user_msg, session, menu):
         items = parse_order(msg, menu)
 
         cart = session.get("cart", {})
 
         for item, qty, _ in items:
             if item in cart:
                 cart[item]["qty"] -= qty
 
                 if cart[item]["qty"] <= 0:
                     del cart[item]
 
         return build_cart(session)
 
     # =========================
     # 📍 ADDRESS DETECTION
     # =========================
     if any(word in msg for word in ["shop", "road", "street", "sector"]):
         session["address"] = user_msg
         return build_cart(session)
 
     # =========================
     # ✅ CONFIRM ORDER
     # =========================
     if msg in ["yes", "y"]:
 
-        if not session.get("cart") or not session.get("address"):
-            return "⚠️ Please complete your order (items + address)"
+        if not session.get("cart"):
+            return "⚠️ Please add items before confirming your order."
+
+        if not session.get("address"):
+            return "Hey unable to confirm your order, please share *address* before confirming the order."
+
+        payment_mode = os.getenv("ENABLE_PAYMENT", "false").lower()
+
+        if payment_mode in ["payonly", "paycod"]:
+            order_id = session.get("order_id") or generate_order_id()
+            session["order_id"] = order_id
+            session["awaiting_payment"] = True
+
+            if payment_mode == "paycod":
+                return f"""🧾 Order almost done!
+
+🆔 Order ID: {order_id}
+💰 Total: ₹{session.get("total", 0)}
+
+Reply *PAY* for online payment or *COD* for cash on delivery."""
+
+            return f"""🧾 Order almost done!
+
+🆔 Order ID: {order_id}
+💰 Total: ₹{session.get("total", 0)}
+
+Reply *PAY* to complete payment and confirm your order."""
 
         order_id = generate_order_id()
 
         # SAVE TO SHEET
         update_google_sheet(session, order_id, "COD", "Success")
 
         session.clear()
 
         return f"""✅ Order Confirmed!
 
 🆔 Order ID: {order_id}"""
 
     # =========================
     # ❌ CANCEL
     # =========================
     if msg in ["no", "cancel"]:
         session.clear()
         return "❌ Order cancelled."
 
-    return None
\ No newline at end of file
+    return None
 
EOF
)
