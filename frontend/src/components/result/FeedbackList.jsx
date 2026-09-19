function FeedbackList({ title, items, icon: Icon, emptyMessage, iconClassName }) {
  return (
    <section className="border-t border-line/70">
      <div className="mx-auto max-w-3xl px-6 py-10 sm:px-8">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">{title}</h2>
        {items.length === 0 ? (
          <p className="mt-4 text-sm text-muted">{emptyMessage}</p>
        ) : (
          <ul className="mt-5 flex flex-col gap-3.5">
            {items.map((item, index) => (
              <li key={index} className="flex items-start gap-3">
                <span
                  className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full ${iconClassName}`}
                >
                  <Icon className="h-3 w-3" />
                </span>
                <p className="text-[15px] leading-relaxed text-ink">{item}</p>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  )
}

export default FeedbackList
