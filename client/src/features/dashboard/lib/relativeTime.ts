const MINUTE = 60_000
const HOUR = 60 * MINUTE
const DAY = 24 * HOUR

const dateFormat = new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' })

const plural = (count: number, unit: string) => `${count} ${unit}${count === 1 ? '' : 's'} ago`

/** Deterministic relative time ("2 hours ago", "Yesterday", "Sep 28, 2026"). `now` is injectable for tests. */
export function formatRelativeTime(iso: string | null, now: number = Date.now()): string {
  if (!iso) return '—'
  const time = Date.parse(iso)
  if (Number.isNaN(time)) return '—'

  const diff = now - time
  if (diff < MINUTE) return 'Just now' // also covers small clock skew (future timestamps)
  if (diff < HOUR) return plural(Math.floor(diff / MINUTE), 'minute')
  if (diff < DAY) return plural(Math.floor(diff / HOUR), 'hour')
  const days = Math.floor(diff / DAY)
  if (days === 1) return 'Yesterday'
  if (days < 7) return plural(days, 'day')
  return dateFormat.format(time)
}
