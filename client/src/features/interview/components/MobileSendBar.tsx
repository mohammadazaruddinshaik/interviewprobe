import SendButton from './SendButton'

interface MobileSendBarProps {
  label: string
  busy: boolean
  disabled: boolean
  characters: number
  onSend: () => void
}

function MobileSendBar({ label, busy, disabled, characters, onSend }: MobileSendBarProps) {
  return (
    <div className="fixed inset-x-0 bottom-0 z-30 border-t border-ink/12 bg-cream px-4 pb-[calc(10px+env(safe-area-inset-bottom))] pt-2.5 lg:hidden">
      <div className="flex items-center gap-3">
        <p className="flex-1 text-[12.5px] text-ink/55">{characters.toLocaleString()} characters</p>
        <SendButton label={label} busy={busy} disabled={disabled} onClick={onSend} className="h-12 shrink-0 px-6 text-[15px] font-semibold" />
      </div>
    </div>
  )
}

export default MobileSendBar
