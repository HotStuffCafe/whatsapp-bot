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
        content: `You are an order assistant.

Return ONLY JSON.

Menu:
${menu.join(", ")}

Cart:
${cartText}

ACTIONS:
- add_to_cart
- remove_from_cart
- view_cart
- show_menu

RULES:
- hi → show_menu
- menu → show_menu
- cart → view_cart

FORMATS:

{"action":"view_cart"}

OR

{
  "actions":[
    {"type":"add_to_cart","item":"","quantity":1}
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

// 🔹 Safe JSON
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

  // 🔥 CHECKOUT FLOW
  const checkout = handleCheckout(message, user, carts[user]);

  if (checkout) {
    if (checkout.clearCart) carts[user] = [];
    if (checkout.resetSession) console.log("Session reset");

    return res.send(`
      <Response>
        <Message>${checkout.reply}</Message>
      </Response>
    `);
  }

  let reply = "Sorry, I didn’t understand.";

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

    // SINGLE ACTIONS
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
    console.log(err);
    reply = "System busy 🙏";
  }

  res.send(`
    <Response>
      <Message>${reply}</Message>
    </Response>
  `);
});

app.listen(process.env.PORT || 3000);
