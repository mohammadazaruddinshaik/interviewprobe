// Decorative only: an abstract nod to the interviewer's presence and voice. It depicts no interview, question or data.
const BARS = [10, 18, 30, 46, 64, 82, 96, 82, 64, 46, 30, 18, 10]

function PresenceArt({ className = '' }: { className?: string }) {
  return (
    <svg viewBox="0 0 360 320" aria-hidden="true" focusable="false" className={className}>
      <circle cx="190" cy="160" r="150" fill="none" stroke="#060b07" strokeOpacity="0.07" />
      <circle cx="190" cy="160" r="122" fill="none" stroke="#060b07" strokeOpacity="0.1" strokeDasharray="2 7" />
      <path d="M 70 262 A 150 150 0 0 1 112 52" fill="none" stroke="#cc461a" strokeWidth="2.5" strokeLinecap="round" />
      <circle cx="190" cy="160" r="96" fill="#fde45a" />
      <circle cx="190" cy="160" r="96" fill="none" stroke="#060b07" strokeOpacity="0.12" />
      {BARS.map((h, i) => (
        <rect key={i} x={118 + i * 11} y={160 - h / 2} width="5" height={h} rx="2.5" fill="#060b07" fillOpacity="0.88" />
      ))}
      <circle cx="318" cy="64" r="7" fill="#cc461a" />
      <circle cx="44" cy="226" r="4" fill="#060b07" fillOpacity="0.5" />
    </svg>
  )
}

export default PresenceArt
