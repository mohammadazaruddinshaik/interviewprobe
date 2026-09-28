import {
  BackendRoleIcon,
  EngineeringIcon,
  FullStackRoleIcon,
  InterfaceIcon,
  JavaRoleIcon,
  LearningIcon,
  AIEngineerRoleIcon,
} from '../ui/interviewIcons.jsx'
import RoleCard from './RoleCard.jsx'

// Icons are looked up by role id here rather than added to
// data/interviewCatalog.js's own `icon` field, keeping the mapping local
// to the setup page.
const ROLE_ICONS = {
  AI_ENGINEER: AIEngineerRoleIcon,
  FRONTEND_DEVELOPER: InterfaceIcon,
  BACKEND_DEVELOPER: BackendRoleIcon,
  JAVA_DEVELOPER: JavaRoleIcon,
  SDE: EngineeringIcon,
  SDE_INTERN: LearningIcon,
  FULL_STACK_DEVELOPER: FullStackRoleIcon,
}

// A single-column role list — a compact "selection interface" rather than
// a card grid. Every row is the same full width regardless of viewport,
// which is also what keeps a 24-character name like "Software Development
// Engineer" readable without ever needing to shrink a column.
function RoleSelector({ roles, value, onChange }) {
  return (
    <div className="flex flex-col divide-y divide-line/70 lg:flex-1">
      {roles.map((role) => (
        <RoleCard
          className="lg:flex-1"
          key={role.id}
          icon={ROLE_ICONS[role.id] ?? AIEngineerRoleIcon}
          label={role.label}
          description={role.description}
          selected={role.id === value}
          onClick={() => onChange(role.id)}
        />
      ))}
    </div>
  )
}

export default RoleSelector
