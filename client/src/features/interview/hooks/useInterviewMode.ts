import { useCallback, useEffect, useRef, useState } from 'react'

/**
 * "Interview mode": a focus layer for the live room, not a lockdown. A web page can ask for fullscreen and notice
 * when the candidate leaves, but it cannot stop them leaving, so this only (1) requests fullscreen, (2) shows a
 * calm "paused" cover when the page is hidden, loses focus or leaves fullscreen, and (3) swallows a few page-level
 * shortcuts. Nothing is recorded, and the answer / voice state is never touched here: returning simply uncovers it.
 */
export function useInterviewMode(active: boolean) {
  const [paused, setPaused] = useState(false)
  const [fullscreen, setFullscreen] = useState(false)
  const entered = useRef(false) // fullscreen was actually reached at least once
  const supported = typeof document !== 'undefined' && typeof document.documentElement.requestFullscreen === 'function'

  const enter = useCallback(async () => {
    if (!supported || document.fullscreenElement) return
    try {
      await document.documentElement.requestFullscreen({ navigationUI: 'hide' })
    } catch {
      /* browsers require a user gesture; the next tap on the page or "Return to interview" tries again */
    }
  }, [supported])

  useEffect(() => {
    if (!active) return
    void enter()

    const onFullscreen = () => {
      const on = !!document.fullscreenElement
      setFullscreen(on)
      if (on) entered.current = true
      else if (entered.current) setPaused(true)
    }
    const onVisibility = () => {
      if (document.visibilityState === 'hidden') setPaused(true)
    }
    let blurTimer = 0
    const onBlur = () => {
      // Brief delay: browser prompts (microphone, camera) can blur the page momentarily.
      blurTimer = window.setTimeout(() => {
        if (!document.hasFocus()) setPaused(true)
      }, 500)
    }
    const onFocus = () => window.clearTimeout(blurTimer)
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && !event.altKey && ['p', 's', 'u'].includes(event.key.toLowerCase())) {
        event.preventDefault() // print / save / view source: only the shortcuts a page can actually control
      }
    }
    // A page can only go fullscreen from a gesture: try once on the first tap or key press if the first attempt failed.
    const onFirstGesture = () => {
      if (!entered.current) void enter()
    }

    document.addEventListener('fullscreenchange', onFullscreen)
    document.addEventListener('visibilitychange', onVisibility)
    window.addEventListener('blur', onBlur)
    window.addEventListener('focus', onFocus)
    document.addEventListener('keydown', onKeyDown)
    document.addEventListener('pointerdown', onFirstGesture, { once: true })
    return () => {
      window.clearTimeout(blurTimer)
      document.removeEventListener('fullscreenchange', onFullscreen)
      document.removeEventListener('visibilitychange', onVisibility)
      window.removeEventListener('blur', onBlur)
      window.removeEventListener('focus', onFocus)
      document.removeEventListener('keydown', onKeyDown)
      document.removeEventListener('pointerdown', onFirstGesture)
      if (document.fullscreenElement) void document.exitFullscreen().catch(() => undefined)
    }
  }, [active, enter])

  const resume = useCallback(() => {
    setPaused(false)
    void enter()
  }, [enter])

  return { paused, resume, fullscreen, supported, enter }
}
