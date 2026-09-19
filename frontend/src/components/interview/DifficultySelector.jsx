import { ChartIcon, CheckIcon } from '../ui/icons.jsx'

function DifficultySelector({ difficulties, value, onChange }) {
  return (
    <div className="grid grid-cols-3 gap-3">
      {difficulties.map((difficulty) => {
        const isSelected = difficulty.id === value
        return (
          <button
            key={difficulty.id}
            type="button"
            aria-pressed={isSelected}
            onClick={() => onChange(difficulty.id)}
            className={`flex items-center justify-between gap-2 rounded-xl border px-3.5 py-3 text-sm font-medium transition-all duration-200 sm:px-4 ${
              isSelected
                ? 'border-accent bg-accent-soft/60 text-accent'
                : 'border-line bg-white/70 text-ink hover:border-ink/20 hover:bg-white'
            }`}
          >
            <span className="flex items-center gap-2">
              <ChartIcon className="h-4 w-4" />
              {difficulty.label}
            </span>
            <span
              className={`flex h-4 w-4 shrink-0 items-center justify-center rounded-full border ${
                isSelected ? 'border-accent bg-accent text-cream' : 'border-line'
              }`}
            >
              {isSelected && <CheckIcon className="h-2.5 w-2.5" />}
            </span>
          </button>
        )
      })}
    </div>
  )
}

export default DifficultySelector
