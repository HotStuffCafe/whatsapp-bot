const express = require("express");
const OpenAI = require("openai");

const app = express();

app.use(express.urlencoded({ extended: true }));
app.use(express.json());

const client = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

const menu = [
  "Paneer Tikka Biryani",
  "Veg Biryani",
  "Mushroom Biryani"
];

async function processAI(message) {
  const response = await client.chat.completions.create({
    model: "gpt-5.3",
    messages: [
      {
        role: "system",
        content: `You are an order assistant. Return ONLY JSON.

Menu:
${menu.join(", ")}

Example:
User: 2 paneer biryani
Output:
{"action":"add_to_cart","item":"Paneer Tikka Biryani","quantity":2}`
      },
      {
        role: "user",
        content: message
      }
    ]
  });

  return response.choices[0].message.content;
}

app.post("/webhook/whatsapp", async (req, res) => {
  const message = req.body.Body;

  let reply = "Sorry, I didn’t understand.";

  try {
    const aiResponse = await processAI(message);
    const parsed = JSON.parse(aiResponse);

    if (parsed.action === "add_to_cart") {
      reply = `Added ${parsed.quantity} x ${parsed.item} to cart 🛒`;
    }
  } catch (err) {
    console.log(err);
  }

  res.send(`
    <Response>
      <Message>${reply}</Message>
    </Response>
  `);
});

const PORT = process.env.PORT || 3000;

app.listen(PORT, () => {
  console.log("Server running 🚀");
});