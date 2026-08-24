/**
 * Rendering.
 *
 * Pure DOM writes driven by state passed in from app.js. Nothing here mutates
 * the store or calls the API, which keeps "what the app does" and "what the app
 * looks like" separable.
 *
 * All user and API text goes in through `textContent` or `createElement`, never
 * `innerHTML`, so a product name or transcript can never inject markup.
 */

import { formatQuantity, money } from './format.js';

const $ = (id) => document.getElementById(id);

export const elements = {
  mic: $('mic'),
  micStatus: $('mic-status'),
  micError: $('mic-error'),
  unsupportedBanner: $('unsupported-banner'),
  feedback: $('feedback'),
  heardRow: $('fb-heard-row'),
  heard: $('fb-heard'),
  understoodRow: $('fb-understood-row'),
  understood: $('fb-understood'),
  actionRow: $('fb-action-row'),
  action: $('fb-action'),
  confirmBox: $('confirm-box'),
  confirmText: $('confirm-text'),
  confirmYes: $('confirm-yes'),
  confirmNo: $('confirm-no'),
  textForm: $('text-form'),
  textInput: $('text-input'),
  examples: $('examples'),
  language: $('language'),
  listContainer: $('list-container'),
  listEmpty: $('list-empty'),
  listCount: $('list-count'),
  listActions: $('list-actions'),
  clearCompleted: $('clear-completed'),
  clearAll: $('clear-all'),
  searchSection: $('search-section'),
  searchFilters: $('search-filters'),
  searchResults: $('search-results'),
  searchClose: $('search-close'),
  suggestions: $('suggestions'),
  suggestionsState: $('suggestions-state'),
  toast: $('toast'),
  toastText: $('toast-text'),
  toastUndo: $('toast-undo'),
  resetDemo: $('reset-demo'),
};

/** Category display order, so the list reads like a shop floor plan. */
const CATEGORY_ORDER = [
  'Produce', 'Dairy', 'Bakery', 'Meat & Seafood', 'Pantry', 'Frozen',
  'Beverages', 'Snacks', 'Personal Care', 'Household', 'Baby', 'Other',
];

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = String(text);
  return node;
}

/* ---------------- microphone + feedback ---------------- */

const MIC_LABELS = {
  idle: 'Start listening for a voice command',
  listening: 'Stop listening',
  processing: 'Processing your command',
};

export function setMicState(state, message, tone = null) {
  elements.mic.dataset.state = state;
  elements.mic.setAttribute('aria-label', MIC_LABELS[state] || MIC_LABELS.idle);
  elements.mic.disabled = state === 'processing';
  elements.micStatus.textContent = message;
  if (tone) elements.micStatus.dataset.tone = tone;
  else delete elements.micStatus.dataset.tone;
}

export function showFeedback({ heard, understood, action, source, detected }) {
  const rows = [
    [elements.heardRow, elements.heard, heard],
    [elements.understoodRow, elements.understood, understood],
    [elements.actionRow, elements.action, action],
  ];
  let any = false;
  for (const [row, target, value] of rows) {
    if (value) {
      target.textContent = value;
      row.hidden = false;
      any = true;
    } else {
      row.hidden = true;
    }
  }
  // Mark interpretations that came from the optional LLM fallback rather than
  // the deterministic parser, so the two are never confused.
  if (source === 'llm' && understood) {
    const tag = el('span', 'source-tag', 'AI');
    // Without a label this runs straight into the preceding word for a screen
    // reader, as "milkAI". The visible text stays the short badge.
    tag.setAttribute('aria-label', 'interpreted by AI, please confirm');
    elements.understood.appendChild(tag);
  }

  // Say so when the utterance turned out to be in a language other than the
  // one selected. Silently switching the picker would be worse than not
  // switching it: the user needs to know why it moved.
  if (detected && understood) {
    const tag = el('span', 'source-tag lang-tag', detected);
    tag.setAttribute('aria-label', `detected language: ${detected}`);
    elements.understood.appendChild(tag);
  }

  elements.feedback.hidden = !any;
}

export function showMicError(message) {
  if (!message) {
    elements.micError.hidden = true;
    return;
  }
  elements.micError.textContent = message;
  elements.micError.hidden = false;
}

export function showUnsupportedBanner(show) {
  elements.unsupportedBanner.hidden = !show;
}

/* ---------------- confirmation ---------------- */

export function askConfirmation(message) {
  elements.confirmText.textContent = message;
  elements.confirmBox.hidden = false;
  elements.confirmYes.focus();
}

export function hideConfirmation() {
  elements.confirmBox.hidden = true;
}

/* ---------------- examples + languages ---------------- */

