/**
 * Shopping list state, persisted to localStorage.
 *
 * The list lives entirely in the browser: no accounts, no server-side storage,
 * nothing personal leaving the device except the item names needed to answer a
 * search or suggestions request. Every write is wrapped because localStorage
 * throws in private-browsing modes and when the quota is full - in that case
 * the app keeps working in memory for the session and says so once.
 */

const LIST_KEY = 'cartly.list.v1';
const HISTORY_KEY = 'cartly.history.v1';
const LANG_KEY = 'cartly.language.v1';
const SEEDED_KEY = 'cartly.seeded.v1';

/** Sample purchase history, so recommendations are meaningful on first load. */
const DEMO_HISTORY = [
  { name: 'milk', days_ago: 2, count: 4 },
  { name: 'bread', days_ago: 3, count: 3 },
  { name: 'eggs', days_ago: 5, count: 3 },
  { name: 'bananas', days_ago: 1, count: 2 },
  { name: 'coffee', days_ago: 9, count: 2 },
  { name: 'chicken breast', days_ago: 6, count: 2 },
  { name: 'pasta', days_ago: 12, count: 2 },
];

/** Sample list items, so the first screen shows the product rather than a void. */
const DEMO_ITEMS = [
  { name: 'milk', quantity: 2, unit: 'litre', category: 'Dairy' },
  { name: 'bananas', quantity: 1, unit: 'kg', category: 'Produce' },
  { name: 'pasta', quantity: 1, unit: null, category: 'Pantry' },
];

let storageWorks = true;

function readJSON(key, fallback) {
  try {
    const raw = window.localStorage.getItem(key);
    if (!raw) return fallback;
    const parsed = JSON.parse(raw);
    return parsed ?? fallback;
  } catch (error) {
    // Corrupt or unreadable: drop it rather than crashing on every load.
    console.warn(`Could not read ${key} from storage`, error);
    return fallback;
  }
}

function writeJSON(key, value) {
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
    return true;
  } catch (error) {
    storageWorks = false;
    console.warn(`Could not persist ${key}`, error);
    return false;
  }
}

