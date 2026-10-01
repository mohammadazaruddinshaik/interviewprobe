import { useEffect, useRef, useState } from 'react'

/**
 * Keeps the previous question text on screen for a moment while it fades out, so a new question is a hand-over
 * rather than a swap. Under reduced motion there is no hand-over layer at all.
 */
export function useQuestionTransition(id: string, text: string) {
  const [leaving, setLeaving] = useState<{ id: string; text: string } | null>(null)
  const last = useRef({ id, text })

  useEffect(() => {
    if (last.current.id === id) return
    const previous = last.current
    last.current = { id, text }
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    setLeaving(previous)
    const timer = window.setTimeout(() => setLeaving(null), 650)
    return () => window.clearTimeout(timer)
  }, [id, text])

  return leaving
}
