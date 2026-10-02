import type { SyntheticEvent } from 'react'

// A failed image hides itself so the surrounding frame stays intact (no broken-image icon).
export function hideOnError(event: SyntheticEvent<HTMLImageElement>) {
  event.currentTarget.style.visibility = 'hidden'
}
