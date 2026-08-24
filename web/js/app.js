/**
 * Application orchestrator.
 *
 * Owns the flow that everything else serves:
 *
 *   speech (or typing) -> /api/parse -> intent dispatch -> store -> re-render
 *
 * The dispatch table below is the whole "what does the app do" surface. Each
 * handler takes a parsed command and returns the sentence shown in the Action
 * row, so a new intent means one new entry rather than a new branch in three
 * different places.
 */

import { ApiError, fetchSuggestions, fetchLanguages, parseCommand } from './api.js';
import { formatItemPhrase, formatList, formatNumber, formatUnit } from './format.js';
import { createRecognizer, isSupported } from './speech.js';
import { store } from './store.js';
import * as ui from './ui.js';

const IDLE_MESSAGE = isSupported
  ? 'Tap the microphone and speak'
  : 'Type a command below to get started';

/** A command held back waiting for a yes/no. */
let pendingConfirmation = null;
let suggestionsRequestId = 0;
/** Language packs from /api/languages, used to label detected languages. */
let languagePacks = [];

/* ------------------------------------------------------------------ */
/* Intent handlers                                                     */
/* ------------------------------------------------------------------ */

function itemsOf(command) {
  if (Array.isArray(command.items) && command.items.length) return command.items;
  if (!command.item) return [];
  return [
    {
      item: command.item,
      quantity: command.quantity,
      unit: command.unit,
      attributes: command.attributes,
      category: command.category,
    },
  ];
}

function displayNameFor(entry) {
  return [...(entry.attributes || []), entry.item].filter(Boolean).join(' ');
}

function handleAdd(command) {
  const entries = itemsOf(command);
  if (!entries.length) {
    return { ok: false, message: "I didn't catch what to add. Try \"add milk\"." };
  }

  const added = [];
  for (const entry of entries) {
    const name = displayNameFor(entry);
    const result = store.add({
      name,
      quantity: entry.quantity,
      unit: entry.unit,
      category: entry.category || 'Other',
    });
    if (result) {
      added.push(
        formatItemPhrase({ name, quantity: entry.quantity, unit: entry.unit })
      );
    }
  }

  if (!added.length) {
    return { ok: false, message: "I couldn't add that. Try naming the item again." };
  }
  return { ok: true, message: `Added ${formatList(added)}`, undoable: true };
}

function handleRemove(command) {
  const entries = itemsOf(command);
  if (!entries.length) {
    return { ok: false, message: 'Tell me what to remove, for example "remove milk".' };
  }

  const removed = [];
  const missing = [];
  for (const entry of entries) {
    const result = store.remove(entry.item, entry.quantity);
    if (!result) {
      missing.push(entry.item);
      continue;
    }
    if (result.removedAll) {
      removed.push(result.name);
    } else {
      const took = formatItemPhrase({
        name: result.name,
        quantity: result.removed,
        unit: result.unit,
      });
      const left = result.unit
        ? `${formatNumber(result.remaining)} ${formatUnit(result.unit, result.remaining)}`
        : formatNumber(result.remaining);
      removed.push(`${took} (${left} left)`);
    }
  }

  if (!removed.length) {
    return { ok: false, message: `"${formatList(missing)}" isn't on your list.` };
  }
  const note = missing.length
    ? ` (${formatList(missing)} wasn't on your list)`
    : '';
  return {
    ok: true,
    message: `Removed ${formatList(removed)}${note}`,
    undoable: true,
  };
}

function handleUpdate(command) {
  const updated = store.update(command.item, {
    quantity: command.quantity,
    unit: command.unit,
    replacement: command.replacement,
    category: command.category,
  });
  if (!updated) {
    return {
      ok: false,
      message: command.item
        ? `"${command.item}" isn't on your list.`
        : 'Your list is empty, so there is nothing to change.',
    };
  }
  if (command.replacement) {
    return { ok: true, message: `Changed to ${command.replacement}`, undoable: true };
  }
  const unit = updated.unit
    ? ` ${formatUnit(updated.unit, updated.quantity)}`
    : '';
  return {
    ok: true,
    message: `${updated.name} is now ${formatNumber(updated.quantity)}${unit}`,
    undoable: true,
  };
}

