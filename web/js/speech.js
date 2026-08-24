/**
 * Thin wrapper around the Web Speech API.
 *
 * Speech recognition is the one part of this application that cannot live in
 * Python: it is a browser capability. Isolating it here means the rest of the
 * app talks to a four-method interface and never touches a vendor-prefixed
 * global, and it keeps every "what if this browser can't do it" branch in one
 * file.
 *
 * Support as of writing: Chrome, Edge and Safari implement it (Chrome and Edge
 * stream audio to a cloud service). Firefox does not. `isSupported` is what the
 * UI branches on, and the typed-command path works identically either way.
 */

const SpeechRecognitionImpl =
  window.SpeechRecognition || window.webkitSpeechRecognition || null;

/** Human-readable copy for the error codes the spec defines. */
const ERROR_MESSAGES = {
  'no-speech': "I didn't hear anything. Tap the microphone and try again.",
  'audio-capture': 'No microphone was found. Check that one is connected.',
  'not-allowed':
    'Microphone access is blocked. Allow it in your browser settings, or type your command below.',
  'service-not-allowed':
    'Your browser blocked the speech service. You can still type commands below.',
  network: 'Speech recognition needs a network connection. Please check yours.',
  aborted: null, // User-initiated stop; not worth surfacing.
  'language-not-supported':
    "This browser can't recognise the selected language. Try English, or type your command.",
};

export const isSupported = Boolean(SpeechRecognitionImpl);

/**
 * Create a recognizer.
 *
 * @param {object} handlers
 * @param {(transcript: string) => void} handlers.onResult   Final transcript.
 * @param {(transcript: string) => void} handlers.onInterim  Partial transcript.
 * @param {(message: string, code: string) => void} handlers.onError
 * @param {() => void} handlers.onStart
 * @param {() => void} handlers.onEnd
 */
export function createRecognizer({
  onResult = () => {},
  onInterim = () => {},
  onError = () => {},
  onStart = () => {},
  onEnd = () => {},
} = {}) {
  let recognition = null;
  let listening = false;
  // Distinguishes a user-requested stop from the engine ending on its own,
  // so we don't report "aborted" as a failure.
  let stoppedByUser = false;

  function build(language) {
    const instance = new SpeechRecognitionImpl();
    instance.lang = language;
    instance.continuous = false;      // One command per tap.
    instance.interimResults = true;   // Drives the live transcript.
    instance.maxAlternatives = 1;

    instance.onstart = () => {
      listening = true;
      onStart();
    };

    instance.onresult = (event) => {
      let interim = '';
      let final = '';
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const result = event.results[i];
        if (result.isFinal) final += result[0].transcript;
        else interim += result[0].transcript;
      }
      if (interim) onInterim(interim.trim());
      if (final.trim()) onResult(final.trim());
    };

    instance.onerror = (event) => {
      const code = event.error || 'unknown';
      if (code === 'aborted' && stoppedByUser) return;
      const message =
        code in ERROR_MESSAGES
          ? ERROR_MESSAGES[code]
          : 'Something went wrong with speech recognition. Please try again.';
      if (message) onError(message, code);
    };

    instance.onend = () => {
      listening = false;
      onEnd();
    };

    return instance;
  }

  return {
    get isListening() {
      return listening;
    },

    isSupported,

    start(language = 'en-US') {
      if (!SpeechRecognitionImpl) {
        onError('Voice input is not supported in this browser.', 'unsupported');
        return false;
      }
      if (listening) return false;

      stoppedByUser = false;
      try {
        // A fresh instance per utterance: reusing one after an error leaves
        // some engines in a state where start() silently never fires.
        recognition = build(language);
        recognition.start();
        return true;
      } catch (error) {
        listening = false;
        onError('Could not start listening. Please try again.', 'start-failed');
        return false;
      }
    },

    stop() {
      stoppedByUser = true;
      if (recognition && listening) {
        try {
          recognition.stop();
        } catch {
          /* Already stopped; nothing to do. */
        }
      }
      listening = false;
    },

    abort() {
      stoppedByUser = true;
      if (recognition) {
        try {
          recognition.abort();
        } catch {
          /* No-op. */
        }
      }
      listening = false;
    },
  };
}
