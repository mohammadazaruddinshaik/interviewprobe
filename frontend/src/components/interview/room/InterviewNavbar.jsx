import { useEffect, useState } from 'react'

// Contextual section labels only — "Interview" is the only one with a
// real destination (this page itself). Progress/Feedback/Resources have
// no real pages anywhere in the app (see App.jsx's router), so they're
// rendered as inert, muted labels rather than becoming fake routes or
// dead links.
const CONTEXT_LABELS = ['Progress', 'Feedback', 'Resources']

function formatElapsed(totalSeconds) {
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${minutes}:${seconds.toString().padStart(2, '0')}`
}

// A real, running clock — time actually elapsed since this room mounted,
// not a fetched or fabricated duration (the API doesn't expose a session
// start time). Resets on reload, same honest scope as `transcript` in
// Interview.jsx.
function useElapsedSeconds() {
  const [seconds, setSeconds] = useState(0)

  useEffect(() => {
    const startedAt = Date.now()
    const id = setInterval(() => setSeconds(Math.floor((Date.now() - startedAt) / 1000)), 1000)
    return () => clearInterval(id)
  }, [])

  return seconds
}

function InterviewNavbar() {
  const elapsedSeconds = useElapsedSeconds()

  return (
    <header className="px-4 pt-3 sm:px-6 lg:px-8">
      <div className="flex h-12 items-center justify-between gap-3">
        <a href="/" className="flex shrink-0 items-center">
          <img src="/assets/brand/logo.svg" alt="InterviewProbe" className="h-6 w-auto sm:h-7" />
        </a>

        <nav
          aria-label="Interview sections"
          className="hidden items-center gap-1 rounded-full border border-line bg-glass/50 p-1 md:flex"
        >
          <span className="rounded-full bg-glass px-3.5 py-1.5 text-sm font-medium text-primary shadow-glass-sm">
            Interview
          </span>
          {CONTEXT_LABELS.map((label) => (
            <span key={label} aria-disabled="true" className="cursor-default px-3.5 py-1.5 text-sm text-muted/70">
              {label}
            </span>
          ))}
        </nav>

        <div className="flex shrink-0 items-center gap-2">
          <span
            className="hidden items-center gap-1.5 whitespace-nowrap rounded-full border border-line bg-glass/60 px-3 py-1.5 text-xs font-medium text-muted sm:flex"
            aria-label="Time elapsed"
          >
            {formatElapsed(elapsedSeconds)}
          </span>
          <a
            href="/"
            className="whitespace-nowrap rounded-full bg-danger px-3.5 py-1.5 text-sm font-medium text-white transition-colors duration-200 hover:bg-danger/90"
          >
            End Interview
          </a>
        </div>
      </div>
    </header>
  )
}

export default InterviewNavbar
