interface DashboardNoticeProps {
  title: string
  message: string
  action: { label: string; onClick?: () => void; href?: string }
}

const buttonClass =
  'inline-flex h-[46px] items-center justify-center rounded-[12px] bg-forest px-6 text-[14px] font-semibold text-cream shadow-[inset_0_1px_0_rgb(255_255_255/0.14),0_1px_2px_rgb(20_42_11/0.3)] outline-offset-4 transition-[background-color,translate] duration-200 ease-out hover:-translate-y-0.5 hover:bg-forest-light focus-visible:outline-[3px] focus-visible:outline-yellow active:translate-y-0 motion-reduce:transition-none motion-reduce:hover:translate-y-0'

/** Compact full-width state used when the dashboard cannot be shown (error / signed out). */
function DashboardNotice({ title, message, action }: DashboardNoticeProps) {
  return (
    <section
      data-dash="greeting"
      role="alert"
      className="rounded-[20px] border border-ink/12 bg-white/60 p-6 shadow-[0_1px_2px_rgb(20_42_11/0.05)] sm:p-8 lg:col-span-2"
    >
      <h1 className="font-display text-[26px] font-extrabold leading-[1.1] tracking-[-0.02em] text-deep sm:text-[32px]">{title}</h1>
      <p className="mt-3 max-w-[520px] font-serif text-[16px] leading-[1.5] text-ink/70">{message}</p>
      {action.href ? (
        <a href={action.href} className={`${buttonClass} mt-6`}>
          {action.label}
        </a>
      ) : (
        <button type="button" onClick={action.onClick} className={`${buttonClass} mt-6`}>
          {action.label}
        </button>
      )}
    </section>
  )
}

export default DashboardNotice
