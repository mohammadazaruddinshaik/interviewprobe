import { useEffect, useRef, useState } from 'react'
import { hideOnError } from '@/lib/image'
import { ApiError } from '@/lib/api'
import { usePageEntrance } from '@/features/app/hooks/usePageEntrance'
import { getCurrentUser, signInWithGoogle } from '@/lib/auth'
import { safeNext } from '@/lib/authRedirect'

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

/** Where to go once signed in: the page the visitor was trying to reach, otherwise the dashboard. */
const destination = () => safeNext(new URLSearchParams(window.location.search).get('next')) ?? '/app'

function SignInPage() {
  const scope = usePageEntrance()
  const buttonRef = useRef<HTMLDivElement>(null)
  const [error, setError] = useState<string | null>(
    CLIENT_ID ? null : 'Google Sign-In isn’t configured. Set VITE_GOOGLE_CLIENT_ID and restart the dev server.',
  )
  const [busy, setBusy] = useState(false)

  // Already signed in: the sign-in page has nothing to offer, so continue straight to the destination.
  useEffect(() => {
    let cancelled = false
    getCurrentUser()
      .then((user) => {
        if (user && !cancelled) window.location.replace(destination())
      })
      .catch(() => undefined)
    return () => {
      cancelled = true
    }
  }, [])

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
              window.location.assign(destination())
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
    <main ref={scope} className="relative min-h-screen overflow-hidden bg-cream text-ink lg:grid lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
      <section className="relative flex flex-col justify-center gap-10 px-6 pb-10 pt-8 sm:px-12 lg:gap-9 lg:px-16 lg:py-10">
        <a data-enter="" href="/" aria-label="InterviewProbe home" className="relative block h-[38px] w-[196px] overflow-hidden rounded-sm outline-offset-4 focus-visible:outline-[3px] focus-visible:outline-yellow">
          <img src="/assets/landing/logo-510.webp" alt="InterviewProbe" width={510} height={190} decoding="async" onError={hideOnError} className="absolute -left-[32px] -top-[27px] h-[95px] w-[255px] max-w-none" />
        </a>
        <div data-enter="" className="max-w-[560px]">
          <span aria-hidden="true" className="mb-6 block h-[2px] w-10 bg-orange" />
          <h1 className="font-serif text-[44px] leading-[1.04] tracking-[-0.025em] text-ink sm:text-[60px]">
            Practice the interview.
            <span className="mt-1 block">
              <span className="bg-gradient-to-t from-yellow from-[30%] to-transparent to-[30%] px-1 -mx-1">Not the script.</span>
            </span>
          </h1>
          <p className="mt-6 max-w-[460px] font-serif text-[18px] leading-[1.5] text-ink/70">
            An adaptive technical interview with a voice-led AI interviewer that follows your answers, then a result grounded in what you actually said.
          </p>
        </div>
        <ol data-enter="" aria-label="How it works" className="mt-0 hidden max-w-[460px] gap-0 border-t border-ink/12 lg:grid">
          {[
            ['01', 'Choose a role', 'Add a resume if you like.'],
            ['02', 'Answer by voice', 'The interviewer follows what you say.'],
            ['03', 'Review the evidence', 'A result grounded in your answers.'],
          ].map(([n, title, text]) => (
            <li key={n} className="grid grid-cols-[40px_minmax(0,1fr)] items-baseline gap-3 border-b border-ink/12 py-3">
              <span className="font-serif text-[15px] text-orange">{n}</span>
              <span>
                <span className="block text-[15px] font-semibold text-ink">{title}</span>
                <span className="block text-[13.5px] text-ink/60">{text}</span>
              </span>
            </li>
          ))}
        </ol>
      </section>

      <section className="relative flex items-center justify-center px-5 pb-14 sm:px-8 lg:py-12">
        <div data-enter="" className="w-full max-w-[420px] rounded-[24px] border border-ink/12 bg-white/70 p-8 text-center shadow-[0_1px_2px_rgb(6_11_7/0.04),0_30px_60px_-36px_rgb(6_11_7/0.4)] sm:p-10">
          <h2 className="font-serif text-[32px] leading-[1.1] tracking-[-0.015em] text-ink">Sign in</h2>
          <p className="mt-3 text-[15px] leading-[1.5] text-ink/65">Continue with Google to start an interview or review your results.</p>

          <div className="mt-8 flex min-h-[44px] justify-center" aria-busy={busy}>
            {busy ? (
              <p role="status" className="inline-flex items-center gap-2.5 text-[14px] font-medium text-ink/70">
                <span aria-hidden="true" className="size-4 animate-spin rounded-full border-2 border-ink/20 border-t-ink motion-reduce:animate-none" />
                Signing you in…
              </p>
            ) : (
              <div ref={buttonRef} />
            )}
          </div>

          <div aria-live="polite" className="mt-4 min-h-[22px]">
            {error && (
              <p role="alert" className="rounded-xl border border-orange/30 bg-orange/[0.06] px-3.5 py-2.5 text-[13.5px] text-ink">
                {error}
              </p>
            )}
          </div>

          <p className="mt-6 border-t border-ink/10 pt-5 text-[12.5px] leading-[1.5] text-ink/50">
            Google only verifies who you are. InterviewProbe never sees your Google password.
          </p>
        </div>
      </section>
    </main>
  )
}

export default SignInPage
