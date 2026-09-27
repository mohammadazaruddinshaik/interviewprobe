import { CoffeeIcon, LayoutIcon, ServerIcon } from './icons.jsx'

// InterviewProbe's own icon family — used for every feature/concept/role
// glyph across the Landing and Setup pages, instead of generic Lucide
// icons. Shares one visual grammar: 24x24 viewBox, rounded stroke
// (1.75-2), rounded caps/joins, compact geometric construction, no
// gradients/3D/emoji. Lucide is still used elsewhere for plain utility
// controls (menu, close, arrows, mic/camera toggle buttons, theme, etc.)
// — this file is only for the identity-carrying concept/role icons.
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

// 1. AI Interview / AI Engineer — a rounded chip housing a small neural
// triad, standing in for "an intelligent interviewer" without a literal
// brain or robot illustration.
export function NeuralChipIcon({ className }) {
  return (
    <svg {...base({ className })}>
      <rect x="4" y="4" width="16" height="16" rx="5" />
      <path d="M9.7 10.2l1.7 3.6M14.3 10.2l-1.7 3.6M10.2 9.3h3.6" />
      <circle cx="9" cy="9.3" r="1.3" fill="currentColor" stroke="none" />
      <circle cx="15" cy="9.3" r="1.3" fill="currentColor" stroke="none" />
      <circle cx="12" cy="15.3" r="1.3" fill="currentColor" stroke="none" />
    </svg>
  )
}

// 2. Adaptive Interview — a conversation bubble with a forked path inside,
// standing in for the interviewer branching into a follow-up, a deeper
// question, or a new topic based on the candidate's answer.
export function AdaptiveIcon({ className }) {
  return (
    <svg {...base({ className })}>
      <path d="M4 7.5A3.5 3.5 0 0 1 7.5 4h9A3.5 3.5 0 0 1 20 7.5v6A3.5 3.5 0 0 1 16.5 17H10l-4 3.5V17h-.5A3.5 3.5 0 0 1 4 13.5v-6z" />
      <path d="M9.5 11h1.8" />
      <path d="M11.3 11l2.6-2.3" />
      <path d="M11.3 11l2.6 2.3" />
    </svg>
  )
}

// 5. Role-specific Interview — an identity badge with a compact figure,
// standing in for "tailored to your role" without a generic briefcase.
export function RoleBadgeIcon({ className }) {
  return (
    <svg {...base({ className })}>
      <rect x="5" y="3" width="14" height="18" rx="4.5" />
      <circle cx="12" cy="9.3" r="2.3" />
      <path d="M7.8 16.2c0-2.3 1.9-3.7 4.2-3.7s4.2 1.4 4.2 3.7" />
    </svg>
  )
}

// 7. Question / Deep Dive — a target with an arrow drilling through its
// center, standing in for probing deeper into a specific topic.
export function DeepDiveIcon({ className }) {
  return (
    <svg {...base({ className })}>
      <circle cx="12" cy="10" r="7" />
      <circle cx="12" cy="10" r="3.1" />
      <path d="M12 17.5v4" />
      <path d="M9.6 19.6L12 21.5l2.4-1.9" />
    </svg>
  )
}

// 9. Real Interview Simulation — two overlapping video tiles (interviewer +
// candidate) with a small live-pulse dot, standing in for a real video-call
// style session rather than a static form.
export function SimulationIcon({ className }) {
  return (
    <svg {...base({ className })}>
      <rect x="3" y="5.5" width="12" height="10" rx="2.5" />
      <rect x="11.5" y="9.5" width="9" height="9" rx="2.5" fill="none" />
      <circle cx="18" cy="9.2" r="1.3" fill="currentColor" stroke="none" />
    </svg>
  )
}

// 4. Evaluation / Feedback — a report card with an ascending checkpoint
// line, standing in for structured, scored feedback rather than a plain
// bar chart.
export function EvaluationIcon({ className }) {
  return (
    <svg {...base({ className })}>
      <rect x="4" y="4" width="16" height="16" rx="3.5" />
      <path d="M7.5 14.5l2.6-3 2 2 4.4-5" />
      <circle cx="16.5" cy="8.5" r="1.3" fill="currentColor" stroke="none" />
    </svg>
  )
}

// Frontend Developer — a browser/app frame with a small filled cursor,
// standing in for building and interacting with interfaces.
export function InterfaceIcon({ className }) {
  return (
    <svg {...base({ className })}>
      <rect x="3.5" y="4.5" width="17" height="15" rx="3" />
      <path d="M3.5 9h17" />
      <path d="M13 12.7l4.3 1.8-1.9.7-.7 1.9z" fill="currentColor" stroke="none" />
    </svg>
  )
}

// SDE / Software Development Engineer — a hexagonal frame (systems /
// engineering) with a compact code mark inside, standing in for
// general-purpose software engineering rather than a literal gear.
export function EngineeringIcon({ className }) {
  return (
    <svg {...base({ className })}>
      <path d="M12 3.5l6.9 4v9l-6.9 4-6.9-4v-9z" />
      <path d="M10.3 9.5L8 12l2.3 2.5" />
      <path d="M13.7 9.5L16 12l-2.3 2.5" />
    </svg>
  )
}

// 3. Voice Interview — a mic capsule with sound waves on one side only
// (never both, symmetrically) — a deliberately asymmetric mark so it
// reads as distinctly InterviewProbe's rather than a stock mic glyph.
export function VoiceInterviewIcon({ className }) {
  return (
    <svg {...base({ className })}>
      <rect x="7" y="3.5" width="6" height="9.5" rx="3" />
      <path d="M5 10.5a5 5 0 0 0 5 5" />
      <path d="M10 18v2.5" />
      <path d="M15 8a3.2 3.2 0 0 1 0 5" />
      <path d="M17.8 6.3a6 6 0 0 1 0 8.4" />
    </svg>
  )
}

// 10. Technical Interview — a terminal window with a command prompt
// caret, standing in for hands-on technical practice rather than plain
// angle brackets.
export function TechnicalInterviewIcon({ className }) {
  return (
    <svg {...base({ className })}>
      <rect x="3" y="5" width="18" height="14" rx="2.5" />
      <path d="M7 10l3 2-3 2" />
      <path d="M13 14.3h4" />
    </svg>
  )
}

// 8. Learning / Improvement — a rising path with a milestone marker at
// its end, standing in for measurable progress rather than a static book.
export function LearningIcon({ className }) {
  return (
    <svg {...base({ className })}>
      <path d="M4 17.5l4.3-4.3 3 3L18 9.5" />
      <path d="M13.8 9.5h4.2v4.2" />
    </svg>
  )
}

// 6. Interview Analytics — a gauge/dial with a needle, standing in for a
// multi-metric read-out rather than a plain bar chart.
export function AnalyticsIcon({ className }) {
  return (
    <svg {...base({ className })}>
      <path d="M4.5 16a7.5 7.5 0 1 1 15 0" />
      <path d="M12 16l3.2-3.6" />
      <circle cx="12" cy="16" r="1.3" fill="currentColor" stroke="none" />
    </svg>
  )
}

// Role tile icons that reuse an existing custom glyph under a
// role-semantic name (Backend's stacked-system bars, Java's cup mark, and
// Full Stack's layered panel already fit their role one-to-one).
export const BackendRoleIcon = ServerIcon
export const JavaRoleIcon = CoffeeIcon
export const FullStackRoleIcon = LayoutIcon
