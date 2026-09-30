/** "38 min", "1 hr 12 min", "2 hr" from completed_at - started_at; null when the timestamps are unusable. */
export function formatDuration(startedAt: string | null, completedAt: string | null): string | null {
  if (!startedAt || !completedAt) return null
  const start = Date.parse(startedAt)
  const end = Date.parse(completedAt)
  if (Number.isNaN(start) || Number.isNaN(end) || end < start) return null
  const minutes = Math.round((end - start) / 60_000)
  if (minutes < 1) return 'Under 1 min'
  if (minutes < 60) return `${minutes} min`
  const hours = Math.floor(minutes / 60)
  const rest = minutes % 60
  return rest === 0 ? `${hours} hr` : `${hours} hr ${rest} min`
}

const dateFormat = new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: 'numeric' })

/** "Sep 30, 2026", or null for a missing/invalid timestamp. */
export function formatCompletedDate(completedAt: string | null): string | null {
  if (!completedAt) return null
  const time = Date.parse(completedAt)
  return Number.isNaN(time) ? null : dateFormat.format(time)
}
