import { ArrowRight } from 'lucide-react'

interface SendButtonProps {
  label: string
  busy: boolean
  disabled: boolean
  onClick: () => void
  className?: string
}

function SendButton({ label, busy, disabled, onClick, className = '' }: SendButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled || busy}
      aria-busy={busy}
      className={`group inline-flex items-center justify-center gap-3 rounded-xl bg-forest text-cream shadow-[inset_0_1px_0_rgb(255_255_255/0.14),0_1px_2px_rgb(20_42_11/0.3),0_10px_20px_-10px_rgb(20_42_11/0.55)] outline-offset-4 transition-[background-color,translate] duration-200 ease-out hover:enabled:-translate-y-0.5 hover:enabled:bg-forest-light focus-visible:outline-[3px] focus-visible:outline-yellow active:translate-y-0 disabled:cursor-not-allowed disabled:shadow-none motion-reduce:transition-none motion-reduce:hover:translate-y-0 ${
        busy ? 'disabled:bg-forest/80' : 'disabled:bg-forest/35'
      } ${className}`}
    >
      {busy ? (
        <>
          <span aria-hidden="true" className="h-4 w-4 animate-spin rounded-full border-2 border-cream/40 border-t-cream motion-reduce:animate-none" />
          Sending…
        </>
      ) : (
        <>
          {label}
          <ArrowRight size={18} aria-hidden="true" className="transition-transform duration-200 group-hover:group-enabled:translate-x-1 motion-reduce:transition-none" />
        </>
      )}
    </button>
  )
}

export default SendButton
