import { useEffect, useRef } from 'react'
import { X } from 'lucide-react'
import type { Question, TranscriptEntry } from '../types/interview'

interface TranscriptDrawerProps {
  open: boolean
  onClose: () => void
  entries: TranscriptEntry[]
  current: Question
}

/** Secondary, collapsed by default. Only what happened in this browser session; the backend keeps the record. */
function TranscriptDrawer({ open, onClose, entries, current }: TranscriptDrawerProps) {
  const ref = useRef<HTMLDialogElement>(null)

  useEffect(() => {
    const dialog = ref.current
    if (!dialog) return
    if (open && !dialog.open) dialog.show()
    if (!open && dialog.open) dialog.close()
  }, [open])

  return (
    <dialog
      ref={ref}
      aria-label="Transcript"
      onKeyDown={(e) => e.key === 'Escape' && onClose()}
      className="fixed inset-y-0 left-auto right-0 z-30 m-0 h-full max-h-none w-[min(100vw,380px)] border-l border-ink/12 bg-cream p-0 text-ink shadow-[-24px_0_60px_-30px_rgb(20_42_11/0.4)]"
    >
      <div className="flex h-full flex-col">
        <div className="flex items-center justify-between border-b border-ink/10 px-5 py-3">
          <h2 className="font-display text-[16px] font-extrabold tracking-[-0.01em] text-deep">Transcript</h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close transcript"
            className="grid size-10 place-items-center rounded-lg text-ink/60 outline-offset-2 hover:bg-forest/[0.06] focus-visible:outline-[3px] focus-visible:outline-yellow"
          >
            <X size={18} aria-hidden="true" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-5 py-5">
          <ol className="flex flex-col gap-6">
            {entries.map((entry) => (
              <li key={entry.questionId}>
                <p className="text-[11px] font-semibold tracking-[0.16em] text-ink/45">INTERVIEWER</p>
                <p className="mt-1 font-serif text-[15px] leading-[1.45] text-deep">{entry.question}</p>
                <p className="mt-3 text-[11px] font-semibold tracking-[0.16em] text-ink/45">YOU</p>
                <p className="mt-1 text-[14.5px] leading-[1.5] text-ink/75">{entry.answer}</p>
              </li>
            ))}
            <li>
              <p className="text-[11px] font-semibold tracking-[0.16em] text-ink/45">INTERVIEWER</p>
              <p className="mt-1 font-serif text-[15px] leading-[1.45] text-deep">{current.text}</p>
            </li>
          </ol>
        </div>
      </div>
    </dialog>
  )
}

export default TranscriptDrawer
