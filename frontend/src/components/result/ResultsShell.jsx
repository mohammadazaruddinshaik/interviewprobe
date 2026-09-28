// The Results page's own large "application window" surface — the same
// glass-shell recipe Landing, Setup, and Interview each use, kept as an
// independent copy so none of these pages can ever visually regress one
// another. Unlike the Interview room, this page has substantial content
// (score breakdown, feedback, question-by-question review), so the shell
// simply grows with its content — normal document scrolling is expected
// here, never forced into a single viewport.
function ResultsShell({ children }) {
  return (
    <div className="relative mx-auto max-w-[1600px] overflow-hidden rounded-[32px] border border-glass/70 bg-glass/45 shadow-glass backdrop-blur-2xl sm:rounded-[40px]">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -right-24 -top-32 h-96 w-96 rounded-full bg-primary-light/70 blur-3xl"
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -left-32 top-[40%] h-96 w-96 -translate-y-1/2 rounded-full bg-tint-purple-light/50 blur-3xl"
      />
      <div className="relative">{children}</div>
    </div>
  )
}

export default ResultsShell
