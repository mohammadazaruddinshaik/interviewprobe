// Viewport-tall minus the wrapper's own vertical padding at each
// breakpoint (py-2.5 / sm:py-3 / lg:py-4), so a short phase never scrolls.
const MIN_HEIGHT = 'min-h-[calc(100svh-1.25rem)] sm:min-h-[calc(100svh-1.5rem)]'

// The interview room's own "application window" — the same glass-shell
// recipe Landing and Setup already use, kept as an independent copy so
// none of these three pages can ever visually regress one another. Reused
// across every phase (loading/error/completed/ready) so the whole route
// reads as one consistent, premium environment.
//
// `fit` is the live room: from `lg` up the shell is exactly one viewport
// tall and its children lay themselves out inside that height (the room
// is a single screen, like a video call, not a scrolling page). Below
// `lg`, and for every other phase, the shell simply grows with content.
// The decorative glows sit in their own clipped layer so the shell itself
// never needs `overflow-hidden` — nothing real can ever be clipped.
function InterviewShell({ children, fit = false }) {
  const minHeight = fit ? `${MIN_HEIGHT} lg:h-full lg:min-h-0` : `${MIN_HEIGHT} lg:min-h-[calc(100svh-2rem)]`

  return (
    <div className={`relative overflow-x-hidden text-ink ${fit ? 'lg:h-dvh lg:min-h-[640px]' : ''}`}>
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -left-16 -top-16 h-64 w-64 rounded-full bg-primary-light/50 opacity-70 blur-3xl sm:-left-24 sm:-top-24 sm:h-96 sm:w-96"
      />
      <div className={`relative px-3 py-2.5 sm:px-5 sm:py-3 lg:px-6 lg:py-4 ${fit ? 'lg:h-full' : ''}`}>
        <div
          className={`relative mx-auto max-w-[1600px] rounded-[32px] border border-glass/70 bg-glass/45 shadow-glass backdrop-blur-2xl sm:rounded-[40px] flex flex-col ${minHeight}`}
        >
          <div aria-hidden="true" className="pointer-events-none absolute inset-0 overflow-hidden rounded-[inherit]">
            <div className="absolute -right-24 -top-32 h-96 w-96 rounded-full bg-primary-light/70 blur-3xl" />
            <div className="absolute -left-32 bottom-0 h-96 w-96 rounded-full bg-tint-purple-light/50 blur-3xl" />
          </div>
          <div className={`relative flex flex-1 flex-col ${fit ? 'lg:min-h-0' : ''}`}>
            {children}
          </div>
        </div>
      </div>
    </div>
  )
}

export default InterviewShell
