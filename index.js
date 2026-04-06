const express = require("express");
const fs = require("fs");
const OpenAI = require("openai");

// Modules
const cart = require("./cart");
const checkout = require("./checkout");

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

// 🔹 AI FUNCTION
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

Actions:
- add_to_cart
- remove_from_cart
- view_cart
- show_menu

Examples:
{"action":"show_menu"}
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

// 🔹 SAFE JSON PARSER
function extractJSON(text) {
  try {
    return JSON.parse(text);
  } catch {
    try {
      const cleaned = text
        .replace(/```json/g, "")
        .replace(/```/g, "")
        .trim();
      return JSON.parse(cleaned);
    } catch {
      const match = text.match(/\{[\s\S]*\}/);
      if (match) {
        try {
          return JSON.parse(match[0]);
        } catch {}
      }
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

  // ✅ GREETING HANDLER (NO AI)
  if (
    msg === "hi" ||
    msg === "hello" ||
    msg === "hey" ||
    msg === "hii"
  ) {
    const menuText = menuData
      .map((i, idx) => `${idx + 1}. ${i.name} - ₹${i.price}`)
      .join("\n");

    return res.send(`
      <Response>
        <Message>Welcome! 😊\n\nHere’s our menu 🍽️:\n\n${menuText}</Message>
      </Response>
    `);
  }

  // ✅ CHECKOUT FLOW
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

  let reply =
    "I didn’t understand that 🤔\nTry:\n- menu\n- cart\n- add 2 paneer biryani";

  try {
    const aiResponse = await processAI(message, carts[user]);
    console.log("AI:", aiResponse);

    const parsed = extractJSON(aiResponse);

    if (!parsed) {
      reply = "Try again 🙏";
    }

    // 🔥 MULTI ACTION
    else if (parsed.actions) {
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

    // 🔥 VIEW CART
    else if (parsed.action === "view_cart") {
      reply =
        carts[user].length === 0
          ? "Your cart is empty 🛒"
          : cart.buildCartText(carts[user]);
    }

    // 🔥 SHOW MENU
    else if (parsed.action === "show_menu") {
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

// ✅ SINGLE SERVER START
const PORT = process.env.PORT || 3000;

app.listen(PORT, () => {
  console.log("Server running on port", PORT);
});
