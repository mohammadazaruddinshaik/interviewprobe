// InterviewProbe's own icon family — the glyphs that carry product
// meaning (AI interviewer, voice, adaptive questioning, evaluation, roles,
// questions, results). Lucide stays for plain utility controls only
// (menu, close, arrows, chevrons, theme, playback).
//
// One grammar, applied to every glyph:
// - 24×24 grid, content kept inside a 3–21 live area
// - 1.75 stroke, round caps and joins, no fills except the signal dot
// - containers are rounded rects (rx 4–5) or circles, never sharp boxes
// - the "signal dot": one small filled circle (r 1.3) marking the active
//   or intelligent part of the concept, so the family reads as related
// - no gradients, no emoji, no sparkles
function base(props) {
  return {
    xmlns: 'http://www.w3.org/2000/svg',
    viewBox: '0 0 24 24',
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: 1.75,
    strokeLinecap: 'round',
    strokeLinejoin: 'round',
    'aria-hidden': true,
    ...props,
  }
}

function Dot({ cx, cy }) {
  return <circle cx={cx} cy={cy} r="1.3" fill="currentColor" stroke="none" />
}

// The interviewer — InterviewProbe's primary mark for "AI interviewer".
// A person (head + shoulders) with two speech-signal arcs: someone asking
// you a question out loud. Deliberately not a chip, robot, brain, or
// sparkle: the product is an interview, and the AI shows up as an
// interviewer who speaks, not as a piece of hardware.
export function InterviewerIcon({ className }) {
  return (
    <svg {...base({ className })}>
      <circle cx="9" cy="8" r="3.25" />
      <path d="M3.5 19.5c.7-3.3 2.8-5.25 5.5-5.25s4.8 1.95 5.5 5.25" />
      <path d="M16 6.2a3.6 3.6 0 0 1 0 5.6" />
      <path d="M18.6 4a7 7 0 0 1 0 10" />
    </svg>
  )
}

// Adaptive questioning — a conversation bubble whose path forks inside:
// the interviewer branching based on the answer.
export function AdaptiveIcon({ className }) {
  return (
    <svg {...base({ className })}>
      <path d="M4 8a4 4 0 0 1 4-4h8a4 4 0 0 1 4 4v5a4 4 0 0 1-4 4h-5.5L6 20.5V17a2 2 0 0 1-2-2z" />
      <path d="M8.5 10.5h2.8l2.7-2.2M11.3 10.5l2.7 2.2" />
      <Dot cx="15.4" cy="8" />
    </svg>
  )
}

// Voice — a conversation bubble carrying a waveform: speaking with the
// interviewer, not just "a microphone".
export function VoiceInterviewIcon({ className }) {
  return (
    <svg {...base({ className })}>
      <path d="M4 8a4 4 0 0 1 4-4h8a4 4 0 0 1 4 4v5a4 4 0 0 1-4 4h-5.5L6 20.5V17a2 2 0 0 1-2-2z" />
      <path d="M8.5 9.3v2.4M10.8 7.9v5.2M13.1 9v3M15.4 10v1" />
    </svg>
  )
}

// Role — an identity badge with a person above a small code mark: the
// candidate in a technical context.
export function RoleBadgeIcon({ className }) {
  return (
    <svg {...base({ className })}>
      <rect x="5" y="3" width="14" height="18" rx="4.5" />
      <circle cx="12" cy="8.8" r="2.2" />
      <path d="M8.2 15.3c.9-1.6 2.2-2.4 3.8-2.4s2.9.8 3.8 2.4" />
      <path d="M10.4 18l-.9-.6.9-.6M13.6 16.8l.9.6-.9.6" />
    </svg>
  )
}

// Multiple roles — two offset badges: one product, many role tracks.
export function RolesIcon({ className }) {
  return (
    <svg {...base({ className })}>
      <rect x="3.5" y="6" width="11" height="14" rx="3.5" />
      <path d="M9 3.5h7.5A3.5 3.5 0 0 1 20 7v9.5" />
      <circle cx="9" cy="11" r="1.9" />
      <path d="M6.2 16.6c.6-1.2 1.6-1.8 2.8-1.8s2.2.6 2.8 1.8" />
    </svg>
  )
}

// Question — a conversation bubble with a question mark.
export function QuestionIcon({ className }) {
  return (
    <svg {...base({ className })}>
      <path d="M4 8a4 4 0 0 1 4-4h8a4 4 0 0 1 4 4v5a4 4 0 0 1-4 4h-5.5L6 20.5V17a2 2 0 0 1-2-2z" />
      <path d="M10 8.7a2 2 0 1 1 2.6 1.9c-.4.1-.6.5-.6.9v.2" />
      <Dot cx="12" cy="14" />
    </svg>
  )
}

