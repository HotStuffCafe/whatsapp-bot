const sessions = {};

function handleCheckout(message, user, cart) {
  const msg = message.toLowerCase();

  if (!sessions[user]) {
    sessions[user] = { step: "idle" };
  }

  const session = sessions[user];

  // START CHECKOUT
  if (msg.includes("confirm") && session.step === "idle") {
    if (cart.length === 0) {
      return {
        reply: "Your cart is empty 🛒"
      };
    }

    session.step = "ask_name";

    return {
      reply: "🙏 Please share your *name*"
    };
  }

  // NAME
  if (session.step === "ask_name") {
    session.name = message;
    session.step = "ask_address";

    return {
      reply: `Thanks ${session.name} 😊\n\n📍 Please share your *delivery address*`
    };
  }

  // ADDRESS
  if (session.step === "ask_address") {
    session.address = message;
    session.step = "done";

    let total = 0;

    const items = cart.map(item => {
      const itemTotal = item.price * item.quantity;
      total += itemTotal;
      return `${item.name} x${item.quantity}`;
    });

    // RESET SESSION
    sessions[user] = { step: "idle" };

    return {
      reply: `🎉 *Order Confirmed!*\n\n👤 ${session.name}\n📍 ${session.address}\n\n🛒 ${items.join("\n")}\n\n💰 ₹${total}\n\n🚀 Preparing your food!`,
      clearCart: true
    };
  }

  return null;
}

module.exports = { handleCheckout };
