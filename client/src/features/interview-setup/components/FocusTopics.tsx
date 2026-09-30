import { Check } from 'lucide-react'
import type { CatalogTopic } from '../api/interviewApi'

interface FocusTopicsProps {
  topics: CatalogTopic[]
  selected: string[]
  cap: number
  min: number
  max: number
  onToggle: (value: string) => void
  disabled: boolean
}

function FocusTopics({ topics, selected, cap, min, max, onToggle, disabled }: FocusTopicsProps) {
  const count = selected.length
  const full = count >= topics.length
  let note = ''
  let warn = false
  if (count < min) {
    note = 'Choose at least one focus area to continue.'
    warn = true
  } else if (full) note = `All ${count} focus areas for this role are selected`
  else if (count >= cap) note = `Maximum of ${max} reached. Deselect one to choose another.`

  return (
    <div>
      <div className="mb-3 flex items-center justify-between gap-3 text-[13px] text-ink/60">
        <span aria-live="polite">
          <b className="font-semibold text-deep">{count}</b> of up to {cap} selected
        </span>
        <span aria-hidden="true" className="flex gap-1">
          {Array.from({ length: cap }, (_, i) => (
            <i key={i} className={`h-[5px] w-4 rounded-[3px] transition-colors duration-200 motion-reduce:transition-none ${i < count ? 'bg-forest' : 'bg-forest/[0.12]'}`} />
          ))}
        </span>
      </div>

      <div role="group" aria-label="Focus areas" className="flex flex-wrap gap-2">
        {topics.map((topic) => {
          const on = selected.includes(topic.value)
          const blocked = !on && count >= cap
          return (
            <button
              key={topic.value}
              type="button"
              aria-pressed={on}
              disabled={disabled || blocked}
              onClick={() => onToggle(topic.value)}
              className={`inline-flex min-h-11 items-center gap-2 rounded-full border px-4 text-[14px] font-medium outline-offset-[3px] transition-[border-color,background-color,color] duration-200 focus-visible:outline-[3px] focus-visible:outline-yellow disabled:cursor-not-allowed motion-reduce:transition-none ${
                on
                  ? 'border-forest bg-forest text-cream'
                  : blocked
                    ? 'border-dashed border-ink/12 bg-transparent text-deep opacity-40'
                    : 'border-ink/12 bg-white/55 text-deep hover:border-forest/45 disabled:opacity-60'
              }`}
            >
              {on && <Check size={14} strokeWidth={2.6} aria-hidden="true" />}
              {topic.label}
            </button>
          )
        })}
      </div>
      <p role={warn ? 'alert' : undefined} aria-live="polite" className={`mt-3 min-h-[18px] text-[12.5px] ${warn ? 'text-orange' : 'text-ink/60'}`}>
        {note}
      </p>
    </div>
  )
}

export default FocusTopics
