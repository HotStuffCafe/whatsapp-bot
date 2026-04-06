const express = require("express");
const fs = require("fs");
const OpenAI = require("openai");

// Modules
const cart = require("./cart");
const checkout = require("./checkout");
const orderParser = require("./orderParser");

const app = express();
app.use(express.urlencoded({ extended: true }));
app.use(express.json());

const carts = {};

// Load menu
const menuData = JSON.parse(fs.readFileSync("./menu.json", "utf-8"));
const menu = menuData.map(i => i.name);

// OpenAI
const client = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

// 🔹 AI FUNCTION (fallback only)
async function processAI(message, cartItems) {
  const cartText =
    cartItems.length > 0
      ? cartItems.map(i => `${i.name} x${i.quantity}`).join(", ")
      : "empty";

  const response = await client.chat.completions.create({
    model: "gpt-4o-mini",
    messages: [
      {
        role: "system",
        content: `Return ONLY JSON.

Menu: ${menu.join(", ")}
Cart: ${cartText}

Examples:
{"action":"view_cart"}
{
 "actions":[
  {"type":"add_to_cart","item":"Paneer Tikka Biryani","quantity":2}
 ]
}`
      },
      {
        role: "user",
        content: message,
      },
    ],
  });

  return response.choices[0].message.content.trim();
}

// 🔹 SAFE JSON
function extractJSON(text) {
  try {
    return JSON.parse(text);
  } catch {
    const match = text.match(/\{[\s\S]*\}/);
    if (match) {
      try {
        return JSON.parse(match[0]);
      } catch {}
    }
  }
  return null;
}

// 🔹 MAIN ROUTE
app.post("/webhook/whatsapp", async (req, res) => {
  const message = req.body.Body;
  const user = req.body.From;

  if (!carts[user]) carts[user] = [];

  const msg = message.toLowerCase().trim();

  // ✅ GREETING
  if (["hi", "hello", "hey", "hii"].includes(msg)) {
    const menuText = menuData
      .map((i, idx) => `${idx + 1}. ${i.name} - ₹${i.price}`)
      .join("\n");

    return res.send(`
      <Response>
        <Message>Welcome! 😊\n\nHere’s our menu 🍽️:\n\n${menuText}</Message>
      </Response>
    `);
  }

  // ✅ CHECKOUT
  const checkoutResponse = checkout.handleCheckout(
    message,
    user,
    carts[user]
  );

  if (checkoutResponse) {
    if (checkoutResponse.clearCart) carts[user] = [];

    return res.send(`
      <Response>
        <Message>${checkoutResponse.reply}</Message>
      </Response>
    `);
  }

  // ✅ RULE-BASED ORDER PARSER (PRIMARY ENGINE)
  const parsedOrder = orderParser.parseOrder(message);

  if (parsedOrder) {
    parsedOrder.forEach(a => {
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

    return res.send(`
      <Response>
        <Message>Cart updated ✅</Message>
      </Response>
    `);
  }

  let reply =
    "I didn’t understand 🤔\nTry:\n- menu\n- cart\n- add 2 paneer biryani";

  try {
    // 🔹 AI FALLBACK
    const aiResponse = await processAI(message, carts[user]);
    const parsed = extractJSON(aiResponse);

    if (parsed?.action === "view_cart") {
      reply =
        carts[user].length === 0
          ? "Your cart is empty 🛒"
          : cart.buildCartText(carts[user]);
    }

    else if (parsed?.action === "show_menu") {
      const menuText = menuData
        .map((i, idx) => `${idx + 1}. ${i.name} - ₹${i.price}`)
        .join("\n");

      reply = `Here’s our menu 🍽️:\n\n${menuText}`;
    }

  } catch (err) {
    console.log("ERROR:", err.message);
    reply = "System busy 🙏";
  }

  res.send(`
    <Response>
      <Message>${reply}</Message>
    </Response>
  `);
});

// SERVER
const PORT = process.env.PORT || 3000;

app.listen(PORT, () => {
  console.log("Server running on port", PORT);
});
