import { CheckIcon } from '../ui/icons.jsx'

function RoleSelector({ roles, value, onChange }) {
  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      {roles.map((role) => {
        const isSelected = role.id === value
        return (
          <button
            key={role.id}
            type="button"
            aria-pressed={isSelected}
            onClick={() => onChange(role.id)}
            className={`relative flex flex-col items-start gap-3 rounded-2xl border p-4 text-left transition-all duration-200 ${
              isSelected
                ? 'border-accent bg-accent-soft/60'
                : 'border-line bg-white/70 hover:border-ink/20 hover:bg-white'
            }`}
          >
            {isSelected && (
              <span className="absolute right-3 top-3 flex h-5 w-5 items-center justify-center rounded-full bg-accent text-cream">
                <CheckIcon className="h-3 w-3" />
              </span>
            )}
            <span
              className={`flex h-9 w-9 items-center justify-center rounded-xl ${
                isSelected ? 'bg-accent text-cream' : 'bg-accent-soft text-accent'
              }`}
            >
              <role.icon className="h-4.5 w-4.5" />
            </span>
            <div>
              <p className="text-sm font-semibold text-ink">{role.label}</p>
              <p className="mt-1 text-xs leading-snug text-muted">{role.description}</p>
            </div>
          </button>
        )
      })}
    </div>
  )
}

export default RoleSelector
