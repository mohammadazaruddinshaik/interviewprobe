interface ResultNoticeProps {
  title: string
  message: string
  action: { label: string; onClick?: () => void; href?: string }
}

const button =
  'inline-flex h-[50px] items-center justify-center rounded-xl bg-yellow px-7 text-[15px] font-semibold text-ink outline-offset-4 transition-transform duration-200 hover:-translate-y-0.5 focus-visible:outline-[3px] focus-visible:outline-ink motion-reduce:transition-none motion-reduce:hover:translate-y-0'

/** Calm full-width notice on the dark result canvas (not found, signed out, not finished, failed). */
function ResultNotice({ title, message, action }: ResultNoticeProps) {
  return (
    <section role="alert" className="pt-10 sm:pt-16">
      <h1 className="font-serif text-[30px] font-normal leading-[1.15] tracking-[-0.01em] text-ink sm:text-[40px]">{title}</h1>
      <p className="mt-4 max-w-[520px] text-[16px] leading-[1.55] text-ink/65">{message}</p>
      {action.href ? (
        <a href={action.href} className={`${button} mt-8`}>
          {action.label}
        </a>
      ) : (
        <button type="button" onClick={action.onClick} className={`${button} mt-8`}>
          {action.label}
        </button>
      )}
    </section>
  )
}

export default ResultNotice
