import StartButton from './StartButton'

interface MobileStartBarProps {
  title: string
  subtitle: string
  canSubmit: boolean
  busy: boolean
  busyLabel: string
  error: string | null
  onStart: () => void
}

/** Fixed bottom bar below `lg`, where the summary card's own button is hidden. */
function MobileStartBar({ title, subtitle, canSubmit, busy, busyLabel, error, onStart }: MobileStartBarProps) {
  return (
    <div className="fixed inset-x-0 bottom-0 z-30 border-t border-ink/12 bg-cream px-4 pb-[calc(10px+env(safe-area-inset-bottom))] pt-2.5 lg:hidden">
      {error && (
        <p role="alert" className="mb-2 text-[12.5px] leading-snug text-orange">
          {error}
        </p>
      )}
      <div className="flex items-center gap-3">
        <div className="min-w-0 flex-1">
          <p className="truncate text-[14px] font-semibold text-deep">{title}</p>
          <p className="mt-px truncate text-[12px] text-ink/60">{subtitle}</p>
        </div>
        <StartButton disabled={!canSubmit} busy={busy} busyLabel={busyLabel} onClick={onStart} className="h-12 shrink-0 px-5 text-[15px] font-semibold" />
      </div>
    </div>
  )
}

export default MobileStartBar
