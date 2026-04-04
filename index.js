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

FORMAT:
{
  "actions":[
    {"type":"add_to_cart","item":"","quantity":1}
  ]
}

OR

{"action":"view_cart"}
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

  // 🔥 CHECKOUT MODULE FIRST
  const checkoutResponse = handleCheckout(message, carts[user]);

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
          ) || carts[user];
        }
      });

      reply = "Cart updated ✅";
    }

    // VIEW CART
    else if (parsed.action === "view_cart") {
      if (carts[user].length === 0) {
        reply = "Your cart is empty 🛒";
      } else {
        const cart = buildCartText(carts[user]);

        reply =
          cart.text +
          "\n\n👉 Should I *confirm* your order?\nYou can also *add* or *remove* items.";
      }
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
