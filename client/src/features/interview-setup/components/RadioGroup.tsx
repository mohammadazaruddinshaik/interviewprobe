import type { KeyboardEvent, ReactNode } from 'react'

interface RadioGroupProps<T extends string | number> {
  label: string
  options: T[]
  value: T
  onChange: (value: T) => void
  disabled?: boolean
  className: string
  /** Renders an option's content; the wrapper button supplies radio semantics and focus handling. */
  renderOption: (option: T, selected: boolean) => ReactNode
  optionClassName: (selected: boolean) => string
}

/** Radio semantics for a row/grid of buttons: one tab stop (roving tabindex) and arrow-key selection. */
function RadioGroup<T extends string | number>({
  label,
  options,
  value,
  onChange,
  disabled,
  className,
  renderOption,
  optionClassName,
}: RadioGroupProps<T>) {
  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    const keys: Record<string, number> = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }
    const step = keys[event.key]
    if (!step || disabled) return
    event.preventDefault()
    const index = options.indexOf(value)
    const next = options[(index + step + options.length) % options.length]
    onChange(next)
    const buttons = event.currentTarget.querySelectorAll<HTMLButtonElement>('[role="radio"]')
    buttons[options.indexOf(next)]?.focus()
  }

  return (
    <div role="radiogroup" aria-label={label} onKeyDown={onKeyDown} className={className}>
      {options.map((option) => {
        const selected = option === value
        return (
          <button
            key={option}
            type="button"
            role="radio"
            aria-checked={selected}
            tabIndex={selected ? 0 : -1}
            disabled={disabled}
            onClick={() => onChange(option)}
            className={`${optionClassName(selected)} outline-offset-[3px] focus-visible:outline-[3px] focus-visible:outline-yellow disabled:cursor-not-allowed`}
          >
            {renderOption(option, selected)}
          </button>
        )
      })}
    </div>
  )
}

export default RadioGroup
