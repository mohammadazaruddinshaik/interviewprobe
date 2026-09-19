import { CoffeeIcon, LayoutIcon, ServerIcon, SparkIcon } from '../ui/icons.jsx'

const ROLES = [
  {
    icon: SparkIcon,
    title: 'AI Engineer',
    description: 'LLMs, RAG, agents and evaluation.',
  },
  {
    icon: ServerIcon,
    title: 'Backend Developer',
    description: 'APIs, databases and system design.',
  },
  {
    icon: LayoutIcon,
    title: 'Frontend Developer',
    description: 'JavaScript, React and modern CSS.',
  },
  {
    icon: CoffeeIcon,
    title: 'Java Developer',
    description: 'Core Java, OOP and the JVM ecosystem.',
  },
]

function Roles() {
  return (
    <section id="roles" className="border-t border-line/70">
      <div className="mx-auto max-w-7xl px-6 py-24">
        <h2 className="max-w-lg text-4xl font-semibold leading-tight tracking-tight text-ink sm:text-5xl">
          Practice for the role you&apos;re chasing.
        </h2>

        <div className="mt-14 grid grid-cols-1 gap-5 sm:grid-cols-2">
          {ROLES.map((role) => (
            <div
              key={role.title}
              className="group rounded-2xl border border-transparent p-6 transition-all duration-200 hover:-translate-y-0.5 hover:border-line hover:bg-white hover:shadow-sm"
            >
              <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent-soft text-accent transition-transform duration-200 group-hover:scale-105">
                <role.icon className="h-5 w-5" />
              </span>
              <h3 className="mt-4 text-base font-semibold text-ink">{role.title}</h3>
              <p className="mt-1.5 text-sm leading-relaxed text-muted">{role.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

export default Roles
