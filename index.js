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

// OpenAI (fallback only)
const client = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

// 🔹 AI FUNCTION (SAFE FALLBACK)
async function processAI(message, cartItems) {
  try {
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
{"action":"show_menu"}
`,
        },
        {
          role: "user",
          content: message,
        },
      ],
    });

    return response.choices[0].message.content.trim();
  } catch (err) {
    console.log("AI ERROR:", err.message);
    return null;
  }
}

// 🔹 SAFE JSON PARSER
function extractJSON(text) {
  if (!text) return null;

  try {
    return JSON.parse(text);
  } catch {
    try {
      const match = text.match(/\{[\s\S]*\}/);
      if (match) return JSON.parse(match[0]);
    } catch {}
  }

  return null;
}

// 🔹 MAIN ROUTE
app.post("/webhook/whatsapp", async (req, res) => {
  const message = req.body.Body || "";
  const user = req.body.From || "unknown";

  if (!carts[user]) carts[user] = [];

  const msg = message.toLowerCase().trim();

  // ✅ GREETING HANDLER
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

  // ✅ CHECKOUT FLOW
  const checkoutResponse = checkout.handleCheckout(
    message,
    user,
    carts[user]
  );

  if (checkoutResponse) {
    if (checkoutResponse.clearCart) {
      carts[user] = [];
    }

    return res.send(`
      <Response>
        <Message>${checkoutResponse.reply}</Message>
      </Response>
    `);
  }

  // ✅ ORDER PARSER (PRIMARY ENGINE)
  try {
    const parsed = orderParser.parseOrder(message);

    if (parsed && parsed.actions && parsed.actions.length > 0) {
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

      return res.send(`
        <Response>
          <Message>Cart updated ✅</Message>
        </Response>
      `);
    }
  } catch (err) {
    console.log("PARSER ERROR:", err.message);
  }

  // 🔹 DEFAULT RESPONSE
  let reply =
    "I didn’t understand 🤔\nTry:\n- menu\n- cart\n- add 2 paneer biryani";

  // 🔹 AI FALLBACK (SAFE)
  try {
    const aiResponse = await processAI(message, carts[user]);
    const parsedAI = extractJSON(aiResponse);

    if (parsedAI?.action === "view_cart") {
      reply =
        carts[user].length === 0
          ? "Your cart is empty 🛒"
          : cart.buildCartText(carts[user]);
    }

    else if (parsedAI?.action === "show_menu") {
      const menuText = menuData
        .map((i, idx) => `${idx + 1}. ${i.name} - ₹${i.price}`)
        .join("\n");

      reply = `Here’s our menu 🍽️:\n\n${menuText}`;
    }
  } catch (err) {
    console.log("AI FALLBACK ERROR:", err.message);
  }

  res.send(`
    <Response>
      <Message>${reply}</Message>
    </Response>
  `);
});

// ✅ SINGLE SERVER START (IMPORTANT)
const PORT = process.env.PORT || 3000;

app.listen(PORT, () => {
  console.log("Server running on port", PORT);
});