function handleComplete(command) {
  const entries = itemsOf(command);
  if (!entries.length) {
    return { ok: false, message: 'Which item did you get?' };
  }
  const done = [];
  for (const entry of entries) {
    const res = store.complete(entry.item);
    if (res) done.push(res.name);
  }
  if (!done.length) {
    return { ok: false, message: 'None of those items are on your list.' };
  }
  return { ok: true, message: `Ticked off ${formatList(done)}` };
}

function handleShow() {
  const count = store.items.length;
  ui.hideSearch();
  document.getElementById('list-section')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  if (!count) return { ok: true, message: 'Your list is empty' };
  const summary = store.items
    .slice(0, 4)
    .map((item) => item.name)
    .join(', ');
  const more = count > 4 ? `, and ${count - 4} more` : '';
  return { ok: true, message: `${count} item${count === 1 ? '' : 's'}: ${summary}${more}` };
}

function handleClear() {
  const removed = store.clearAll();
  if (!removed) return { ok: true, message: 'Your list was already empty' };
  return {
    ok: true,
    message: `Cleared ${removed} item${removed === 1 ? '' : 's'}`,
    undoable: true,
  };
}

function handleSearch(command, response) {
  const results = response.search;
  if (!results) {
    return { ok: false, message: "I couldn't run that search. Please try again." };
  }
  ui.renderSearch(results, cardHandlers());
  document.getElementById('search-section')?.scrollIntoView({
    behavior: 'smooth',
    block: 'start',
  });
  if (!results.total) {
    return { ok: true, message: 'No exact matches — showing the closest options' };
  }
  return {
    ok: true,
    message: `Found ${results.total} match${results.total === 1 ? '' : 'es'}`,
  };
}

const HANDLERS = {
  ADD_ITEM: handleAdd,
  REMOVE_ITEM: handleRemove,
  UPDATE_ITEM: handleUpdate,
  COMPLETE_ITEM: handleComplete,
  SHOW_LIST: handleShow,
  CLEAR_LIST: handleClear,
  SEARCH_PRODUCT: handleSearch,
};

/* ------------------------------------------------------------------ */
/* Command flow                                                        */
/* ------------------------------------------------------------------ */

/** Plain-language description of what the parser understood. */
function describeCommand(command) {
  const quantityPhrase =
    command.quantity !== null && command.quantity !== undefined
      ? formatNumber(command.quantity) +
        (command.unit ? ` ${formatUnit(command.unit, command.quantity)}` : '')
      : '';

  const detail = [];
  if (command.intent === 'UPDATE_ITEM') {
    // Reads as "milk → almond milk" / "pasta → 3 packets", which matches the
    // direction the user spoke it in.
    const target = command.item || 'the last item';
    const outcome = command.replacement || quantityPhrase;
    detail.push(outcome ? `${target} → ${outcome}` : target);
  } else {
    if (quantityPhrase) detail.push(quantityPhrase);
    if (command.brand) detail.push(command.brand);
    detail.push(...(command.attributes || []));
    if (command.item) detail.push(command.item);
  }

  const prices = [];
  if (command.min_price !== null && command.min_price !== undefined) {
    prices.push(`over $${command.min_price}`);
  }
  if (command.max_price !== null && command.max_price !== undefined) {
    prices.push(`under $${command.max_price}`);
  }

  const readable = {
    ADD_ITEM: 'Add', REMOVE_ITEM: 'Remove', UPDATE_ITEM: 'Change',
    COMPLETE_ITEM: 'Tick off', SEARCH_PRODUCT: 'Search', SHOW_LIST: 'Show list',
    CLEAR_LIST: 'Clear list', CONFIRM: 'Confirm', CANCEL: 'Cancel',
    UNKNOWN: 'Not understood',
  }[command.intent] || command.intent;

  return [readable, detail.join(' '), prices.join(' and ')]
    .filter(Boolean)
    .join(' · ');
}

