// The setup page's own large "application window" surface — the same
// glass-shell recipe the (locked) Landing Page uses, kept as an
// independent copy here rather than importing Landing's version, so
// nothing on this page can ever visually regress Landing and vice versa.
function SetupShell({ children }) {
  return (
    <div className="relative mx-auto w-full max-w-[1600px] overflow-hidden rounded-[32px] border border-glass/70 bg-glass/45 shadow-glass backdrop-blur-2xl sm:rounded-[40px] lg:flex lg:flex-1 lg:flex-col">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -right-24 -top-32 h-96 w-96 rounded-full bg-primary-light/70 blur-3xl"
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -left-32 bottom-0 h-96 w-96 rounded-full bg-tint-purple-light/50 blur-3xl"
      />
      <div className="relative lg:flex lg:flex-1 lg:flex-col">{children}</div>
    </div>
  )
}

export default SetupShell
