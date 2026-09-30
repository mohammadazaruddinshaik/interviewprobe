import RadioGroup from './RadioGroup'

interface QuestionCountSelectorProps {
  min: number
  max: number
  value: number
  onChange: (value: number) => void
  disabled: boolean
}

function QuestionCountSelector({ min, max, value, onChange, disabled }: QuestionCountSelectorProps) {
  const options = Array.from({ length: max - min + 1 }, (_, i) => min + i)
  return (
    <RadioGroup
      label="Number of questions"
      options={options}
      value={value}
      onChange={onChange}
      disabled={disabled}
      className="grid grid-cols-4 gap-2 sm:grid-cols-8"
      optionClassName={(selected) =>
        `min-h-12 rounded-xl border font-display text-[17px] font-extrabold transition-[border-color,background-color] duration-200 motion-reduce:transition-none ${
          selected ? 'border-forest bg-forest text-cream' : 'border-ink/12 bg-white/55 text-deep hover:border-forest/45'
        }`
      }
      renderOption={(option) => option}
    />
  )
}

export default QuestionCountSelector
