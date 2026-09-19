import { MinusIcon, PlusIcon } from '../ui/icons.jsx'

function QuestionCountSelector({ value, onChange, min, max }) {
  return (
    <div className="flex items-center gap-3">
      <button
        type="button"
        aria-label="Decrease number of questions"
        disabled={value <= min}
        onClick={() => onChange(Math.max(min, value - 1))}
        className="flex h-9 w-9 items-center justify-center rounded-full border border-line text-ink transition-colors duration-200 hover:border-ink/30 hover:bg-white disabled:cursor-not-allowed disabled:opacity-40"
      >
        <MinusIcon className="h-4 w-4" />
      </button>
      <span className="w-6 text-center text-base font-semibold text-ink" aria-live="polite">
        {value}
      </span>
      <button
        type="button"
        aria-label="Increase number of questions"
        disabled={value >= max}
        onClick={() => onChange(Math.min(max, value + 1))}
        className="flex h-9 w-9 items-center justify-center rounded-full border border-line text-ink transition-colors duration-200 hover:border-ink/30 hover:bg-white disabled:cursor-not-allowed disabled:opacity-40"
      >
        <PlusIcon className="h-4 w-4" />
      </button>
    </div>
  )
}

export default QuestionCountSelector
