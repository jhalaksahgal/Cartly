/**
 * Display formatting shared by the list rendering and the spoken-feedback
 * messages, so "2 bottles of water" reads the same everywhere.
 *
 * The parser canonicalises units to a singular form ("bottles" -> "bottle")
 * because that is the right shape for matching and storage. Pluralising is a
 * presentation concern, so it lives here rather than in the parser.
 */

/** Units written as abbreviations, which never take a plural. */
const ABBREVIATIONS = new Set(['kg', 'g', 'ml', 'lb', 'oz']);

/** Irregular plurals worth spelling out. */
const IRREGULAR = {
  loaf: 'loaves',
  box: 'boxes',
  bunch: 'bunches',
  dozen: 'dozen',
};

export function formatNumber(value) {
  if (value === null || value === undefined) return '';
  const number = Number(value);
  if (Number.isNaN(number)) return '';
  return Number.isInteger(number) ? String(number) : String(Number(number.toFixed(2)));
}

/** Pluralise a unit for the given quantity. */
export function formatUnit(unit, quantity) {
  if (!unit) return '';
  if (ABBREVIATIONS.has(unit)) return unit;
  if (quantity === 1) return unit;
  return IRREGULAR[unit] || `${unit}s`;
}

/**
 * "2 bottles", "1 kg", "× 3" when there is no unit.
 * Used for the quantity badge next to a list item.
 */
export function formatQuantity(item) {
  const quantity = item.quantity ?? 1;
  const pretty = formatNumber(quantity);
  if (!item.unit) return `× ${pretty}`;
  return `${pretty} ${formatUnit(item.unit, quantity)}`;
}

/**
 * "2 bottles of water", "5 oranges", "milk".
 * Used in confirmation sentences, where the item name is part of the phrase.
 */
export function formatItemPhrase({ name, quantity = null, unit = null }) {
  const parts = [];
  if (quantity !== null && quantity !== undefined) parts.push(formatNumber(quantity));
  if (unit) {
    parts.push(formatUnit(unit, quantity ?? 1));
    parts.push('of');
  }
  parts.push(name);
  return parts.filter(Boolean).join(' ');
}

export function formatList(items) {
  if (!items || !items.length) return '';
  if (items.length === 1) return items[0];
  if (items.length === 2) return `${items[0]} and ${items[1]}`;
  return `${items.slice(0, -1).join(', ')}, and ${items[items.length - 1]}`;
}

export function money(value) {
  return `$${Number(value).toFixed(2)}`;
}
