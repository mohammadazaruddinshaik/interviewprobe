function SetupHeader() {
  return (
    <header data-enter="">
      <p className="flex items-center gap-2.5 text-[11px] font-semibold tracking-[0.18em] text-ink/45">
        <span aria-hidden="true" className="h-2 w-2 rounded-[2px] bg-yellow" />
        NEW INTERVIEW
      </p>
      <h1 className="mt-3.5 font-display text-[32px] font-extrabold leading-[1.08] tracking-[-0.025em] text-deep sm:text-[40px] xl:text-[46px]">
        Set up your interview.
        <span className="block text-deep/45">We’ll adapt from there.</span>
      </h1>
      <p className="mt-3.5 max-w-[540px] font-serif text-[16.5px] leading-[1.5] text-ink/70">
        Tell us the role you’re interviewing for, and add a resume if you like. We plan the topics and difficulty for you, then your interviewer follows up and digs deeper as you answer.
      </p>
    </header>
  )
}

export default SetupHeader
