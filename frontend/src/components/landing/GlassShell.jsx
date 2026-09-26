// The one large "application window" surface the reference design is
// built around: every landing-page section (navbar, hero, feature strip,
// trust section, feature cards) lives inside this single glass shell,
// rather than each being its own independent floating panel.
//
// `overflow-hidden` is load-bearing: the soft decorative blobs children
// render (radial gradients) must be clipped to the shell's own rounded
// corners rather than bleeding past them.
function GlassShell({ children }) {
  return (
    <div className="relative mx-auto max-w-[1600px] overflow-hidden rounded-[32px] border border-white/70 bg-white/45 shadow-glass backdrop-blur-2xl sm:rounded-[40px]">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -right-24 -top-32 h-96 w-96 rounded-full bg-primary-light/70 blur-3xl"
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -left-32 top-1/2 h-96 w-96 -translate-y-1/2 rounded-full bg-tint-purple-light/50 blur-3xl"
      />
      <div className="relative">{children}</div>
    </div>
  )
}

export default GlassShell
