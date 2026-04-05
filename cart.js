const fs = require("fs");

const menuData = JSON.parse(fs.readFileSync("./menu.json", "utf-8"));

function normalize(text) {
  return text?.toLowerCase().trim();
}

function getPrice(name) {
  const item = menuData.find(
    i => normalize(i.name) === normalize(name)
  );
  return item ? item.price : 0;
}

// ✅ ADD
function addToCart(cart, item, quantity) {
  if (!item || !quantity) return;

  const existing = cart.find(
    i => normalize(i.name) === normalize(item)
  );

  if (existing) {
    existing.quantity += quantity;
  } else {
    cart.push({ name: item, quantity });
  }
}

// ✅ REMOVE
function removeFromCart(cart, item, quantity) {
  const existing = cart.find(
    i => normalize(i.name) === normalize(item)
  );

  if (!existing) return cart;

  existing.quantity -= quantity;

  if (existing.quantity <= 0) {
    return cart.filter(i => normalize(i.name) !== normalize(item));
  }

  return cart;
}

// ✅ BUILD CART TEXT
function buildCartText(cart) {
  let total = 0;

  const lines = cart.map(item => {
    const price = getPrice(item.name);
    const itemTotal = price * item.quantity;
    total += itemTotal;

    return `${item.name} x${item.quantity} = ₹${itemTotal}`;
  });

  return `🛒 *Your Cart:*\n\n${lines.join("\n")}\n\n*Total: ₹${total}*\n\n👉 Should I *confirm* your order?\nYou can also *add* or *remove* items.`;
}

// 🔥 EXPORT PROPERLY
module.exports = {
  addToCart,
  removeFromCart,
  buildCartText
};
