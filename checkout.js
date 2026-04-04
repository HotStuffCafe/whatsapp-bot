function handleCheckout(message, cart) {
  const msg = message.toLowerCase();

  if (msg.includes("confirm")) {
    return {
      reply: "🎉 Order confirmed!\n\nWe are preparing your food 🍽️",
      clearCart: true
    };
  }

  return null;
}

module.exports = { handleCheckout };
