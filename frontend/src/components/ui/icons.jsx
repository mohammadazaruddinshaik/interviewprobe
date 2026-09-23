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

export function BrandMark({ className }) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true">
      <rect x="3" y="12" width="4" height="9" rx="1" fill="currentColor" />
      <rect x="10" y="7" width="4" height="14" rx="1" fill="currentColor" opacity="0.85" />
      <rect x="17" y="3" width="4" height="18" rx="1" fill="currentColor" opacity="0.7" />
    </svg>
  )
}

export function ArrowRightIcon({ className }) {
  return (
    <svg {...base({ className })}>
      <path d="M5 12h14" />
      <path d="M13 6l6 6-6 6" />
    </svg>
  )
}

export function PlayIcon({ className }) {
  return (
    <svg {...base({ className, fill: 'currentColor', stroke: 'none' })}>
      <path d="M8 5.5v13l11-6.5-11-6.5z" />
    </svg>
  )
}

export function MenuIcon({ className }) {
  return (
    <svg {...base({ className })}>
      <path d="M4 7h16" />
      <path d="M4 12h16" />
      <path d="M4 17h16" />
    </svg>
  )
}

export function CloseIcon({ className }) {
  return (
    <svg {...base({ className })}>
      <path d="M6 6l12 12" />
      <path d="M18 6L6 18" />
    </svg>
  )
}

export function ChatIcon({ className }) {
  return (
    <svg {...base({ className })}>
      <path d="M21 12a8 8 0 1 1-3.2-6.4L21 4l-1.2 3.6A8 8 0 0 1 21 12z" />
    </svg>
  )
}

export function ChartIcon({ className }) {
  return (
    <svg {...base({ className })}>
      <path d="M4 20V10" />
      <path d="M12 20V4" />
      <path d="M20 20v-7" />
    </svg>
  )
}

export function BookIcon({ className }) {
  return (
    <svg {...base({ className })}>
      <path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v15H6.5A2.5 2.5 0 0 0 4 20.5v-15z" />
      <path d="M4 20.5A2.5 2.5 0 0 1 6.5 18H20" />
    </svg>
  )
}

export function UsersIcon({ className }) {
  return (
    <svg {...base({ className })}>
      <circle cx="9" cy="8" r="3" />
      <path d="M2.5 20a6.5 6.5 0 0 1 13 0" />
      <path d="M16 8.5a3 3 0 1 1 3.5 2.96" />
      <path d="M15.5 14.5c2.9.3 5 1.9 5.5 4.5" />
    </svg>
  )
}

export function SparkIcon({ className }) {
  return (
    <svg {...base({ className })}>
      <path d="M12 3v4" />
      <path d="M12 17v4" />
      <path d="M3 12h4" />
      <path d="M17 12h4" />
      <path d="M6 6l2.5 2.5" />
      <path d="M15.5 15.5L18 18" />
      <path d="M18 6l-2.5 2.5" />
      <path d="M8.5 15.5L6 18" />
    </svg>
  )
}

export function ServerIcon({ className }) {
  return (
    <svg {...base({ className })}>
      <rect x="3" y="4" width="18" height="7" rx="1.5" />
      <rect x="3" y="13" width="18" height="7" rx="1.5" />
      <path d="M7 7.5h.01" />
      <path d="M7 16.5h.01" />
    </svg>
  )
}

export function LayoutIcon({ className }) {
  return (
    <svg {...base({ className })}>
      <rect x="3" y="4" width="18" height="16" rx="1.5" />
      <path d="M3 9h18" />
      <path d="M9 9v11" />
    </svg>
  )
}

export function CoffeeIcon({ className }) {
  return (
    <svg {...base({ className })}>
      <path d="M4 8h13v6a5 5 0 0 1-5 5H9a5 5 0 0 1-5-5V8z" />
      <path d="M17 9h1.5a2.5 2.5 0 0 1 0 5H17" />
      <path d="M8 3.5c-.5.7-.5 1.3 0 2" />
      <path d="M12 3.5c-.5.7-.5 1.3 0 2" />
    </svg>
  )
}

export function CheckIcon({ className }) {
  return (
    <svg {...base({ className })}>
      <path d="M5 12.5l4.5 4.5L19 7" />
    </svg>
  )
}

export function CodeIcon({ className }) {
  return (
    <svg {...base({ className })}>
      <path d="M9 6.5L3.5 12 9 17.5" />
      <path d="M15 6.5l5.5 5.5-5.5 5.5" />
    </svg>
  )
}

export function TargetIcon({ className }) {
  return (
    <svg {...base({ className })}>
      <circle cx="12" cy="12" r="8" />
      <circle cx="12" cy="12" r="4" />
      <circle cx="12" cy="12" r="0.6" fill="currentColor" />
    </svg>
  )
}

export function ArrowLeftIcon({ className }) {
  return (
    <svg {...base({ className })}>
      <path d="M19 12H5" />
      <path d="M11 6l-6 6 6 6" />
    </svg>
  )
}

export function MinusIcon({ className }) {
  return (
    <svg {...base({ className })}>
      <path d="M5 12h14" />
    </svg>
  )
}

export function PlusIcon({ className }) {
  return (
    <svg {...base({ className })}>
      <path d="M12 5v14" />
      <path d="M5 12h14" />
    </svg>
  )
}

export function ChevronDownIcon({ className }) {
  return (
    <svg {...base({ className })}>
      <path d="M6 9l6 6 6-6" />
    </svg>
  )
}

export function MicIcon({ className }) {
  return (
    <svg {...base({ className })}>
      <rect x="9" y="3" width="6" height="11" rx="3" />
      <path d="M5 11a7 7 0 0 0 14 0" />
      <path d="M12 18v3" />
      <path d="M8.5 21h7" />
    </svg>
  )
}

export function SpeakerIcon({ className }) {
  return (
    <svg {...base({ className })}>
      <path d="M4 9.5v5h4l5 4v-13l-5 4H4z" />
      <path d="M16.5 9a4.5 4.5 0 0 1 0 6" />
      <path d="M19 6.5a8.5 8.5 0 0 1 0 11" />
    </svg>
  )
}

export function StopIcon({ className }) {
  return (
    <svg {...base({ className, fill: 'currentColor', stroke: 'none' })}>
      <rect x="6" y="6" width="12" height="12" rx="2" />
    </svg>
  )
}
