const express = require("express");
const fs = require("fs");

const cart = require("./cart");
const checkout = require("./checkout");
const orderParser = require("./orderParser");

const app = express();
app.use(express.urlencoded({ extended: true }));
app.use(express.json());

const carts = {};

const menuData = JSON.parse(fs.readFileSync("./menu.json", "utf-8"));

app.post("/webhook/whatsapp", async (req, res) => {
  const message = req.body.Body || "";
  const user = req.body.From || "unknown";

  console.log("📩 Incoming:", message);

  if (!carts[user]) carts[user] = [];

  let reply = null;

  // 🔥 1. CHECKOUT FIRST
  try {
    const checkoutResponse = checkout.handleCheckout(
      message,
      carts[user]
    );

    console.log("🧠 Checkout Response:", checkoutResponse);

    if (checkoutResponse) {
      if (checkoutResponse.clearCart) {
        carts[user] = [];
      }

      reply = checkoutResponse.reply;
    }
  } catch (err) {
    console.log("❌ Checkout error:", err.message);
  }

  // 🔥 2. PARSER
  if (!reply) {
    try {
      const parsed = orderParser.parseOrder(message);

      console.log("🧠 Parser:", parsed);

      if (parsed?.actions?.length > 0) {
        parsed.actions.forEach(a => {
          if (a.type === "add_to_cart") {
            cart.addToCart(carts[user], a.item, a.quantity);
          }

          if (a.type === "remove_from_cart") {
            carts[user] = cart.removeFromCart(
              carts[user],
              a.item,
              a.quantity
            );
          }
        });

        reply = "Cart updated ✅";
      }
    } catch (err) {
      console.log("❌ Parser error:", err.message);
    }
  }

  // 🔥 3. FALLBACK
  if (!reply) {
    reply = "⚠️ System didn’t understand. Try:\nmenu\ncart\nadd 2 paneer biryani";
  }

  console.log("📤 Reply:", reply);

  return res.send(`
    <Response>
      <Message>${reply}</Message>
    </Response>
  `);
});

const PORT = process.env.PORT || 3000;

app.listen(PORT, () => {
  console.log("Server running on port", PORT);
});
