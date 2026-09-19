function ScoreHero({ overallScore, roleLabel, difficultyLabel, questionCount }) {
  return (
    <section className="motion-safe:animate-rise mx-auto max-w-3xl px-6 pb-4 pt-14 text-center sm:px-8">
      <h1 className="text-3xl font-semibold leading-snug text-ink sm:text-4xl">
        Interview complete.
        <br />
        Here&apos;s how you performed.
      </h1>

      <p className="mt-8 flex items-baseline justify-center gap-1.5">
        <span className="text-6xl font-semibold tracking-tight text-ink">{overallScore.toFixed(1)}</span>
        <span className="text-xl font-medium text-muted">/ 10</span>
      </p>

      <p className="mt-4 text-sm text-muted">
        {[roleLabel, difficultyLabel, questionCount != null ? `${questionCount} questions` : null]
          .filter(Boolean)
          .join(' · ')}
      </p>
    </section>
  )
}

export default ScoreHero
