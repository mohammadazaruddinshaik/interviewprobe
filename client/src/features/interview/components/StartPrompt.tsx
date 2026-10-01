import { useState } from 'react'
import { startInterview } from '@/features/interview-setup/api/interviewApi'
import { describeSubmitFailure, isAlreadyStarted } from '@/features/interview-setup/lib/submitErrors'

/**
 * Shown for an interview that was created but never started (for example, left behind in setup). It starts THIS
 * interview with the existing start endpoint instead of sending the candidate to create a second one, then reloads
 * the room, which loads the started interview from the server as usual.
 */
function StartPrompt({ interviewId }: { interviewId: string }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const start = async () => {
    if (busy) return
    setBusy(true)
    setError(null)
    try {
      await startInterview(interviewId)
      window.location.reload()
    } catch (failure) {
      if (isAlreadyStarted(failure)) return window.location.reload()
      const described = describeSubmitFailure(failure)
      if (described.kind === 'unauthenticated') return window.location.assign('/signin')
      setError(described.message)
      setBusy(false)
    }
  }

  return (
    <section className="pt-10 sm:pt-16" aria-labelledby="start-heading">
      <p className="text-[11px] font-semibold tracking-[0.2em] text-cream/45">YOUR INTERVIEW</p>
      <h1 id="start-heading" className="mt-4 font-serif text-[34px] font-normal leading-[1.12] tracking-[-0.01em] text-cream sm:text-[46px]">
        Ready when you are.
      </h1>
      <p className="mt-4 max-w-[480px] text-[16px] leading-[1.55] text-cream/65">
        Your interviewer will open with a first question and follow the conversation from there. Make sure your microphone is ready.
      </p>
      <button
        type="button"
        onClick={() => void start()}
        disabled={busy}
        aria-busy={busy}
        className="mt-8 inline-flex h-[54px] items-center justify-center rounded-xl bg-yellow px-8 text-[16px] font-semibold text-forest outline-offset-4 transition-transform duration-200 hover:enabled:-translate-y-0.5 focus-visible:outline-[3px] focus-visible:outline-cream disabled:opacity-70 motion-reduce:transition-none"
      >
        {busy ? 'Starting…' : 'Start interview'}
      </button>
      {error && (
        <p role="alert" className="mt-4 max-w-[480px] text-[14.5px] text-cream/85">
          {error}
        </p>
      )}
      <a href="/app" className="mt-6 block w-fit rounded-lg py-2 text-[14px] font-medium text-cream/60 outline-offset-2 hover:text-cream focus-visible:outline-[3px] focus-visible:outline-yellow">
        Back to dashboard
      </a>
    </section>
  )
}

export default StartPrompt
