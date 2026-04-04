const express = require("express");
const OpenAI = require("openai");
const fs = require("fs");

const app = express();

app.use(express.urlencoded({ extended: true }));
app.use(express.json());

// 🔹 Load menu from JSON file
const menuData = JSON.parse(
  fs.readFileSync("./menu.json", "utf-8")
);

// Extract only item names for AI
const menu = menuData.map(item => item.name);

// Create menu display text
const menuText = menuData
  .map((item, i) => `${i + 1}. ${item.name} - ₹${item.price}`)
  .join("\n");

// 🔹 OpenAI client
const client = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

// 🔹 AI Processing Function
async function processAI(message) {
  const response = await client.chat.completions.create({
    model: "gpt-4o-mini",
    messages: [
      {
        role: "system",
        content: `You are an order assistant.

Return ONLY valid JSON. No text.

Menu:
${menu.join(", ")}

AVAILABLE ACTIONS:
- add_to_cart
- show_menu
- clarify

RULES:
- If user says hi/hello → show_menu
- If user asks for menu → show_menu
- If user orders → add_to_cart
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

User: menu
Output:
{"action":"show_menu","item":"","quantity":0}

User: 2 paneer biryani
Output:
{"action":"add_to_cart","item":"Paneer Tikka Biryani","quantity":2}
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

// 🔹 WhatsApp Webhook
app.post("/webhook/whatsapp", async (req, res) => {
  const message = req.body.Body;

  console.log("USER MESSAGE:", message);

  let reply = "Sorry, I didn’t understand.";

  try {
    const aiResponse = await processAI(message);

    console.log("AI RAW RESPONSE:", aiResponse);

    let parsed;

    try {
      parsed = JSON.parse(aiResponse);
    } catch (e) {
      // Try extracting JSON if extra text present
      const match = aiResponse.match(/\{.*\}/s);
      if (match) {
        parsed = JSON.parse(match[0]);
      }
    }

    if (parsed?.action === "add_to_cart") {
      reply = `Added ${parsed.quantity} x ${parsed.item} to cart 🛒`;

    } else if (parsed?.action === "show_menu") {
      reply = `Here’s our menu 🍽️:\n\n${menuText}`;

    } else {
      reply = "Please choose from menu 🙌";
    }

  } catch (err) {
    console.log("ERROR:", err.message);
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
