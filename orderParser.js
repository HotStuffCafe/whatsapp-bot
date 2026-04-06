const fs = require("fs");

const menuData = JSON.parse(fs.readFileSync("./menu.json", "utf-8"));

function normalize(text) {
  return text.toLowerCase();
}

// 🔥 Match item from menu
function findItem(text) {
  const lower = normalize(text);

  for (let item of menuData) {
    if (lower.includes(item.name.toLowerCase())) {
      return item.name;
    }
  }

  return null;
}

// 🔥 Extract quantity
function extractQuantity(text) {
  const match = text.match(/\d+/);
  return match ? parseInt(match[0]) : 1;
}

// 🔥 MAIN PARSER
function parseOrder(message) {
  const msg = normalize(message);

  const parts = msg.split(/and|,/);

  const actions = [];

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

  return actions.length > 0 ? actions : null;
}

module.exports = { parseOrder };
