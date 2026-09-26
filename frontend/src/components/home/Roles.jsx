import { ROLES } from '../../data/interviewCatalog.js'
import SectionHeading from '../ui/SectionHeading.jsx'
import RoleCard from './RoleCard.jsx'

// Renders every role the backend actually supports (src/data/
// interviewCatalog.js, kept in sync with backend/app/domain/enums.py) —
// never a hardcoded subset that can drift as roles are added.
function Roles() {
  return (
    <section id="roles" className="scroll-mt-28 px-6 py-20">
      <div className="mx-auto max-w-7xl">
        <SectionHeading
          align="center"
          eyebrow="Role Coverage"
          title="Practice for the role you're chasing."
          className="mb-14"
        />

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {ROLES.map((role) => (
            <RoleCard key={role.id} icon={role.icon} title={role.label} description={role.description} />
          ))}
        </div>
      </div>
    </section>
  )
}

export default Roles