// Real interview simulation — two overlapping video tiles (interviewer +
// candidate) with a live dot.
export function SimulationIcon({ className }) {
  return (
    <svg {...base({ className })}>
      <rect x="3" y="5.5" width="12" height="10" rx="3" />
      <rect x="11.5" y="9.5" width="9" height="9" rx="3" />
      <Dot cx="18" cy="6.5" />
    </svg>
  )
}

// Evaluation / feedback — a report card with an ascending checkpoint line.
export function EvaluationIcon({ className }) {
  return (
    <svg {...base({ className })}>
      <rect x="4" y="4" width="16" height="16" rx="4" />
      <path d="M7.5 14.5l2.6-3 2 2 4-4.5" />
      <Dot cx="16.5" cy="8.5" />
    </svg>
  )
}

// Results — a score ring with its signal dot at the arc's end: a single,
// measured outcome.
export function ResultsIcon({ className }) {
  return (
    <svg {...base({ className })}>
      <path d="M12 3.5a8.5 8.5 0 1 1-7.4 4.3" />
      <path d="M9 12.2l2 2 4-4.4" />
      <Dot cx="4.6" cy="7.8" />
    </svg>
  )
}

// Interview analytics — a gauge with a needle: a multi-metric read-out.
export function AnalyticsIcon({ className }) {
  return (
    <svg {...base({ className })}>
      <path d="M4.5 16a7.5 7.5 0 1 1 15 0" />
      <path d="M12 16l3.2-3.6" />
      <Dot cx="12" cy="16" />
    </svg>
  )
}

// Learning / improvement — a rising path with a milestone at its end.
export function LearningIcon({ className }) {
  return (
    <svg {...base({ className })}>
      <path d="M4 17.5l4.3-4.3 3 3L18 9.5" />
      <path d="M13.8 9.5H18v4.2" />
    </svg>
  )
}

// AI engineer (role) — three connected model nodes: the role's subject
// matter (building AI systems), not the product's own AI identity.
export function AIEngineerRoleIcon({ className }) {
  return (
    <svg {...base({ className })}>
      <circle cx="6.5" cy="7" r="2.5" />
      <circle cx="17.5" cy="7" r="2.5" />
      <circle cx="12" cy="17" r="2.5" />
      <path d="M9 7h6M7.8 9.2l3 5.6M16.2 9.2l-3 5.6" />
    </svg>
  )
}

// Frontend developer — an app frame with a cursor.
export function InterfaceIcon({ className }) {
  return (
    <svg {...base({ className })}>
      <rect x="3.5" y="4.5" width="17" height="15" rx="4" />
      <path d="M3.5 9h17" />
      <path d="M13 12.7l4.3 1.8-1.9.7-.7 1.9z" fill="currentColor" stroke="none" />
    </svg>
  )
}

// Software engineering — a hexagonal system frame with a code mark.
export function EngineeringIcon({ className }) {
  return (
    <svg {...base({ className })}>
      <path d="M12 3.5l6.9 4v9l-6.9 4-6.9-4v-9z" />
      <path d="M10.3 9.5L8 12l2.3 2.5" />
      <path d="M13.7 9.5L16 12l-2.3 2.5" />
    </svg>
  )
}

// Backend developer — two stacked service units with status dots.
export function BackendRoleIcon({ className }) {
  return (
    <svg {...base({ className })}>
      <rect x="3.5" y="4" width="17" height="7" rx="3" />
      <rect x="3.5" y="13" width="17" height="7" rx="3" />
      <Dot cx="7.5" cy="7.5" />
      <Dot cx="7.5" cy="16.5" />
      <path d="M11.5 7.5h5M11.5 16.5h5" />
    </svg>
  )
}

// Java developer — a cup with rising steam.
export function JavaRoleIcon({ className }) {
  return (
    <svg {...base({ className })}>
      <path d="M4.5 9h12v4.5a5 5 0 0 1-5 5h-2a5 5 0 0 1-5-5z" />
      <path d="M16.5 10h1.2a2.3 2.3 0 0 1 0 4.6h-1.4" />
      <path d="M8.5 3.8c-.5.7-.5 1.4 0 2.1M12.5 3.8c-.5.7-.5 1.4 0 2.1" />
    </svg>
  )
}

// Full stack developer — a layered panel: interface over services.
export function FullStackRoleIcon({ className }) {
  return (
    <svg {...base({ className })}>
      <rect x="3.5" y="4" width="17" height="16" rx="4" />
      <path d="M3.5 9.5h17M9.5 9.5V20" />
      <Dot cx="7" cy="6.8" />
    </svg>
  )
}