function makeId() {
  // crypto.randomUUID is unavailable on older Safari and on insecure origins.
  if (window.crypto?.randomUUID) return window.crypto.randomUUID();
  return `id-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

function normalizeName(value) {
  return String(value || '').trim().toLowerCase();
}

/**
 * Find the list item a spoken name refers to.
 *
 * Matching is tiered rather than a plain substring test, and the tolerance
 * differs by operation:
 *
 * - Adding uses `fuzzy: false`. "Add almond milk" when milk is already on the
 *   list must create a second item, not silently bump the quantity of the
 *   first - they are different products.
 * - Removing and updating use fuzzy matching, because "remove milk" should
 *   still find an item recorded as "Whole Milk 1L".
 *
 * Exact matches always win, so "milk" finds "milk" before "almond milk"
 * regardless of which was added first.
 */
function findMatch(items, name, { fuzzy = true } = {}) {
  const needle = normalizeName(name);
  if (!needle) return null;

  const exact = items.find((item) => normalizeName(item.name) === needle);
  if (exact || !fuzzy) return exact || null;

  // Whole-word match: "milk" matches "whole milk", not "milkshake".
  const wordBoundary = items.find((item) =>
    normalizeName(item.name).split(/\s+/).includes(needle)
  );
  if (wordBoundary) return wordBoundary;

  // Last resort, and only for names long enough to be meaningful. Only the
  // "needle is contained in the item" direction: the reverse would make
  // "almond milk" match a plain "milk" entry.
  if (needle.length < 3) return null;
  return items.find((item) => normalizeName(item.name).includes(needle)) || null;
}

export const store = {
  items: [],
  history: [],
  language: 'en-US',
  /** Snapshot of the previous list, powering a single level of undo. */
  undoSnapshot: null,

  get storageAvailable() {
    return storageWorks;
  },

  load() {
    this.items = readJSON(LIST_KEY, []);
    this.history = readJSON(HISTORY_KEY, []);
    this.language = readJSON(LANG_KEY, 'en-US');

    // Seed once, and only if the user has never had anything. A returning user
    // who deliberately emptied their list must not have demo data reappear.
    if (!readJSON(SEEDED_KEY, false)) {
      if (this.items.length === 0) {
        this.items = DEMO_ITEMS.map((item) => ({
          id: makeId(),
          name: item.name,
          quantity: item.quantity,
          unit: item.unit,
          category: item.category,
          completed: false,
          addedAt: new Date().toISOString(),
          demo: true,
        }));
      }
      if (this.history.length === 0) this.history = [...DEMO_HISTORY];
      writeJSON(SEEDED_KEY, true);
      this.save();
    }
    return this;
  },

  save() {
    writeJSON(LIST_KEY, this.items);
    writeJSON(HISTORY_KEY, this.history);
    writeJSON(LANG_KEY, this.language);
  },

  setLanguage(language) {
    this.language = language;
    writeJSON(LANG_KEY, language);
  },

  snapshot() {
    this.undoSnapshot = JSON.parse(JSON.stringify(this.items));
  },

  undo() {
    if (!this.undoSnapshot) return false;
    this.items = this.undoSnapshot;
    this.undoSnapshot = null;
    this.save();
    return true;
  },

  find(name, options) {
    return findMatch(this.items, name, options);
  },

  /**
   * Add an item, or bump the quantity if it is already on the list.
   * Returns { item, merged } so the UI can say "added" vs "updated".
   */
  add({ name, quantity = null, unit = null, category = 'Other' }) {
    const cleaned = String(name || '').trim();
    if (!cleaned) return null;

    this.snapshot();
    // Strict: only merge into an item with the same name, never a related one.
    const existing = this.find(cleaned, { fuzzy: false });
    if (existing) {
      const added = quantity ?? 1;
      existing.quantity = (existing.quantity ?? 1) + added;
      if (unit) existing.unit = unit;
      existing.completed = false;
      this.save();
      return { item: existing, merged: true };
    }

    const item = {
      id: makeId(),
      name: cleaned,
      quantity: quantity ?? 1,
      unit: unit || null,
      category: category || 'Other',
      completed: false,
      addedAt: new Date().toISOString(),
    };
    this.items.push(item);
    this.recordPurchase(cleaned);
    this.save();
    return { item, merged: false };
  },

  remove(name, quantity = null) {
    const target = this.find(name);
    if (!target) return null;

    this.snapshot();
    if (quantity !== null && quantity !== undefined && quantity > 0 && target.quantity > quantity) {
      target.quantity -= quantity;
      this.save();
      return {
        id: target.id,
        name: target.name,
        removed: quantity,
        remaining: target.quantity,
        unit: target.unit,
        removedAll: false,
      };
    }

    this.items = this.items.filter((item) => item.id !== target.id);
    this.save();
    return {
      id: target.id,
      name: target.name,
      removed: target.quantity ?? 1,
      remaining: 0,
      unit: target.unit,
      removedAll: true,
    };
  },

  removeById(id) {
    const target = this.items.find((item) => item.id === id);
    if (!target) return null;
    this.snapshot();
    this.items = this.items.filter((item) => item.id !== id);
    this.save();
    return target;
  },

  /**
   * Change an item's quantity, unit, or identity.
   * `replacement` swaps the product itself ("change milk to almond milk").
   */
  update(name, { quantity = null, unit = null, replacement = null, category = null }) {
    const target = name ? this.find(name) : this.items[this.items.length - 1];
    if (!target) return null;

    this.snapshot();
    if (replacement) {
      target.name = replacement;
      target.category = category || target.category;
      this.recordPurchase(replacement);
    }
    if (quantity !== null && quantity !== undefined) target.quantity = quantity;
    if (unit) target.unit = unit;
    this.save();
    return target;
  },

  setQuantity(id, quantity) {
    const target = this.items.find((item) => item.id === id);
    if (!target) return null;
    if (quantity <= 0) return this.removeById(id);
    this.snapshot();
    target.quantity = quantity;
    this.save();
    return target;
  },

  toggleComplete(id) {
    const target = this.items.find((item) => item.id === id);
    if (!target) return null;
    target.completed = !target.completed;
    this.save();
    return target;
  },

  complete(name) {
    const target = this.find(name);
    if (!target) return null;
    target.completed = true;
    this.save();
    return target;
  },

  clearCompleted() {
    const removed = this.items.filter((item) => item.completed).length;
    if (!removed) return 0;
    this.snapshot();
    this.items = this.items.filter((item) => !item.completed);
    this.save();
    return removed;
  },

  clearAll() {
    const removed = this.items.length;
    if (!removed) return 0;
    this.snapshot();
    this.items = [];
    this.save();
    return removed;
  },

  /** Track what gets added, which is the signal the recommender runs on. */
  recordPurchase(name) {
    const cleaned = String(name || '').trim().toLowerCase();
    if (!cleaned) return;
    const existing = this.history.find((entry) => entry.name.toLowerCase() === cleaned);
    if (existing) {
      existing.count += 1;
      existing.days_ago = 0;
    } else {
      this.history.push({ name: cleaned, days_ago: 0, count: 1 });
    }
    // Keep the payload small; the recommender only needs recent behaviour.
    if (this.history.length > 60) this.history = this.history.slice(-60);
  },

  itemNames() {
    return this.items.map((item) => item.name);
  },

  /** Wipe everything including the seed flag, then reseed on next load. */
  resetDemo() {
    try {
      window.localStorage.removeItem(LIST_KEY);
      window.localStorage.removeItem(HISTORY_KEY);
      window.localStorage.removeItem(SEEDED_KEY);
    } catch (error) {
      console.warn('Could not clear storage', error);
    }
    this.items = [];
    this.history = [];
    this.undoSnapshot = null;
  },
};