/** Run a command that has already been parsed and confirmed. */
function execute(command, response) {
  if (
    Array.isArray(command.items) &&
    command.items.length > 1 &&
    command.items.some((item) => item.intent && item.intent !== command.intent)
  ) {
    const initialSnapshot = JSON.parse(JSON.stringify(store.items));
    const results = [];
    for (const entry of command.items) {
      const itemIntent = entry.intent || command.intent;
      const subCommand = {
        ...command,
        intent: itemIntent,
        items: [entry],
        item: entry.item,
        quantity: entry.quantity,
        unit: entry.unit,
        brand: entry.brand,
        attributes: entry.attributes,
        category: entry.category,
      };
      const handler = HANDLERS[itemIntent];
      if (handler) {
        try {
          const res = handler(subCommand, response);
          if (res && res.message) results.push(res);
        } catch (err) {
          console.error(`Sub-command ${itemIntent} failed`, err);
        }
      }
    }

    if (!results.length) {
      return { ok: false, message: "Could not apply compound command." };
    }

    // Set initial snapshot so undo reverts all multi-intent operations
    store.undoSnapshot = initialSnapshot;

    const allOk = results.some((r) => r.ok);
    const messages = results.map((r) => r.message).filter(Boolean);
    return {
      ok: allOk,
      message: messages.join('. '),
      undoable: results.some((r) => r.undoable),
    };
  }

  const handler = HANDLERS[command.intent];
  if (!handler) {
    return { ok: false, message: "I don't know how to do that yet." };
  }
  try {
    return handler(command, response);
  } catch (error) {
    console.error('Command failed', error);
    return { ok: false, message: 'Something went wrong applying that command.' };
  }
}

function applyResult(result) {
  render();
  ui.showFeedback({ action: result.message });
  ui.setMicState('idle', result.message, result.ok ? 'success' : 'error');

  if (result.undoable) {
    ui.showToast(result.message, {
      undo: () => {
        if (store.undo()) {
          render();
          ui.setMicState('idle', 'Undone', 'success');
          refreshSuggestions();
        }
      },
    });
  }
  if (result.ok) refreshSuggestions();
}

/**
 * The single entry point for a user utterance, typed or spoken.
 */
async function runCommand(transcript) {
  const text = String(transcript || '').trim();
  if (!text) {
    ui.setMicState('idle', "I didn't hear anything. Try again.", 'error');
    return;
  }

  // A pending confirmation swallows the next utterance.
  if (pendingConfirmation) {
    await resolveConfirmationByVoice(text);
    return;
  }

  ui.showMicError(null);
  ui.setMicState('processing', 'Understanding your request…');
  ui.showFeedback({ heard: text, understood: 'Working on it…' });

  let response;
  try {
    response = await parseCommand(text, store.language);
  } catch (error) {
    const message =
      error instanceof ApiError ? error.message : 'Something went wrong. Please try again.';
    ui.setMicState('idle', message, 'error');
    ui.showFeedback({ heard: text, understood: null, action: null });
    return;
  }

  const command = response.command;

  if (command.intent === 'UNKNOWN') {
    ui.showFeedback({ heard: text, understood: 'Not understood' });
    ui.setMicState(
      'idle',
      "Sorry, I didn't understand that. Try \"add milk\" or \"find apples\".",
      'error'
    );
    return;
  }

  if (command.intent === 'CONFIRM' || command.intent === 'CANCEL') {
    ui.showFeedback({ heard: text, understood: describeCommand(command) });
    ui.setMicState('idle', 'Nothing was waiting for confirmation.', null);
    return;
  }

  // The parser may have found the utterance was in another language entirely.
  // Move the picker to match, so the next spoken command uses the right
  // speech-recognition locale rather than failing the same way.
  const detectedPack = command.detected_language
    ? languagePacks.find((pack) => pack.locale === command.detected_language)
    : null;
  if (detectedPack && detectedPack.locale !== store.language) {
    store.setLanguage(detectedPack.locale);
    ui.setLanguageSelection(detectedPack.locale);
    loadExamples();
    // No toast here: the command about to run raises its own, which would
    // replace this one within the same frame. The tag on the Understood line
    // and the picker visibly moving are what communicate the switch.
  }

  ui.showFeedback({
    heard: text,
    understood: describeCommand(command),
    source: command.source,
    detected: detectedPack ? detectedPack.label : null,
  });

  // Destructive commands, and anything the parser is unsure about, get a
  // confirmation step rather than being applied silently.
  if (command.requires_confirmation) {
    const count = store.items.length;
    pendingConfirmation = { command, response };
    ui.askConfirmation(
      count
        ? `This will remove all ${count} item${count === 1 ? '' : 's'} from your list. Say "confirm" or tap Confirm.`
        : 'Your list is already empty. Clear anyway?'
    );
    ui.setMicState('idle', 'Waiting for confirmation…');
    return;
  }

  // The server owns the confidence threshold and reports the decision, so
  // there is no second copy of the number here to drift out of sync.
  if (command.needs_clarification) {
    pendingConfirmation = { command, response };
    ui.askConfirmation(`Did you mean: ${describeCommand(command)}?`);
    ui.setMicState('idle', "I'm not certain — please confirm.");
    return;
  }

  applyResult(execute(command, response));
}

