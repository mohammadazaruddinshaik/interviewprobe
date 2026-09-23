// A small, deterministic text-processing layer sitting between a generated
// interview question and the TTS provider (ttsProvider.js). It exists
// purely to make spoken delivery sound natural — it must never change what
// the question *means*.
//
// Hard rule: nothing in this file may paraphrase, summarize, reorder,
// add, or remove meaningful content. Every transformation here is a fixed,
// inspectable string rewrite (markup stripping, whitespace normalization,
// or a literal term substitution), never a judgment call about the text's
// meaning. If a transformation could plausibly change what a question is
// asking, it does not belong here.
//
// The UI must keep showing the original `question.text` unchanged — this
// module's output is for the TTS provider only, never for display.

// Explicit, small, and easy to extend — each entry is the literal spoken
// replacement for a whole-word technical abbreviation the TTS voice would
// otherwise be likely to mis-pronounce (e.g. spelling out "LLM" letter by
// letter, or reading "SQL" as a made-up word). Deliberately conservative:
// an abbreviation is only listed here when its spoken form is unambiguous
// interview-tech usage. Anything ambiguous is left untouched rather than
// guessed at.
const PRONUNCIATION_MAP = {
  LLM: 'L L M',
  RAG: 'R A G',
  API: 'A P I',
  SQL: 'sequel',
  HTTP: 'H T T P',
  HTTPS: 'H T T P S',
  REST: 'rest',
  Redis: 'Redis',
  Qdrant: 'Quadrant',
  PostgreSQL: 'Postgres sequel',
  JSON: 'jay-sawn',
  JWT: 'J W T',
  WebSocket: 'Web Socket',
  STT: 'S T T',
  TTS: 'T T S',
}

// Matches each pronunciation-map key as a whole word only (case-sensitive),
// so e.g. "Api" or "api" inside ordinary prose is left alone — only the
// exact technical abbreviation as InterviewProbe's questions actually write
// it is substituted.
const PRONUNCIATION_PATTERN = new RegExp(
  `\\b(${Object.keys(PRONUNCIATION_MAP)
    .map((term) => term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
    .join('|')})\\b`,
  'g',
)

// Strips Markdown emphasis/heading markers that would otherwise be spoken
// literally (e.g. a TTS engine reading "**RAG**" as "asterisk asterisk RAG
// asterisk asterisk"). Only removes the delimiter characters themselves —
// the emphasized word/phrase inside is always preserved verbatim, so no
// word is ever dropped.
function stripMarkdownDelimiters(text) {
  return (
    text
      // Heading markers at the start of a line: "## Explain X" -> "Explain X".
      .replace(/^ {0,3}#{1,6}\s+/gm, '')
      // Bold+italic, bold, then italic — longest delimiter first so
      // "**foo**" isn't left with a stray "*" by the italic pass.
      .replace(/\*\*\*([^*]+)\*\*\*/g, '$1')
      .replace(/___([^_]+)___/g, '$1')
      .replace(/\*\*([^*]+)\*\*/g, '$1')
      .replace(/__([^_]+)__/g, '$1')
      .replace(/\*([^*]+)\*/g, '$1')
      .replace(/(?<![A-Za-z0-9])_([^_]+)_(?![A-Za-z0-9])/g, '$1')
      // Inline code delimiters: keep the code content, drop the backticks.
      .replace(/`([^`]+)`/g, '$1')
  )
}

// Collapses incidental whitespace (multiple spaces, line breaks used only
// for layout) down to single spaces between sentences. This never changes
// wording or punctuation, only how much silence a TTS engine would
// otherwise insert for whitespace that was never meant to be a pause.
function normalizeWhitespace(text) {
  return text
    .replace(/[ \t]+/g, ' ')
    .replace(/\s*\n\s*/g, ' ')
    .trim()
}

function applyPronunciation(text) {
  return text.replace(PRONUNCIATION_PATTERN, (match) => PRONUNCIATION_MAP[match])
}

// Produces the deterministic spoken representation of `text`. Returns a
// structured result — `text` is the plain-text form to hand to a TTS
// provider's speak(); `ssml` is reserved as an extension point for a future
// provider that accepts SSML and is always null today, since the current
// TTS provider (remoteTtsProvider.js) doesn't consume it — it keeps taking
// plain text exactly as before, only *which* plain text it's given changes.
export function createSpeechPresentation(text) {
  if (!text || !text.trim()) {
    return { text: '', ssml: null }
  }

  let spoken = text
  spoken = stripMarkdownDelimiters(spoken)
  spoken = applyPronunciation(spoken)
  spoken = normalizeWhitespace(spoken)

  return { text: spoken, ssml: null }
}
