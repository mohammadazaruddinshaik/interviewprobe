import { useEffect, useState } from 'react'

/** Whole seconds left until `until` (epoch ms), ticking once a second; 0 when null or elapsed. */
export function useRetryCountdown(until: number | null): number {
  const [now, setNow] = useState(() => Date.now())

  useEffect(() => {
    if (until === null) return
    const tick = () => setNow(Date.now())
    tick()
    const id = window.setInterval(tick, 1000)
    return () => window.clearInterval(id)
  }, [until])

  return until === null ? 0 : Math.max(0, Math.ceil((until - now) / 1000))
}
