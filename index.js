const express = require("express");
const OpenAI = require("openai");

const { addToCart, removeFromCart, buildCartText } = require("./cart");
const { handleCheckout } = require("./checkout");

const fs = require("fs");

const app = express();
app.use(express.urlencoded({ extended: true }));
app.use(express.json());

const carts = {};

const menuData = JSON.parse(fs.readFileSync("./menu.json", "utf-8"));
const menu = menuData.map(i => i.name);

const client = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

// 🔹 AI
async function processAI(message, cart) {
  const cartText =
    cart.length > 0
      ? cart.map(i => `${i.name} x${i.quantity}`).join(", ")
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
}
`
      },
      { role: "user", content: message }
    ]
  });

  return response.choices[0].message.content.trim();
}

// 🔹 JSON SAFE
function extractJSON(text) {
  try {
    return JSON.parse(text);
  } catch {
    const match = text.match(/\{[\s\S]*\}/);
    if (match) return JSON.parse(match[0]);
    return null;
  }
}

// 🔹 MAIN ROUTE
app.post("/webhook/whatsapp", async (req, res) => {
  const message = req.body.Body;
  const user = req.body.From;

  if (!carts[user]) carts[user] = [];

  // 🔥 CHECKOUT FIRST
  const checkout = handleCheckout(message, user, carts[user]);

  if (checkout) {
    if (checkout.clearCart) carts[user] = [];

    return res.send(`
      <Response>
        <Message>${checkout.reply}</Message>
      </Response>
    `);
  }

  let reply = "Try again 🙏";

  try {
    const aiResponse = await processAI(message, carts[user]);
    const parsed = extractJSON(aiResponse);

    if (!parsed) {
      reply = "Try again 🙏";
    }

    // MULTI ACTION
    else if (parsed.actions) {
      parsed.actions.forEach(a => {
        if (a.type === "add_to_cart") {
          addToCart(carts[user], a.item, a.quantity);
        }

        if (a.type === "remove_from_cart") {
          carts[user] = removeFromCart(
            carts[user],
            a.item,
            a.quantity
          );
        }
      });

      reply = "Cart updated ✅";
    }

    // SINGLE
    else if (parsed.action === "view_cart") {
      reply =
        carts[user].length === 0
          ? "Your cart is empty 🛒"
          : buildCartText(carts[user]);
    }

    else if (parsed.action === "show_menu") {
      const menuText = menuData
        .map((i, idx) => `${idx + 1}. ${i.name} - ₹${i.price}`)
        .join("\n");

      reply = `Here’s our menu 🍽️:\n\n${menuText}`;
    }

  } catch (err) {
    console.log(err);
    reply = "System busy 🙏";
  }

  res.send(`
    <Response>
      <Message>${reply}</Message>
    </Response>
  `);
});

// ✅ ONLY ONE SERVER START
const PORT = process.env.PORT || 3000;

app.listen(PORT, () => {
  console.log("Server running on port", PORT);
});
