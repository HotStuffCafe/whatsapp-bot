const express = require("express");
const OpenAI = require("openai");
const fs = require("fs");

const app = express();

app.use(express.urlencoded({ extended: true }));
app.use(express.json());

// 🔹 In-memory cart (per user)
const carts = {};

// 🔹 Load menu
const menuData = JSON.parse(
  fs.readFileSync("./menu.json", "utf-8")
);

const menu = menuData.map(item => item.name);

const menuText = menuData
  .map((item, i) => `${i + 1}. ${item.name} - ₹${item.price}`)
  .join("\n");

// 🔹 OpenAI
const client = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

// 🔹 AI function
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

AVAILABLE ACTIONS:
- add_to_cart
- show_menu
- view_cart
- clarify

RULES:
- hi/hello → show_menu
- "menu" → show_menu
- "cart" → view_cart
- "add more" → add_to_cart (use last item from cart)
- If unclear → clarify

FORMAT:
{
  "action": "",
  "item": "",
  "quantity": 1
}

EXAMPLES:

User: hi
Output:
{"action":"show_menu","item":"","quantity":0}

User: show cart
Output:
{"action":"view_cart","item":"","quantity":0}

User: 2 paneer biryani
Output:
{"action":"add_to_cart","item":"Paneer Tikka Biryani","quantity":2}

User: add 1 more
Output:
{"action":"add_to_cart","item":"Paneer Tikka Biryani","quantity":1}
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

// 🔹 Webhook
app.post("/webhook/whatsapp", async (req, res) => {
  const message = req.body.Body;
  const user = req.body.From;

  console.log("USER:", user);
  console.log("MESSAGE:", message);

  if (!carts[user]) {
    carts[user] = [];
  }

  let reply = "Sorry, I didn’t understand.";

  try {
    const aiResponse = await processAI(message, carts[user]);

    console.log("AI RAW:", aiResponse);

    let parsed;

    try {
      parsed = JSON.parse(aiResponse);
    } catch (e) {
      const match = aiResponse.match(/\{.*\}/s);
      if (match) parsed = JSON.parse(match[0]);
    }

    // 🛒 ADD TO CART
    if (parsed?.action === "add_to_cart") {
      const existing = carts[user].find(
        i => i.name === parsed.item
      );

      if (existing) {
        existing.quantity += parsed.quantity;
      } else {
        carts[user].push({
          name: parsed.item,
          quantity: parsed.quantity
        });
      }

      reply = `Added ${parsed.quantity} x ${parsed.item} 🛒`;
    }

    // 📋 SHOW MENU
    else if (parsed?.action === "show_menu") {
      reply = `Here’s our menu 🍽️:\n\n${menuText}`;
    }

    // 🧺 VIEW CART
    else if (parsed?.action === "view_cart") {
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
    reply = "System busy, please try again 🙏";
  }

  res.send(`
    <Response>
      <Message>${reply}</Message>
    </Response>
  `);
});

// 🔹 Health check
app.get("/", (req, res) => {
  res.send("Server is running ✅");
});

// 🔹 Start server
const PORT = process.env.PORT || 3000;

app.listen(PORT, () => {
  console.log("Server running 🚀");
});
