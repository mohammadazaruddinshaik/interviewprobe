import { useEffect, useRef } from 'react'
import type { EndFlow } from '../hooks/roomReducer'

interface EndInterviewDialogProps {
  flow: EndFlow
  onCancel: () => void
  onConfirm: () => void
}

/** Native <dialog>: modal focus trap, Escape to close and focus restoration come from the platform. */
function EndInterviewDialog({ flow, onCancel, onConfirm }: EndInterviewDialogProps) {
  const ref = useRef<HTMLDialogElement>(null)
  const open = flow.status !== 'closed'

  useEffect(() => {
    const dialog = ref.current
    if (!dialog) return
    if (open && !dialog.open) dialog.showModal()
    if (!open && dialog.open) dialog.close()
  }, [open])

  const ending = flow.status === 'ending'
  return (
    <dialog
      ref={ref}
      aria-labelledby="end-title"
      aria-describedby="end-desc"
      onCancel={(e) => {
        e.preventDefault() // we close via state so a pending request can't be dismissed mid-flight
        if (!ending) onCancel()
      }}
      className="m-auto w-[min(92vw,440px)] rounded-[20px] border border-ink/12 bg-cream p-0 text-ink shadow-[0_24px_60px_-20px_rgb(20_42_11/0.45)] backdrop:bg-ink/40"
    >
      <div className="p-6">
        <h2 id="end-title" className="font-display text-[22px] font-extrabold tracking-[-0.02em] text-deep">
          End this interview?
        </h2>
        <p id="end-desc" className="mt-2 font-serif text-[15.5px] leading-[1.5] text-ink/70">
          The interview will finish now, and your current question stays unanswered. You’ll get your evaluation based on what you’ve answered so far.
        </p>
        {flow.status === 'error' && (
          <p role="alert" className="mt-3 rounded-xl border border-orange/30 bg-orange/[0.06] px-3 py-2.5 text-[13.5px] text-deep">
            {flow.message}
          </p>
        )}
        <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <button
            type="button"
            onClick={onCancel}
            disabled={ending}
            autoFocus
            className="h-11 rounded-xl border border-forest/30 bg-cream px-5 text-[14px] font-semibold text-forest outline-offset-2 transition-colors hover:bg-forest/[0.05] focus-visible:outline-[3px] focus-visible:outline-yellow disabled:opacity-50 motion-reduce:transition-none"
          >
            Keep going
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={ending}
            aria-busy={ending}
            className="h-11 rounded-xl bg-forest px-5 text-[14px] font-semibold text-cream outline-offset-2 transition-colors hover:enabled:bg-forest-light focus-visible:outline-[3px] focus-visible:outline-yellow disabled:opacity-70 motion-reduce:transition-none"
          >
            {ending ? 'Ending…' : flow.status === 'error' ? 'Try again' : 'End interview'}
          </button>
        </div>
      </div>
    </dialog>
  )
}

export default EndInterviewDialog
