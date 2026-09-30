import type { CatalogRole } from '../api/interviewApi'
import RadioGroup from './RadioGroup'

interface RoleSelectorProps {
  roles: CatalogRole[]
  value: string
  onChange: (value: string) => void
  disabled: boolean
}

function RoleSelector({ roles, value, onChange, disabled }: RoleSelectorProps) {
  const byValue = new Map(roles.map((r) => [r.value, r]))
  return (
    <RadioGroup
      label="Role"
      options={roles.map((r) => r.value)}
      value={value}
      onChange={onChange}
      disabled={disabled}
      className="grid grid-cols-1 gap-2 min-[480px]:grid-cols-2"
      optionClassName={(selected) =>
        `flex min-h-[60px] w-full items-center gap-3.5 rounded-[14px] border px-3.5 py-3 text-left transition-[border-color,background-color,box-shadow,translate] duration-200 motion-reduce:transition-none ${
          selected
            ? 'border-forest bg-forest/[0.05] shadow-[0_1px_2px_rgb(20_42_11/0.06),0_12px_24px_-18px_rgb(20_42_11/0.4)]'
            : 'border-ink/12 bg-white/55 hover:-translate-y-px hover:border-forest/40 motion-reduce:hover:translate-y-0'
        }`
      }
      renderOption={(option, selected) => {
        const role = byValue.get(option)!
        return (
          <>
            <span
              aria-hidden="true"
              className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full border-[1.5px] ${
                selected ? 'border-forest bg-forest' : 'border-ink/30'
              }`}
            >
              {selected && <span className="mb-[2px] h-[5px] w-[9px] -rotate-45 border-b-2 border-l-2 border-cream" />}
            </span>
            <span className="min-w-0">
              <span className="block text-[15px] font-semibold leading-snug text-deep">{role.label}</span>
              <span className="mt-0.5 block text-[12.5px] leading-snug text-ink/60">{role.description}</span>
            </span>
          </>
        )
      }}
    />
  )
}

export default RoleSelector
