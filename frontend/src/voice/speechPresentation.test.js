import { describe, expect, it } from 'vitest'
import { createSpeechPresentation } from './speechPresentation.js'

describe('createSpeechPresentation — identity / basic input', () => {
  it('returns a plain sentence unchanged', () => {
    expect(createSpeechPresentation('Explain how a hash map works.')).toEqual({
      text: 'Explain how a hash map works.',
      ssml: null,
    })
  })

  it('returns empty text for an empty string', () => {
    expect(createSpeechPresentation('')).toEqual({ text: '', ssml: null })
  })

  it('returns empty text for whitespace-only input', () => {
    expect(createSpeechPresentation('   \n\t  ')).toEqual({ text: '', ssml: null })
  })

  it('handles very short input', () => {
    expect(createSpeechPresentation('Why?')).toEqual({ text: 'Why?', ssml: null })
  })
})

describe('createSpeechPresentation — formatting cleanup', () => {
  it('strips markdown bold delimiters while keeping the emphasized word', () => {
    expect(createSpeechPresentation('Explain **caching** and its advantages.').text).toBe(
      'Explain caching and its advantages.',
    )
  })

  it('strips markdown italic delimiters while keeping the emphasized word', () => {
    expect(createSpeechPresentation('What is *eventual* consistency?').text).toBe(
      'What is eventual consistency?',
    )
  })

  it('strips heading-style markers at the start of a line', () => {
    expect(createSpeechPresentation('## System design\nDesign a rate limiter.').text).toBe(
      'System design Design a rate limiter.',
    )
  })

  it('strips mixed bold+italic and inline code delimiters', () => {
    // REST also goes through the pronunciation map (spoken as the word
    // "rest"), so the delimiters are gone and the known term is rewritten.
    expect(createSpeechPresentation('Explain ***REST*** and the `GET` verb.').text).toBe(
      'Explain rest and the GET verb.',
    )
  })

  it('does not touch underscores inside a snake_case identifier', () => {
    expect(createSpeechPresentation('What does `max_retry_count` control?').text).toBe(
      'What does max_retry_count control?',
    )
  })

  it('preserves punctuation meaning in technical text', () => {
    expect(createSpeechPresentation('What does the expression a[i], b[i] return?').text).toBe(
      'What does the expression a[i], b[i] return?',
    )
  })
})

describe('createSpeechPresentation — technical term pronunciation', () => {
  const cases = [
    ['Explain how an LLM generates text.', 'Explain how an L L M generates text.'],
    ['What is RAG used for?', 'What is R A G used for?'],
    ['Design a REST API for orders.', 'Design a rest A P I for orders.'],
    ['Write a SQL query to find duplicates.', 'Write a sequel query to find duplicates.'],
    ['How would you index a PostgreSQL table?', 'How would you index a Postgres sequel table?'],
    ['When would you choose Redis over Qdrant?', 'When would you choose Redis over Quadrant?'],
    ['Parse this JSON payload.', 'Parse this jay-sawn payload.'],
    ['How does a JWT get validated?', 'How does a J W T get validated?'],
    ['Compare STT and TTS latency.', 'Compare S T T and T T S latency.'],
  ]

  it.each(cases)('rewrites %s deterministically for speech', (input, expected) => {
    expect(createSpeechPresentation(input).text).toBe(expected)
  })

  it('leaves lowercase mentions of an abbreviation untouched', () => {
    expect(createSpeechPresentation('Describe an api you have built.').text).toBe(
      'Describe an api you have built.',
    )
  })

  it('is idempotent for a question with no matching terms', () => {
    const input = 'Describe a time you resolved a difficult merge conflict.'
    expect(createSpeechPresentation(input).text).toBe(input)
  })
})

describe('createSpeechPresentation — semantic preservation', () => {
  it('preserves every meaningful word for a realistic multi-sentence question', () => {
    const input =
      'Explain **RAG** and its advantages over fine-tuning. ' +
      'Then describe how you would design a `REST` API that exposes it, ' +
      'and how a JWT would be used to authenticate callers.'

    const result = createSpeechPresentation(input)

    // A known abbreviation (RAG, JWT) is deliberately spelled out as
    // space-separated letters for pronunciation — collapse those back to
    // the original token before comparing, so the comparison only checks
    // that no *other* word was reordered, dropped, or added.
    const collapsed = result.text
      .replace(/\bR A G\b/g, 'RAG')
      .replace(/\bJ W T\b/g, 'JWT')
      .replace(/\bA P I\b/g, 'API')

    const originalWords = input
      .replace(/[*_`#]/g, '')
      .split(/\s+/)
      .filter(Boolean)
    const rewrittenWords = collapsed.split(/\s+/).filter(Boolean)

    expect(rewrittenWords.length).toBe(originalWords.length)
    originalWords.forEach((word, index) => {
      const rewritten = rewrittenWords[index]
      const isKnownAbbreviation = word.replace(/[.,?]+$/, '') === 'REST'
      if (!isKnownAbbreviation) {
        expect(rewritten).toBe(word)
      }
    })
  })

  it('does not add sentences, filler words, or answer content', () => {
    const input = 'What are the tradeoffs of using a message queue?'
    const result = createSpeechPresentation(input)

    expect(result.text).not.toMatch(/\b(Okay|So|Now|Let's move on)\b/)
    expect(result.text.split(/[.?!]/).filter((s) => s.trim()).length).toBe(
      input.split(/[.?!]/).filter((s) => s.trim()).length,
    )
  })
})

describe('createSpeechPresentation — long question', () => {
  it('keeps a longer technical question semantically identical and speech-safe', () => {
    const input =
      'Suppose you are designing a search service backed by **Qdrant** for vector similarity ' +
      'and PostgreSQL for metadata. Walk through how you would handle a write that must update ' +
      'both stores consistently, what happens if the Qdrant write succeeds but the PostgreSQL ' +
      'write fails, and how you would expose this through a REST API secured with a JWT.'

    const result = createSpeechPresentation(input)

    expect(result.ssml).toBeNull()
    expect(result.text).not.toMatch(/[*_]/)
    // Sentence count (by terminal punctuation) is unchanged — no sentence
    // was split, merged, or summarized away.
    const originalSentences = input.split(/(?<=[.?!])\s+/).length
    const rewrittenSentences = result.text.split(/(?<=[.?!])\s+/).length
    expect(rewrittenSentences).toBe(originalSentences)
  })
})
