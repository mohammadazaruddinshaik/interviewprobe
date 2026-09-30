import { difficultyCopy } from '../lib/copy'
import RadioGroup from './RadioGroup'

interface DifficultySelectorProps {
  difficulties: string[]
  value: string
  onChange: (value: string) => void
  disabled: boolean
}

function DifficultySelector({ difficulties, value, onChange, disabled }: DifficultySelectorProps) {
  return (
    <RadioGroup
      label="Difficulty"
      options={difficulties}
      value={value}
      onChange={onChange}
      disabled={disabled}
      className="grid grid-cols-3 gap-2"
      optionClassName={(selected) =>
        `min-h-16 rounded-[14px] border px-3.5 py-3 text-left transition-[border-color,background-color,box-shadow] duration-200 motion-reduce:transition-none ${
          selected
            ? 'border-forest bg-forest shadow-[0_12px_24px_-16px_rgb(20_42_11/0.6)]'
            : 'border-ink/12 bg-white/55 hover:border-forest/40'
        }`
      }
      renderOption={(option, selected) => {
        const copy = difficultyCopy(option)
        return (
          <>
            <span className={`block text-[15px] font-semibold ${selected ? 'text-cream' : 'text-deep'}`}>{copy.label}</span>
            {copy.description && (
              <span className={`mt-0.5 block text-[12.5px] leading-[1.35] ${selected ? 'text-cream/70' : 'text-ink/60'}`}>
                {copy.description}
              </span>
            )}
          </>
        )
      }}
    />
  )
}

export default DifficultySelector
