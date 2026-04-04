function buildCartText(cart) {
  let total = 0;

  const lines = cart.map(item => {
    const price = getPrice(item.name);
    const itemTotal = price * item.quantity;
    total += itemTotal;

    // attach price for checkout
    item.price = price;

    return `${item.name} x${item.quantity} = ₹${itemTotal}`;
  });

  return `🛒 *Your Cart:*\n\n${lines.join("\n")}\n\n*Total: ₹${total}*\n\n👉 Should I *confirm* your order?\nYou can also *add* or *remove* items.`;
}
