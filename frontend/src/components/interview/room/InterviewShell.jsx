// The interview room's own "application window" — the same glass-shell
// recipe Landing and Setup already use, kept as an independent copy so
// none of these three pages can ever visually regress one another. Reused
// across every phase (loading/error/completed/ready) so the whole route
// reads as one consistent, premium environment rather than the room
// looking different from its own loading/error states.
function InterviewShell({ children }) {
  return (
    <div className="relative overflow-x-hidden text-ink">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -left-16 -top-16 h-64 w-64 rounded-full bg-primary-light/50 opacity-70 blur-3xl sm:-left-24 sm:-top-24 sm:h-96 sm:w-96"
      />
      <div className="relative px-3 py-2.5 sm:px-5 sm:py-3 lg:px-6 lg:py-4">
        <div className="relative mx-auto min-h-[calc(100svh-1.5rem)] max-w-[1600px] overflow-hidden rounded-[32px] border border-glass/70 bg-glass/45 shadow-glass backdrop-blur-2xl sm:rounded-[40px]">
          <div
            aria-hidden="true"
            className="pointer-events-none absolute -right-24 -top-32 h-96 w-96 rounded-full bg-primary-light/70 blur-3xl"
          />
          <div
            aria-hidden="true"
            className="pointer-events-none absolute -left-32 bottom-0 h-96 w-96 rounded-full bg-tint-purple-light/50 blur-3xl"
          />
          <div className="relative flex min-h-[calc(100svh-1.5rem)] flex-col">{children}</div>
        </div>
      </div>
    </div>
  )
}

export default InterviewShell
