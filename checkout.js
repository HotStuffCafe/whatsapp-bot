const fs = require("fs");

const menuData = JSON.parse(fs.readFileSync("./menu.json", "utf-8"));

// 🔹 Price lookup
function getPrice(itemName) {
  const item = menuData.find(
    i => i.name.toLowerCase() === itemName.toLowerCase()
  );
  return item ? item.price : 0;
}

// 🔹 Order ID
function generateOrderId() {
  return "ORD" + Date.now().toString().slice(-6);
}

// 🔹 Payment link
function generatePaymentLink(amount) {
  const upiId = "adi.singh@icici";
  return `upi://pay?pa=${upiId}&pn=HotStuffCafe&am=${amount}&cu=INR`;
}

function handleCheckout(message, userCart) {
  if (!message) return null;

  const msg = message.toLowerCase().trim();

  // 🔥 Attach state to cart
  if (!userCart._meta) {
    userCart._meta = { step: "idle" };
  }

  const meta = userCart._meta;

  // ✅ START
  if (msg === "confirm" && meta.step === "idle") {
    if (userCart.length === 0) {
      return { reply: "Your cart is empty 🛒" };
    }

    meta.step = "ask_name";
    return { reply: "🙏 Please share your *name*" };
  }

  // ✅ NAME
  if (meta.step === "ask_name") {
    meta.name = message;
    meta.step = "ask_address";

    return {
      reply: `Thanks ${meta.name} 😊\n\n📍 Please share your *delivery address*`,
    };
  }

  // ✅ ADDRESS (THIS IS NOW BULLETPROOF)
  if (meta.step === "ask_address") {
    meta.address = message;

    let total = 0;

    const items = userCart
      .filter(item => item.name) // ignore _meta
      .map(item => {
        const price = getPrice(item.name);
        const itemTotal = price * item.quantity;
        total += itemTotal;

        return `${item.name} x${item.quantity}`;
      });

    const orderId = generateOrderId();
    const paymentLink = generatePaymentLink(total);

    console.log("🔥 ORDER:", {
      orderId,
      name: meta.name,
      address: meta.address,
      items,
      total,
    });

    // 🔥 RESET STATE
    userCart._meta = { step: "idle" };

    return {
      reply: `🎉 *Order Confirmed!*\n\n🆔 ${orderId}\n\n👤 ${meta.name}\n📍 ${meta.address}\n\n🛒 ${items.join("\n")}\n\n💰 Total: ₹${total}\n\n💳 Pay here:\n${paymentLink}`,
      clearCart: true,
    };
  }

  // 🔒 LOCK FLOW
  if (meta.step !== "idle") {
    return {
      reply: "Please complete checkout 🙏",
    };
  }

  return null;
}

module.exports = { handleCheckout };
