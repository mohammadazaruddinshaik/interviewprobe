/** Calm cover shown when the candidate steps away. It hides the room but never changes what is behind it. */
function InterviewPausedOverlay({ onReturn }: { onReturn: () => void }) {
  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="paused-title"
      aria-describedby="paused-desc"
      className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-[#06110a]/95 px-6 text-center backdrop-blur-md"
    >
      <span aria-hidden="true" className="size-14 rounded-full bg-[radial-gradient(circle_at_34%_28%,#c9cdb8_0%,#6d7a62_45%,#2c3a26_100%)] opacity-80" />
      <h2 id="paused-title" className="mt-8 font-display text-[28px] font-extrabold tracking-[-0.02em] text-cream sm:text-[34px]">
        Interview paused
      </h2>
      <p id="paused-desc" className="mt-3 max-w-[360px] font-serif text-[17px] leading-[1.5] text-cream/65">
        Please return to the interview to continue.
      </p>
      <button
        type="button"
        autoFocus
        onClick={onReturn}
        className="mt-9 inline-flex h-[54px] items-center justify-center rounded-2xl bg-yellow px-9 text-[16px] font-semibold text-forest outline-offset-4 transition-transform duration-200 hover:-translate-y-0.5 focus-visible:outline-[3px] focus-visible:outline-cream motion-reduce:transition-none motion-reduce:hover:translate-y-0"
      >
        Return to interview
      </button>
    </div>
  )
}

export default InterviewPausedOverlay
