import { useEffect, useRef, useState } from 'react'
import { ApiError } from '@/lib/api'
import { signInWithGoogle } from '@/lib/auth'

// Google Identity Services (ID-token flow): the button returns a signed ID token ("credential") to the
// callback below; the backend verifies it and sets the HttpOnly session cookie. No redirects, no client secret.
const GIS_SRC = 'https://accounts.google.com/gsi/client'
const CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined

interface GoogleIdApi {
  initialize: (config: { client_id: string; callback: (response: { credential?: string }) => void }) => void
  renderButton: (parent: HTMLElement, options: Record<string, string | number>) => void
}
declare global {
  interface Window {
    google?: { accounts: { id: GoogleIdApi } }
  }
}

function loadGoogleScript(): Promise<void> {
  if (window.google?.accounts?.id) return Promise.resolve()
  return new Promise((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>(`script[src="${GIS_SRC}"]`)
    const script = existing ?? Object.assign(document.createElement('script'), { src: GIS_SRC, async: true, defer: true })
    script.addEventListener('load', () => resolve(), { once: true })
    script.addEventListener('error', () => reject(new Error('gis-load-failed')), { once: true })
    if (!existing) document.head.appendChild(script)
  })
}

function describeFailure(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.isNetworkError) return 'We couldn’t reach InterviewProbe. Check your connection and try again.'
    if (error.status === 401) return 'We couldn’t verify your Google account. Please try again.'
    if (error.status === 503) return 'Sign-in isn’t available right now. Please try again shortly.'
  }
  return 'Something went wrong while signing you in. Please try again.'
}

function SignInPage() {
  const buttonRef = useRef<HTMLDivElement>(null)
  const [error, setError] = useState<string | null>(
    CLIENT_ID ? null : 'Google Sign-In isn’t configured. Set VITE_GOOGLE_CLIENT_ID and restart the dev server.',
  )
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!CLIENT_ID) return
    let cancelled = false
    loadGoogleScript()
      .then(() => {
        const api = window.google?.accounts.id
        if (cancelled || !api || !buttonRef.current) return
        api.initialize({
          client_id: CLIENT_ID,
          callback: async ({ credential }) => {
            if (!credential) return setError('Google didn’t return a sign-in credential. Please try again.')
            setError(null)
            setBusy(true)
            try {
              await signInWithGoogle(credential) // reuses the existing auth client (POST /auth/google, cookie set by the server)
              window.location.assign('/app')
            } catch (failure) {
              setError(describeFailure(failure))
              setBusy(false)
            }
          },
        })
        buttonRef.current.innerHTML = '' // StrictMode renders the effect twice
        api.renderButton(buttonRef.current, { type: 'standard', theme: 'outline', size: 'large', text: 'signin_with', shape: 'pill', width: 280 })
      })
      .catch(() => !cancelled && setError('We couldn’t load Google Sign-In. Check your connection or ad blocker and try again.'))
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <main className="flex min-h-screen items-center justify-center bg-cream px-4 py-10 text-ink">
      <section className="w-full max-w-[420px] rounded-[20px] border border-ink/12 bg-white/60 p-7 text-center shadow-[0_1px_2px_rgb(20_42_11/0.05),0_18px_36px_-24px_rgb(20_42_11/0.3)] sm:p-9">
        <a href="/" aria-label="InterviewProbe home" className="relative mx-auto block h-[38px] w-[196px] overflow-hidden">
          <img src="/assets/landing/logo.png" alt="InterviewProbe" className="absolute -left-[32px] -top-[27px] h-[95px] w-[255px] max-w-none" />
        </a>
        <h1 className="mt-7 font-display text-[28px] font-extrabold leading-[1.1] tracking-[-0.025em] text-deep">Sign in to continue</h1>
        <p className="mt-3 font-serif text-[16px] leading-[1.5] text-ink/70">Use your Google account to practice and review your interviews.</p>

        <div className="mt-7 flex min-h-[44px] justify-center" aria-busy={busy}>
          {busy ? (
            <p role="status" className="text-[14px] font-medium text-ink/70">
              Signing you in…
            </p>
          ) : (
            <div ref={buttonRef} />
          )}
        </div>

        <div aria-live="polite" className="mt-4 min-h-[22px]">
          {error && (
            <p role="alert" className="rounded-xl border border-orange/30 bg-orange/[0.06] px-3.5 py-2.5 text-[13.5px] text-deep">
              {error}
            </p>
          )}
        </div>
      </section>
    </main>
  )
}

export default SignInPage
