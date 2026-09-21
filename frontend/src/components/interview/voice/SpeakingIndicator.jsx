// Always renders some status (never pops in/out, so the layout never
// shifts) and never relies on the dot's color/motion alone — the text label
// carries the actual information; the dot is a redundant visual reinforcement.
function SpeakingIndicator({ active }) {
  return (
    <p
      role="status"
      aria-live="polite"
      className={`inline-flex items-center gap-1.5 text-xs font-medium ${active ? 'text-accent' : 'text-muted'}`}
    >
      <span
        aria-hidden="true"
        className={`h-1.5 w-1.5 rounded-full ${active ? 'bg-accent motion-safe:animate-pulse' : 'bg-line'}`}
      />
      {active ? 'Interviewer speaking' : 'Interviewer idle'}
    </p>
  )
}

export default SpeakingIndicator
