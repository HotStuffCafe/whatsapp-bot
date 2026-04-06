const fs = require("fs");

const menuData = JSON.parse(fs.readFileSync("./menu.json", "utf-8"));

function normalize(text) {
  return text.toLowerCase();
}

// 🔹 simple fuzzy match (SAFE)
function findItem(text) {
  const lower = normalize(text);

  let bestMatch = null;

  for (let item of menuData) {
    const name = item.name.toLowerCase();

    if (lower.includes(name)) return item.name;

    if (lower.includes("paneer")) bestMatch = "Paneer Tikka Biryani";
    if (lower.includes("veg")) bestMatch = "Veg Biryani";
    if (lower.includes("mushroom")) bestMatch = "Mushroom Biryani";
  }

  return bestMatch;
}

// 🔹 quantity
function extractQuantity(text) {
  const match = text.match(/\d+/);
  return match ? parseInt(match[0]) : 1;
}

// 🔹 parser
function parseOrder(message) {
  try {
    const lines = message
      .toLowerCase()
      .split("\n")
      .map(l => l.trim())
      .filter(Boolean);

    let actions = [];

    lines.forEach(line => {
      const parts = line.split(/and|,/);

      parts.forEach(part => {
        const item = findItem(part);
        if (!item) return;

        const quantity = extractQuantity(part);

        if (part.includes("remove")) {
          actions.push({
            type: "remove_from_cart",
            item,
            quantity,
          });
        } else {
          actions.push({
            type: "add_to_cart",
            item,
            quantity,
          });
        }
      });
    });

    return {
      actions: actions.length > 0 ? actions : null,
      suggestions: [],
    };
  } catch (err) {
    console.log("PARSER ERROR:", err.message);
    return { actions: null, suggestions: [] };
  }
}

module.exports = { parseOrder };
