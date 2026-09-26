// One role's card in the coverage grid — icon, name, and a short
// description drawn straight from the same catalog (src/data/
// interviewCatalog.js) the interview setup page uses, so this section can
// never drift out of sync with the roles actually offered.
function RoleCard({ icon: Icon, title, description }) {
  return (
    <div className="group rounded-2xl border border-white/70 bg-white/60 p-5 shadow-glass-sm backdrop-blur-xl transition-all duration-200 hover:-translate-y-0.5 hover:bg-white/80">
      <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary-light text-primary transition-transform duration-200 group-hover:scale-105">
        <Icon className="h-5 w-5" />
      </span>
      <h3 className="mt-4 text-base font-semibold text-ink">{title}</h3>
      <p className="mt-1.5 text-sm leading-relaxed text-muted">{description}</p>
    </div>
  )
}

export default RoleCard
