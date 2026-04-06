const fs = require("fs");

const menuData = JSON.parse(fs.readFileSync("./menu.json", "utf-8"));

// 🔹 Normalize
function normalize(text) {
  return text.toLowerCase();
}

// 🔹 Levenshtein Distance (typo matching)
function levenshtein(a, b) {
  const matrix = [];

  for (let i = 0; i <= b.length; i++) {
    matrix[i] = [i];
  }

  for (let j = 0; j <= a.length; j++) {
    matrix[0][j] = j;
  }

  for (let i = 1; i <= b.length; i++) {
    for (let j = 1; j <= a.length; j++) {
      if (b.charAt(i - 1) === a.charAt(j - 1)) {
        matrix[i][j] = matrix[i - 1][j - 1];
      } else {
        matrix[i][j] = Math.min(
          matrix[i - 1][j - 1] + 1,
          matrix[i][j - 1] + 1,
          matrix[i - 1][j] + 1
        );
      }
    }
  }

  return matrix[b.length][a.length];
}

// 🔹 Find best match
function findBestMatch(text) {
  const lower = normalize(text);

  let bestMatch = null;
  let bestScore = Infinity;

  for (let item of menuData) {
    const name = item.name.toLowerCase();

    const distance = levenshtein(lower, name);

    if (distance < bestScore) {
      bestScore = distance;
      bestMatch = item.name;
    }

    // partial match boost
    if (lower.includes(name)) {
      return { item: item.name, confident: true };
    }
  }

  // threshold (tuneable)
  if (bestScore <= 5) {
    return { item: bestMatch, confident: true };
  }

  if (bestScore <= 8) {
    return { item: bestMatch, confident: false };
  }

  return null;
}

// 🔹 Quantity
function extractQuantity(text) {
  const match = text.match(/\d+/);
  return match ? parseInt(match[0]) : 1;
}

// 🔹 Parse one line
function parseLine(line) {
  const parts = line.split(/and|,/);

  const actions = [];
  const suggestions = [];

  parts.forEach(part => {
    const match = findBestMatch(part);

    if (!match) return;

    const quantity = extractQuantity(part);

    if (!match.confident) {
      suggestions.push(match.item);
    }

    if (part.includes("remove")) {
      actions.push({
        type: "remove_from_cart",
        item: match.item,
        quantity,
      });
    } else {
      actions.push({
        type: "add_to_cart",
        item: match.item,
        quantity,
      });
    }
  });

  return { actions, suggestions };
}

// 🔹 MAIN PARSER
function parseOrder(message) {
  const lines = message
    .toLowerCase()
    .split("\n")
    .map(l => l.trim())
    .filter(Boolean);

  let allActions = [];
  let allSuggestions = [];

  lines.forEach(line => {
    const result = parseLine(line);
    allActions = allActions.concat(result.actions);
    allSuggestions = allSuggestions.concat(result.suggestions);
  });

  return {
    actions: allActions.length > 0 ? allActions : null,
    suggestions: allSuggestions,
  };
}

module.exports = { parseOrder };