export function renderExamples(examples, onPick) {
  elements.examples.replaceChildren();
  for (const example of examples.slice(0, 4)) {
    const chip = el('button', 'example-chip', example);
    chip.type = 'button';
    chip.addEventListener('click', () => onPick(example));
    elements.examples.appendChild(chip);
  }
}

export function setLanguageSelection(locale) {
  if ([...elements.language.options].some((option) => option.value === locale)) {
    elements.language.value = locale;
  }
}

export function renderLanguages(languages, selected) {
  elements.language.replaceChildren();
  for (const language of languages) {
    const option = el('option', null, language.label);
    option.value = language.locale;
    if (language.locale === selected) option.selected = true;
    elements.language.appendChild(option);
  }
}

/* ---------------- shopping list ---------------- */

export function renderList(items, handlers) {
  elements.listContainer.replaceChildren();

  const count = items.length;
  const done = items.filter((item) => item.completed).length;
  elements.listCount.textContent =
    count === 0 ? 'Empty' : `${done}/${count} done`;
  elements.listEmpty.hidden = count > 0;
  elements.listActions.hidden = count === 0;
  elements.clearCompleted.disabled = done === 0;

  if (count === 0) return;

  const grouped = new Map();
  for (const item of items) {
    const category = item.category || 'Other';
    if (!grouped.has(category)) grouped.set(category, []);
    grouped.get(category).push(item);
  }

  const ordered = [...grouped.keys()].sort(
    (a, b) => CATEGORY_ORDER.indexOf(a) - CATEGORY_ORDER.indexOf(b)
  );

  for (const category of ordered) {
    const group = el('div', 'category-group');
    // Aisle label, then a dotted leader, then the count - set like a receipt
    // line. The leader is drawn in CSS so it stays out of the accessible name.
    const title = el('h3', 'category-title');
    title.appendChild(el('span', 'category-label', category));
    const size = grouped.get(category).length;
    const count = el('span', 'category-count', size);
    // Without this the heading reads as "Produce1": the leader between them is
    // drawn in CSS, so there is no whitespace in the accessible name.
    count.setAttribute('aria-label', `${size} item${size === 1 ? '' : 's'}`);
    title.appendChild(count);
    group.appendChild(title);

    const list = el('ul');
    list.style.listStyle = 'none';
    list.style.margin = '0';
    list.style.padding = '0';

    for (const item of grouped.get(category)) {
      list.appendChild(renderItemRow(item, handlers));
    }
    group.appendChild(list);
    elements.listContainer.appendChild(group);
  }
}

function renderItemRow(item, handlers) {
  const row = el('li', 'item-row');
  row.dataset.done = String(Boolean(item.completed));

  const check = el('button', 'item-check', '✓');
  check.type = 'button';
  check.setAttribute('aria-pressed', String(Boolean(item.completed)));
  check.setAttribute(
    'aria-label',
    item.completed ? `Mark ${item.name} as not bought` : `Mark ${item.name} as bought`
  );
  check.addEventListener('click', () => handlers.onToggle(item.id));

  const body = el('div', 'item-body');
  body.appendChild(el('div', 'item-name', item.name));
  const metaBits = [formatQuantity(item)];
  if (item.demo) metaBits.push('sample');
  body.appendChild(el('div', 'item-meta', metaBits.join(' · ')));

  const controls = el('div', 'qty-controls');
  const minus = el('button', 'qty-btn', '−');
  minus.type = 'button';
  minus.setAttribute('aria-label', `Decrease quantity of ${item.name}`);
  minus.addEventListener('click', () => handlers.onQuantity(item.id, -1));

  const value = el('span', 'qty-value', formatQuantity(item));
  value.setAttribute('aria-live', 'off');

  const plus = el('button', 'qty-btn', '+');
  plus.type = 'button';
  plus.setAttribute('aria-label', `Increase quantity of ${item.name}`);
  plus.addEventListener('click', () => handlers.onQuantity(item.id, 1));

  controls.append(minus, value, plus);

  const remove = el('button', 'item-remove', '✕');
  remove.type = 'button';
  remove.setAttribute('aria-label', `Remove ${item.name} from the list`);
  remove.addEventListener('click', () => handlers.onRemove(item.id));

  row.append(check, body, controls, remove);
  return row;
}

/* ---------------- product cards ---------------- */

