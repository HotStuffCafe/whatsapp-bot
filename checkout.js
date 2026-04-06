const sessions = {};

// 🔥 Generate Order ID
function generateOrderId() {
  return "ORD" + Date.now().toString().slice(-6);
}

// 🔥 Generate UPI Payment Link
function generatePaymentLink(amount) {
  const upiId = "adi.singh@icici"; // ✅ YOUR UPI ID
  return `upi://pay?pa=${upiId}&pn=HotStuffCafe&am=${amount}&cu=INR`;
}

function handleCheckout(message, user, cart) {
  const msg = message.toLowerCase();

  if (!sessions[user]) {
    sessions[user] = { step: "idle" };
  }

  const session = sessions[user];

  // STEP 1: START CHECKOUT
  if (msg.includes("confirm") && session.step === "idle") {
    if (cart.length === 0) {
      return { reply: "Your cart is empty 🛒" };
    }

    session.step = "ask_name";

    return { reply: "🙏 Please share your *name*" };
  }

  // STEP 2: NAME
  if (session.step === "ask_name") {
    session.name = message;
    session.step = "ask_address";

    return {
      reply: `Thanks ${session.name} 😊\n\n📍 Please share your *delivery address*`,
    };
  }

  // STEP 3: ADDRESS + FINAL ORDER
  if (session.step === "ask_address") {
    session.address = message;

    let total = 0;

    const items = cart.map(item => {
      const itemTotal = item.price * item.quantity;
      total += itemTotal;
      return `${item.name} x${item.quantity}`;
    });

    const orderId = generateOrderId();
    const paymentLink = generatePaymentLink(total);

    // 🔥 ADMIN ALERT (Render Logs)
    console.log("🔥 NEW ORDER RECEIVED");
    console.log("Order ID:", orderId);
    console.log("Customer:", session.name);
    console.log("Address:", session.address);
    console.log("Items:", items);
    console.log("Total:", total);

    // RESET SESSION
    sessions[user] = { step: "idle" };

    return {
      reply: `🎉 *Order Confirmed!*\n\n🆔 Order ID: ${orderId}\n\n👤 ${session.name}\n📍 ${session.address}\n\n🛒 ${items.join("\n")}\n\n💰 Amount: ₹${total}\n\n💳 Pay here:\n${paymentLink}\n\n🚀 Once payment is done, we’ll start preparing your order!`,
      clearCart: true,
    };
  }

  return null;
}

module.exports = { handleCheckout };
