import { ROLES } from '../../data/interviewCatalog.js'

// The reference's row here is fabricated company logos ("trusted by
// Google, Microsoft, Amazon…") — InterviewProbe has no such partnerships,
// so this keeps the reference's visual rhythm (a muted horizontal row
// beneath a small trust heading) with the one thing that's actually true:
// the real roles the product supports, drawn from the same catalog the
// interview setup page uses.
function TrustSection() {
  return (
    <section id="trust" className="scroll-mt-4 px-4 py-6 text-center sm:px-6 lg:px-10">
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-muted">
        Built for Modern Technical Interviews
      </p>

      <div className="mt-4 flex flex-wrap items-center justify-center gap-x-7 gap-y-2">
        {ROLES.map((role) => (
          <span key={role.id} className="flex items-center gap-1.5 text-sm font-medium text-ink/50 grayscale">
            <role.icon className="h-3.5 w-3.5" />
            {role.label}
          </span>
        ))}
      </div>
    </section>
  )
}

export default TrustSection
