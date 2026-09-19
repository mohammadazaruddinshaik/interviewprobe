import { CheckIcon } from '../ui/icons.jsx'

function TopicSelector({ topics, selected, onToggle, max }) {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {topics.map((topic) => {
        const isSelected = selected.includes(topic.id)
        const isDisabled = !isSelected && selected.length >= max

        return (
          <button
            key={topic.id}
            type="button"
            aria-pressed={isSelected}
            disabled={isDisabled}
            onClick={() => onToggle(topic.id)}
            className={`flex items-center gap-2.5 rounded-xl border px-4 py-3 text-left text-sm font-medium transition-all duration-200 ${
              isSelected
                ? 'border-accent bg-accent-soft/60 text-ink'
                : isDisabled
                  ? 'cursor-not-allowed border-line bg-white/40 text-ink/40'
                  : 'border-line bg-white/70 text-ink hover:border-ink/20 hover:bg-white'
            }`}
          >
            <span
              className={`flex h-4 w-4 shrink-0 items-center justify-center rounded border ${
                isSelected ? 'border-accent bg-accent text-cream' : 'border-line'
              }`}
            >
              {isSelected && <CheckIcon className="h-2.5 w-2.5" />}
            </span>
            {topic.label}
          </button>
        )
      })}
    </div>
  )
}

export default TopicSelector
