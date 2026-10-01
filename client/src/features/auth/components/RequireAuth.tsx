import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { signInUrl } from '@/lib/authRedirect'
import { getCurrentUser } from '@/lib/auth'

/**
 * Gate for every /app route: the server session decides. Nothing of the page is rendered until the session is
 * confirmed, and a missing session sends the visitor to sign-in with this page as the destination.
 */
function RequireAuth({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false)

  useEffect(() => {
    let cancelled = false
    getCurrentUser()
      .then((user) => {
        if (cancelled) return
        if (user) setReady(true)
        else window.location.replace(signInUrl(window.location.pathname + window.location.search))
      })
      // A network failure is not "signed out": render the page, which shows its own retryable error.
      .catch(() => !cancelled && setReady(true))
    return () => {
      cancelled = true
    }
  }, [])

  return ready ? <>{children}</> : <div role="status" aria-label="Checking your session" className="min-h-screen bg-cream" />
}

export default RequireAuth
