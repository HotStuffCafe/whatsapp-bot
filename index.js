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

// 🔹 Price lookup
function getPrice(itemName) {
  const item = menuData.find(
    i => i.name.toLowerCase() === itemName.toLowerCase()
  );
  return item ? item.price : 0;
}

// 🔹 Normalize
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

IMPORTANT:
- Use "actions" array for multiple operations
- Use "action" for single operations

FORMATS:

Single:
{"action":"view_cart"}

Multiple:
{
  "actions":[
    {"type":"add_to_cart","item":"Paneer Tikka Biryani","quantity":2},
    {"type":"remove_from_cart","item":"Veg Biryani","quantity":1}
  ]
}
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

// 🔹 Safe JSON parser
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
    return null;
  }
}

// 🔹 Build cart text (UX improved)
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

// 🔹 Webhook
app.post("/webhook/whatsapp", async (req, res) => {
  const message = req.body.Body;
  const user = req.body.From;

  if (!carts[user]) carts[user] = [];

  let reply = "Sorry, I didn’t understand.";

  try {
    const aiResponse = await processAI(message, carts[user]);
    console.log("AI:", aiResponse);

    const parsed = extractJSON(aiResponse);

    if (!parsed) {
      reply = "Couldn’t understand, try again 🙏";
    }

    // 🔥 MULTI ACTION
    else if (parsed.actions) {
      parsed.actions.forEach(action => {
        const item = action.item;
        const quantity = action.quantity;

        if (!item || !quantity) return;

        // ➕ ADD
        if (action.type === "add_to_cart") {
          const existing = carts[user].find(
            i => normalize(i.name) === normalize(item)
          );

          if (existing) {
            existing.quantity += quantity;
          } else {
            carts[user].push({ name: item, quantity });
          }
        }

        // ➖ REMOVE
        if (action.type === "remove_from_cart") {
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
        }
      });

      reply = "Cart updated ✅";
    }

    // 🔥 SINGLE ACTIONS
    else if (parsed.action === "view_cart") {
      if (carts[user].length === 0) {
        reply = "Your cart is empty 🛒";
      } else {
        reply = buildCartText(carts[user]);
      }
    }

    else if (parsed.action === "show_menu") {
      const menuText = menuData
        .map((i, idx) => `${idx + 1}. ${i.name} - ₹${i.price}`)
        .join("\n");

      reply = `Here’s our menu 🍽️:\n\n${menuText}`;
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
