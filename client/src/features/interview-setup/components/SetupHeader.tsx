function SetupHeader() {
  return (
    <header data-setup="header">
      <a
        href="/app"
        className="group -ml-1 inline-flex items-center gap-2 rounded-lg px-1 py-1.5 text-[13.5px] font-semibold text-forest outline-offset-2 focus-visible:outline-[3px] focus-visible:outline-yellow"
      >
        <span aria-hidden="true" className="transition-transform duration-200 group-hover:-translate-x-[3px] motion-reduce:transition-none">
          ←
        </span>
        Back to dashboard
      </a>
      <p className="mt-[18px] flex items-center gap-2.5 text-[11px] font-semibold tracking-[0.18em] text-ink/45">
        <span aria-hidden="true" className="h-2 w-2 rounded-[2px] bg-yellow" />
        NEW INTERVIEW
      </p>
      <h1 className="mt-3.5 font-display text-[32px] font-extrabold leading-[1.08] tracking-[-0.025em] text-deep sm:text-[40px] xl:text-[46px]">
        Set up your interview.
        <span className="block text-deep/45">We’ll adapt from there.</span>
      </h1>
      <p className="mt-3.5 max-w-[540px] font-serif text-[16.5px] leading-[1.5] text-ink/70">
        Choose the role, difficulty and focus. As you answer, your interviewer follows up and digs deeper where it matters.
      </p>
    </header>
  )
}

export default SetupHeader
