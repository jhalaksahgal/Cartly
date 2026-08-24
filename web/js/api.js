/**
 * API client.
 *
 * Every call is time-limited and every failure becomes a readable message, so
 * a flaky network shows "Couldn't reach the server" rather than an unhandled
 * rejection in the console and a UI stuck on a spinner.
 */

const TIMEOUT_MS = 8000;

export class ApiError extends Error {
  constructor(message, { status = 0, cause = null } = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.cause = cause;
  }
}

async function request(path, options = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);

  try {
    const response = await fetch(path, {
      ...options,
      signal: controller.signal,
      headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    });

    if (!response.ok) {
      let detail = `Request failed (${response.status})`;
      try {
        const body = await response.json();
        if (body?.detail) {
          detail = typeof body.detail === 'string' ? body.detail : detail;
        }
      } catch {
        /* Non-JSON error body; keep the generic message. */
      }
      throw new ApiError(detail, { status: response.status });
    }

    return await response.json();
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (error.name === 'AbortError') {
      throw new ApiError('That took too long. Please try again.', { cause: error });
    }
    throw new ApiError("Couldn't reach the server. Check your connection.", {
      cause: error,
    });
  } finally {
    clearTimeout(timer);
  }
}

/** Interpret an utterance. Search results ride along when it was a search. */
export function parseCommand(transcript, language) {
  return request('/api/parse', {
    method: 'POST',
    body: JSON.stringify({ transcript, language }),
  });
}

/** Ranked recommendations with their explanations. */
export function fetchSuggestions({ history, currentItems, limit = 6 }) {
  return request('/api/suggestions', {
    method: 'POST',
    body: JSON.stringify({
      history,
      current_items: currentItems,
      limit,
    }),
  });
}

/** Typed catalog search, using the same engine as the voice path. */
export function searchCatalog({ q = '', brand = null, maxPrice = null, limit = 12 }) {
  const params = new URLSearchParams({ q, limit: String(limit) });
  if (brand) params.set('brand', brand);
  if (maxPrice !== null) params.set('max_price', String(maxPrice));
  return request(`/api/search?${params.toString()}`);
}

/** Substitutes for a named product. */
export function fetchSubstitutes(name, limit = 3) {
  const params = new URLSearchParams({ name, limit: String(limit) });
  return request(`/api/substitutes?${params.toString()}`);
}

/** Supported languages and their example commands. */
export function fetchLanguages() {
  return request('/api/languages');
}