function productCard(product, { reason = null, onAdd, onPickAlternative } = {}) {
  const card = el('div', 'card');
  card.appendChild(el('span', 'card-emoji', product.emoji || '🛒'));

  const body = el('div', 'card-body');
  body.appendChild(el('div', 'card-name', product.name));

  const meta = [product.brand, product.category].filter(Boolean).join(' · ');
  if (meta) body.appendChild(el('div', 'card-meta', meta));

  const priceRow = el('div', 'card-price', money(product.price));
  if (!product.in_stock) {
    const badge = el('span', 'badge badge-out', 'Out of stock');
    badge.style.marginLeft = '.4rem';
    priceRow.appendChild(badge);
  }
  body.appendChild(priceRow);

  if (reason) body.appendChild(el('div', 'card-reason', reason));

  const actions = el('div', 'card-actions');
  const add = el('button', 'btn btn-primary btn-small', 'Add to list');
  add.type = 'button';
  add.setAttribute('aria-label', `Add ${product.name} to your list`);
  add.disabled = !product.in_stock;
  add.addEventListener('click', () => onAdd(product));
  actions.appendChild(add);
  body.appendChild(actions);

  card.appendChild(body);

  if (!product.in_stock && product.alternatives_resolved?.length) {
    const box = el('div', 'alternatives');
    box.appendChild(
      el('div', 'alternatives-title', `${product.name} isn't available. Try these instead:`)
    );
    const list = el('div', 'alt-list');
    for (const alternative of product.alternatives_resolved) {
      const chip = el(
        'button',
        'alt-chip',
        `${alternative.emoji || ''} ${alternative.name} · ${money(alternative.price)}`.trim()
      );
      chip.type = 'button';
      chip.setAttribute('aria-label', `Add ${alternative.name} instead`);
      chip.addEventListener('click', () => onPickAlternative(alternative));
      list.appendChild(chip);
    }
    box.appendChild(list);
    card.appendChild(box);
  }

  return card;
}

export function renderSearch({ filters, hits, total, suggestions }, handlers) {
  elements.searchSection.hidden = false;

  elements.searchFilters.replaceChildren();
  for (const filter of filters || []) {
    elements.searchFilters.appendChild(el('span', 'chip', filter));
  }

  elements.searchResults.replaceChildren();

  if (!hits.length) {
    const empty = el('div', 'empty-state');
    empty.appendChild(el('p', 'empty-title', 'No products matched that'));
    empty.appendChild(
      el('p', null, suggestions?.length
        ? 'Here are the closest things we do have:'
        : 'Try a different name, or relax the price limit.')
    );
    empty.style.gridColumn = '1 / -1';
    elements.searchResults.appendChild(empty);

    for (const product of suggestions || []) {
      elements.searchResults.appendChild(
        productCard(product, { reason: 'Closest match', ...handlers })
      );
    }
    return;
  }

  for (const hit of hits) {
    const product = { ...hit.product, alternatives_resolved: hit.alternatives };
    elements.searchResults.appendChild(productCard(product, handlers));
  }

  if (total > hits.length) {
    const note = el('p', 'panel-note', `Showing ${hits.length} of ${total} matches.`);
    note.style.gridColumn = '1 / -1';
    elements.searchResults.appendChild(note);
  }
}

export function hideSearch() {
  elements.searchSection.hidden = true;
}

export function renderSuggestions(suggestions, handlers) {
  elements.suggestions.replaceChildren();
  elements.suggestionsState.textContent = '';

  if (!suggestions.length) {
    const empty = el('p', 'panel-note', 'Add a few items and suggestions will appear here.');
    elements.suggestions.appendChild(empty);
    return;
  }

  for (const suggestion of suggestions) {
    const card = productCard(suggestion.product, {
      reason: suggestion.explanation,
      ...handlers,
    });
    if (suggestion.reason === 'seasonal') {
      const badge = el('span', 'badge badge-season', 'In season');
      card.querySelector('.card-body').appendChild(badge);
    }
    elements.suggestions.appendChild(card);
  }
}

export function renderSuggestionsLoading() {
  elements.suggestionsState.textContent = 'Updating…';
  elements.suggestions.replaceChildren();
  for (let i = 0; i < 4; i += 1) {
    elements.suggestions.appendChild(el('div', 'skeleton'));
  }
}

export function renderSuggestionsError(message) {
  elements.suggestionsState.textContent = '';
  elements.suggestions.replaceChildren();
  elements.suggestions.appendChild(el('p', 'panel-note', message));
}

/* ---------------- toast ---------------- */

let toastTimer = null;

export function showToast(message, { undo = null, duration = 5000 } = {}) {
  window.clearTimeout(toastTimer);
  elements.toastText.textContent = message;
  elements.toast.hidden = false;

  if (undo) {
    elements.toastUndo.hidden = false;
    elements.toastUndo.onclick = () => {
      undo();
      hideToast();
    };
  } else {
    elements.toastUndo.hidden = true;
    elements.toastUndo.onclick = null;
  }

  toastTimer = window.setTimeout(hideToast, duration);
}

export function hideToast() {
  elements.toast.hidden = true;
  window.clearTimeout(toastTimer);
}
