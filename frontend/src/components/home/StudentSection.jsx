function StudentSection() {
  return (
    <section className="relative overflow-hidden border-t border-line/70 bg-gradient-to-br from-accent-softer via-cream to-cream">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -left-32 top-1/2 h-96 w-96 -translate-y-1/2 rounded-full bg-accent-soft/60 blur-3xl"
      />

      <div className="relative mx-auto grid max-w-7xl gap-10 px-6 py-24 lg:grid-cols-[1.2fr_1fr] lg:items-center lg:gap-16">
        <h2 className="text-4xl font-semibold leading-tight tracking-tight text-ink sm:text-5xl">
          Your first real interview shouldn&apos;t be{' '}
          <span className="text-accent">your first practice.</span>
        </h2>

        <p className="max-w-md text-lg leading-relaxed text-muted lg:justify-self-end">
          Practice explaining what you know, reasoning through unfamiliar problems, and
          communicating technical decisions before the real interview.
        </p>
      </div>
    </section>
  )
}

export default StudentSection