async function resolveConfirmationByVoice(text) {
  let intent = 'UNKNOWN';
  try {
    const response = await parseCommand(text, store.language);
    intent = response.command.intent;
  } catch {
    /* Fall through to the "didn't catch that" branch below. */
  }

  if (intent === 'CONFIRM') {
    acceptConfirmation();
  } else if (intent === 'CANCEL') {
    rejectConfirmation();
  } else {
    ui.setMicState('idle', 'Please say "confirm" or "cancel".', 'error');
  }
}

function acceptConfirmation() {
  if (!pendingConfirmation) return;
  const { command, response } = pendingConfirmation;
  pendingConfirmation = null;
  ui.hideConfirmation();
  applyResult(execute(command, response));
}

function rejectConfirmation() {
  pendingConfirmation = null;
  ui.hideConfirmation();
  ui.setMicState('idle', 'Cancelled — nothing changed.');
  ui.showFeedback({ action: 'Cancelled' });
}

/* ------------------------------------------------------------------ */
/* Rendering + suggestions                                             */
/* ------------------------------------------------------------------ */

function cardHandlers() {
  return {
    onAdd: (product) => {
      const result = store.add({
        name: product.name,
        quantity: 1,
        unit: product.unit === 'each' ? null : product.unit,
        category: product.category,
      });
      render();
      refreshSuggestions();
      ui.showToast(`Added ${product.name}`, {
        undo: () => {
          if (store.undo()) {
            render();
            refreshSuggestions();
          }
        },
      });
      return result;
    },
    onPickAlternative: (product) => cardHandlers().onAdd(product),
  };
}

function render() {
  ui.renderList(store.items, {
    onToggle: (id) => {
      store.toggleComplete(id);
      render();
    },
    onRemove: (id) => {
      const removed = store.removeById(id);
      render();
      refreshSuggestions();
      if (removed) {
        ui.showToast(`Removed ${removed.name}`, {
          undo: () => {
            if (store.undo()) {
              render();
              refreshSuggestions();
            }
          },
        });
      }
    },
    onQuantity: (id, delta) => {
      const item = store.items.find((entry) => entry.id === id);
      if (!item) return;
      store.setQuantity(id, (item.quantity ?? 1) + delta);
      render();
    },
  });
}

async function refreshSuggestions() {
  const requestId = ++suggestionsRequestId;
  ui.renderSuggestionsLoading();
  try {
    const response = await fetchSuggestions({
      history: store.history,
      currentItems: store.itemNames(),
      limit: 6,
    });
    // Ignore a slow response that a newer request has already superseded.
    if (requestId !== suggestionsRequestId) return;
    ui.renderSuggestions(response.suggestions, cardHandlers());
  } catch (error) {
    if (requestId !== suggestionsRequestId) return;
    ui.renderSuggestionsError(
      error instanceof ApiError
        ? `Suggestions unavailable: ${error.message}`
        : 'Suggestions are unavailable right now.'
    );
  }
}

/* ------------------------------------------------------------------ */
/* Speech wiring                                                       */
/* ------------------------------------------------------------------ */

