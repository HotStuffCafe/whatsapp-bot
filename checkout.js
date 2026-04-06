const fs = require("fs");

const menuData = JSON.parse(fs.readFileSync("./menu.json", "utf-8"));

const sessions = {};

// Price lookup
function getPrice(itemName) {
  const item = menuData.find(
    i => i.name.toLowerCase() === itemName.toLowerCase()
  );
  return item ? item.price : 0;
}

// Order ID
function generateOrderId() {
  return "ORD" + Date.now().toString().slice(-6);
}

// Payment link
function generatePaymentLink(amount) {
  const upiId = "adi.singh@icici";
  return `upi://pay?pa=${upiId}&pn=HotStuffCafe&am=${amount}&cu=INR`;
}

function handleCheckout(message, user, cart) {
  if (!message) return null;

  const msg = message.toLowerCase().trim();

  if (!sessions[user]) {
    sessions[user] = { step: "idle" };
  }

  const session = sessions[user];

  // START
  if (msg === "confirm" && session.step === "idle") {
    if (cart.length === 0) {
      return { reply: "Your cart is empty 🛒" };
    }

    session.step = "ask_name";
    return { reply: "🙏 Please share your *name*" };
  }

  // NAME
  if (session.step === "ask_name") {
    session.name = message;
    session.step = "ask_address";

    return {
      reply: `Thanks ${session.name} 😊\n\n📍 Please share your *delivery address*`,
    };
  }

  // ADDRESS (FINAL STEP)
  if (session.step === "ask_address") {
    session.address = message;

    let total = 0;

    const items = cart.map(item => {
      const price = getPrice(item.name);
      const itemTotal = price * item.quantity;
      total += itemTotal;

      return `${item.name} x${item.quantity}`;
    });

    const orderId = generateOrderId();
    const paymentLink = generatePaymentLink(total);

    console.log("🔥 ORDER:", {
      orderId,
      name: session.name,
      address: session.address,
      items,
      total,
    });

    sessions[user] = { step: "idle" };

    return {
      reply: `🎉 *Order Confirmed!*\n\n🆔 ${orderId}\n\n👤 ${session.name}\n📍 ${session.address}\n\n🛒 ${items.join("\n")}\n\n💰 Total: ₹${total}\n\n💳 Pay here:\n${paymentLink}`,
      clearCart: true,
    };
  }

  // LOCK USER IN CHECKOUT
  if (session.step !== "idle") {
    return {
      reply: "Please complete checkout 🙏",
    };
  }

  return null;
}

module.exports = { handleCheckout };
