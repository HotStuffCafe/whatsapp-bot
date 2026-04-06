const express = require("express");
const fs = require("fs");
const OpenAI = require("openai");

const cart = require("./cart");
const checkout = require("./checkout");
const orderParser = require("./orderParser");

const app = express();
app.use(express.urlencoded({ extended: true }));
app.use(express.json());

const carts = {};

// Load menu
const menuData = JSON.parse(fs.readFileSync("./menu.json", "utf-8"));

// OpenAI fallback
const client = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

// AI fallback
async function processAI(message) {
  try {
    const response = await client.chat.completions.create({
      model: "gpt-4o-mini",
      messages: [
        {
          role: "system",
          content: `Return ONLY JSON.
Examples:
{"action":"view_cart"}
{"action":"show_menu"}`,
        },
        { role: "user", content: message },
      ],
    });

    return response.choices[0].message.content.trim();
  } catch (err) {
    console.log("AI ERROR:", err.message);
    return null;
  }
}

// Safe JSON parse
function extractJSON(text) {
  try {
    return JSON.parse(text);
  } catch {
    const match = text?.match(/\{[\s\S]*\}/);
    if (match) {
      try {
        return JSON.parse(match[0]);
      } catch {}
    }
  }
  return null;
}

// MAIN ROUTE
app.post("/webhook/whatsapp", async (req, res) => {
  const message = req.body.Body || "";
  const user = req.body.From || "unknown";

  if (!carts[user]) carts[user] = [];

  const msg = message.toLowerCase().trim();

  // ✅ GREETING
  if (["hi", "hello", "hey"].includes(msg)) {
    const menuText = menuData
      .map((i, idx) => `${idx + 1}. ${i.name} - ₹${i.price}`)
      .join("\n");

    return res.send(`
      <Response>
        <Message>Welcome! 😊\n\nHere’s our menu 🍽️:\n\n${menuText}</Message>
      </Response>
    `);
  }

  // 🔥 CHECKOUT FIRST (LOCKED FLOW)
  try {
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
  } catch (err) {
    console.log("CHECKOUT ERROR:", err.message);
  }

  // ✅ ORDER PARSER
  try {
    const parsed = orderParser.parseOrder(message);

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

      return res.send(`
        <Response>
          <Message>Cart updated ✅</Message>
        </Response>
      `);
    }
  } catch (err) {
    console.log("PARSER ERROR:", err.message);
  }

  // DEFAULT RESPONSE
  let reply =
    "I didn’t understand 🤔\nTry:\n- menu\n- cart\n- add 2 paneer biryani";

  // AI fallback
  try {
    const aiResponse = await processAI(message);
    const parsedAI = extractJSON(aiResponse);

    if (parsedAI?.action === "view_cart") {
      reply =
        carts[user].length === 0
          ? "Your cart is empty 🛒"
          : cart.buildCartText(carts[user]);
    }

    if (parsedAI?.action === "show_menu") {
      const menuText = menuData
        .map((i, idx) => `${idx + 1}. ${i.name} - ₹${i.price}`)
        .join("\n");

      reply = `Here’s our menu 🍽️:\n\n${menuText}`;
    }
  } catch (err) {
    console.log("AI ERROR:", err.message);
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