const recognizer = createRecognizer({
  onStart: () => {
    ui.showMicError(null);
    ui.setMicState('listening', 'Listening…');
    ui.showFeedback({ heard: '…' });
  },
  onInterim: (text) => {
    ui.showFeedback({ heard: text });
  },
  onResult: (text) => {
    runCommand(text);
  },
  onError: (message) => {
    ui.setMicState('idle', IDLE_MESSAGE);
    ui.showMicError(message);
  },
  onEnd: () => {
    // Only reset if a result isn't already being processed.
    if (ui.elements.mic.dataset.state === 'listening') {
      ui.setMicState('idle', IDLE_MESSAGE);
    }
  },
});

/* ------------------------------------------------------------------ */
/* Bootstrap                                                           */
/* ------------------------------------------------------------------ */

function bindEvents() {
  ui.elements.mic.addEventListener('click', () => {
    if (!isSupported) {
      ui.elements.textInput.focus();
      return;
    }
    if (recognizer.isListening) {
      recognizer.stop();
      ui.setMicState('idle', IDLE_MESSAGE);
    } else {
      recognizer.start(store.language);
    }
  });

  ui.elements.textForm.addEventListener('submit', (event) => {
    event.preventDefault();
    const value = ui.elements.textInput.value;
    ui.elements.textInput.value = '';
    runCommand(value);
  });

  ui.elements.confirmYes.addEventListener('click', acceptConfirmation);
  ui.elements.confirmNo.addEventListener('click', rejectConfirmation);

  ui.elements.language.addEventListener('change', (event) => {
    store.setLanguage(event.target.value);
    if (recognizer.isListening) recognizer.stop();
    loadExamples();
    ui.setMicState('idle', IDLE_MESSAGE);
  });

  ui.elements.searchClose.addEventListener('click', ui.hideSearch);

  ui.elements.clearCompleted.addEventListener('click', () => {
    const removed = store.clearCompleted();
    render();
    if (removed) {
      ui.showToast(`Cleared ${removed} completed item${removed === 1 ? '' : 's'}`, {
        undo: () => {
          if (store.undo()) render();
        },
      });
    }
  });

  ui.elements.clearAll.addEventListener('click', () => {
    if (!store.items.length) return;
    pendingConfirmation = { command: { intent: 'CLEAR_LIST' }, response: null };
    ui.askConfirmation(
      `This will remove all ${store.items.length} item${
        store.items.length === 1 ? '' : 's'
      } from your list.`
    );
  });

  ui.elements.resetDemo.addEventListener('click', () => {
    store.resetDemo();
    store.load();
    render();
    refreshSuggestions();
    ui.hideSearch();
    ui.showToast('Demo data restored');
  });

  // Escape closes whatever is open, in priority order.
  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape') return;
    if (pendingConfirmation) rejectConfirmation();
    else if (!ui.elements.searchSection.hidden) ui.hideSearch();
    else if (recognizer.isListening) recognizer.stop();
  });
}

function loadExamples() {
  const pack = languagePacks.find((language) => language.locale === store.language);
  const examples = pack?.examples || [
    'Add 2 bottles of water',
    'Find toothpaste under $5',
    'Remove milk from my list',
    'Show my list',
  ];
  ui.renderExamples(examples, (example) => {
    ui.elements.textInput.value = example;
    runCommand(example);
  });
}

async function loadLanguages() {
  try {
    const response = await fetchLanguages();
    languagePacks = response.languages || [];
    // A stored locale from a previous version may no longer exist.
    if (!languagePacks.some((language) => language.locale === store.language)) {
      store.setLanguage(languagePacks[0]?.locale || 'en-US');
    }
    ui.renderLanguages(languagePacks, store.language);
  } catch {
    // Keep the single hard-coded English option from the HTML.
    languagePacks = [];
  }
  loadExamples();
}

function init() {
  store.load();
  ui.showUnsupportedBanner(!isSupported);
  ui.setMicState('idle', IDLE_MESSAGE);
  if (!isSupported) {
    ui.elements.mic.setAttribute('aria-label', 'Voice input unavailable — type your command instead');
  }
  if (!store.storageAvailable) {
    ui.showMicError(
      "This browser is blocking local storage, so your list won't be saved between visits."
    );
  }

  bindEvents();
  render();
  loadLanguages();
  refreshSuggestions();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
