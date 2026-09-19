function QuestionPanel({ questionNumber, text, headingRef }) {
  return (
    <section className="motion-safe:animate-rise mx-auto max-w-3xl px-6 pb-4 pt-14 text-center sm:px-8">
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-muted">
        Question {questionNumber}
      </p>
      <h1
        ref={headingRef}
        tabIndex={-1}
        className="mt-4 rounded-lg text-2xl font-semibold leading-snug text-ink focus:outline focus:outline-2 focus:outline-accent focus:outline-offset-4 sm:text-3xl"
      >
        {text}
      </h1>
    </section>
  )
}

export default QuestionPanel
