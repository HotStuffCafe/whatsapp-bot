const express = require("express");
const OpenAI = require("openai");
const fs = require("fs");

const app = express();
app.use(express.urlencoded({ extended: true }));
app.use(express.json());

const carts = {};

// 🔹 Load menu
const menuData = JSON.parse(fs.readFileSync("./menu.json", "utf-8"));
const menu = menuData.map(item => item.name);

const menuText = menuData
  .map((item, i) => `${i + 1}. ${item.name} - ₹${item.price}`)
  .join("\n");

// 🔹 Safe normalize
function normalize(text) {
  if (!text) return "";
  return text.toLowerCase().trim();
}

// 🔹 OpenAI
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
        content: `You are an order assistant.

Return ONLY JSON.

Menu:
${menu.join(", ")}

Cart:
${cartText}

RULES:
- Always return ONE JSON object
- Use "items" array for multiple items

FORMAT:
{
  "action": "",
  "items": [
    {"item": "", "quantity": 1}
  ]
}

Actions:
- add_to_cart
- remove_from_cart
- show_menu
- view_cart
`
      },
      {
        role: "user",
        content: message
      }
    ]
  });

  return response.choices[0].message.content.trim();
}

// 🔹 SAFE JSON PARSER (CRITICAL FIX)
function extractJSON(text) {
  try {
    return JSON.parse(text);
  } catch {
    const matches = text.match(/\{[\s\S]*?\}/g);
    if (!matches) return null;

    try {
      return JSON.parse(matches[0]);
    } catch {
      return null;
    }
  }
}

// 🔹 Webhook
app.post("/webhook/whatsapp", async (req, res) => {
  const message = req.body.Body;
  const user = req.body.From;

  if (!carts[user]) carts[user] = [];

  let reply = "Sorry, I didn’t understand.";

  try {
    const aiResponse = await processAI(message, carts[user]);
    console.log("AI RAW:", aiResponse);

    const parsed = extractJSON(aiResponse);

    if (!parsed) {
      reply = "Couldn’t understand properly, try again 🙏";
    }

    // ➕ ADD
    else if (parsed.action === "add_to_cart") {
      const items = parsed.items || [];

      items.forEach(({ item, quantity }) => {
        if (!item || !quantity) return;

        const existing = carts[user].find(
          i => normalize(i.name) === normalize(item)
        );

        if (existing) {
          existing.quantity += quantity;
        } else {
          carts[user].push({
            name: item,
            quantity: quantity
          });
        }
      });

      reply = "Items added to cart 🛒";
    }

    // ➖ REMOVE
    else if (parsed.action === "remove_from_cart") {
      const items = parsed.items || [];

      items.forEach(({ item, quantity }) => {
        if (!item || !quantity) return;

        const existing = carts[user].find(
          i => normalize(i.name) === normalize(item)
        );

        if (!existing) return;

        existing.quantity -= quantity;

        if (existing.quantity <= 0) {
          carts[user] = carts[user].filter(
            i => normalize(i.name) !== normalize(item)
          );
        }
      });

      reply = "Cart updated ❌";
    }

    // 📋 MENU
    else if (parsed.action === "show_menu") {
      reply = `Here’s our menu 🍽️:\n\n${menuText}`;
    }

    // 🧺 CART
    else if (parsed.action === "view_cart") {
      if (carts[user].length === 0) {
        reply = "Your cart is empty 🛒";
      } else {
        const cartText = carts[user]
          .map(i => `${i.name} x${i.quantity}`)
          .join("\n");

        reply = `🛒 Your Cart:\n\n${cartText}`;
      }
    }

    else {
      reply = "Please choose from menu 🙌";
    }

  } catch (err) {
    console.log("ERROR:", err.message);
    reply = "System busy, try again 🙏";
  }

  res.send(`
    <Response>
      <Message>${reply}</Message>
    </Response>
  `);
});

// 🔹 Health
app.get("/", (req, res) => {
  res.send("Server is running ✅");
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log("Server running 🚀");
});
