const sessions = {};

// 🔥 Order ID
function generateOrderId() {
  return "ORD" + Date.now().toString().slice(-6);
}

// 🔥 Payment Link
function generatePaymentLink(amount) {
  const upiId = "adi.singh@icici";
  return `upi://pay?pa=${upiId}&pn=HotStuffCafe&am=${amount}&cu=INR`;
}

function handleCheckout(message, user, cart) {
  const msg = message.toLowerCase();

  if (!sessions[user]) {
    sessions[user] = { step: "idle" };
  }

  const session = sessions[user];

  // ✅ STEP 1: START CHECKOUT
  if (msg === "confirm" && session.step === "idle") {
    if (cart.length === 0) {
      return { reply: "Your cart is empty 🛒" };
    }

    session.step = "ask_name";

    return { reply: "🙏 Please share your *name*" };
  }

  // ✅ STEP 2: NAME
  if (session.step === "ask_name") {
    session.name = message;
    session.step = "ask_address";

    return {
      reply: `Thanks ${session.name} 😊\n\n📍 Please share your *delivery address*`,
    };
  }

  // ✅ STEP 3: ADDRESS → FINAL ORDER
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

    console.log("🔥 NEW ORDER");
    console.log(orderId, session.name, session.address, items, total);

    // RESET SESSION
    sessions[user] = { step: "idle" };

    return {
      reply: `🎉 *Order Confirmed!*\n\n🆔 Order ID: ${orderId}\n\n👤 ${session.name}\n📍 ${session.address}\n\n🛒 ${items.join("\n")}\n\n💰 Amount: ₹${total}\n\n💳 Pay here:\n${paymentLink}`,
      clearCart: true,
    };
  }

  return null;
}

module.exports = { handleCheckout };
