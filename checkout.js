const fs = require("fs");

const menuData = JSON.parse(fs.readFileSync("./menu.json", "utf-8"));

function getPrice(name) {
  const item = menuData.find(i => i.name.toLowerCase() === name.toLowerCase());
  return item ? item.price : 0;
}

function generateOrderId() {
  return "ORD" + Date.now().toString().slice(-6);
}

function generatePaymentLink(amount) {
  return `upi://pay?pa=adi.singh@icici&pn=HotStuffCafe&am=${amount}&cu=INR`;
}

function handleCheckout(message, cart) {
  if (!cart._meta) {
    cart._meta = { step: "idle" };
  }

  const meta = cart._meta;
  const msg = message.toLowerCase().trim();

  console.log("📍 Step:", meta.step);

  // START
  if (msg === "confirm" && meta.step === "idle") {
    if (cart.length === 0) {
      return { reply: "Your cart is empty 🛒" };
    }

    meta.step = "name";
    return { reply: "🙏 Please share your *name*" };
  }

  // NAME
  if (meta.step === "name") {
    meta.name = message;
    meta.step = "address";

    return { reply: `Thanks ${meta.name} 😊\n📍 Share address` };
  }

  // ADDRESS
  if (meta.step === "address") {
    meta.address = message;

    let total = 0;

    const items = cart
      .filter(i => i.name)
      .map(i => {
        const price = getPrice(i.name);
        total += price * i.quantity;
        return `${i.name} x${i.quantity}`;
      });

    const orderId = generateOrderId();
    const link = generatePaymentLink(total);

    cart._meta = { step: "idle" };

    return {
      reply: `🎉 Order Confirmed!\n🆔 ${orderId}\n📍 ${meta.address}\n💰 ₹${total}\n${link}`,
      clearCart: true,
    };
  }

  // 🔥 FORCE RETURN IF IN FLOW
  if (meta.step !== "idle") {
    return { reply: "Continuing checkout..." };
  }

  return null;
}

module.exports = { handleCheckout };
