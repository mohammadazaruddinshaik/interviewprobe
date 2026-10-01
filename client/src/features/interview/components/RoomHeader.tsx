import { FileText, Maximize2 } from 'lucide-react'
import { roleLabel } from '@/features/dashboard/lib/labels'

interface RoomHeaderProps {
  role: string
  onTranscript: () => void
  onEnd: () => void
  endDisabled: boolean
  /** Shown only when the browser supports fullscreen and the room is not in it yet. */
  onFullscreen: (() => void) | null
}

const quiet =
  'inline-flex min-h-11 min-w-11 items-center justify-center gap-2 rounded-lg px-2.5 text-[13px] font-medium text-cream/60 outline-offset-2 transition-colors duration-200 hover:text-cream focus-visible:outline-[3px] focus-visible:outline-yellow disabled:cursor-not-allowed disabled:opacity-40 motion-reduce:transition-none sm:px-3'

/** Identity on the left, two quiet actions on the right. No counters, no planner or evaluation details. */
function RoomHeader({ role, onTranscript, onEnd, endDisabled, onFullscreen }: RoomHeaderProps) {
  return (
    <header data-room="header" className="relative z-10 mx-auto flex max-w-[1100px] items-center justify-between gap-3 px-4 pt-3 sm:px-6">
      <div className="min-w-0">
        <p className="font-display text-[15px] font-extrabold leading-tight tracking-[-0.02em] text-cream">InterviewProbe</p>
        <p className="truncate text-[12px] leading-tight text-cream/50">{roleLabel(role)} Interview</p>
      </div>
      <div className="flex shrink-0 items-center">
        {onFullscreen && (
          <button type="button" onClick={onFullscreen} className={quiet} aria-label="Enter full screen">
            <Maximize2 size={16} aria-hidden="true" />
          </button>
        )}
        <button type="button" onClick={onTranscript} className={quiet} aria-label="Open transcript">
          <FileText size={16} aria-hidden="true" />
          <span className="max-sm:hidden">Transcript</span>
        </button>
        <button type="button" onClick={onEnd} disabled={endDisabled} className={quiet}>
          <span className="sm:hidden">End</span>
          <span className="max-sm:hidden">End interview</span>
        </button>
      </div>
    </header>
  )
}

export default RoomHeader
