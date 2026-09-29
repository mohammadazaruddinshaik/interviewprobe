const A = "/assets/interviewprobe-landing";

export function Navigation() {
  return (
    <nav className="relative z-50" data-anim="nav">
      <div className="flex h-[72px] items-center justify-between px-[5vw] lg:h-[88px]">
        <a href="/" aria-label="InterviewProbe home">
          <img
            src={`${A}/brand/logo-placeholder.svg`}
            alt="InterviewProbe"
            className="h-9 w-auto lg:h-12"
          />
        </a>

        <div className="flex items-center gap-3 sm:gap-4">
          <a
            href="/setup"
            className="hidden items-center gap-2 rounded-full bg-forest px-6 py-3 font-display text-[15px] font-semibold text-white transition-colors hover:bg-green sm:inline-flex"
          >
            Start Interview
            <svg
              width="15"
              height="15"
              viewBox="0 0 64 64"
              fill="none"
              aria-hidden="true"
            >
              <path
                d="M16 48 L48 16 M29 16 H48 V35"
                stroke="currentColor"
                strokeWidth="5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </a>

          <button
            className="flex h-11 w-11 items-center justify-center rounded-lg transition-colors hover:bg-ink/5"
            aria-label="Menu"
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
              <path
                d="M3 6h18M3 12h18M3 18h18"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
              />
            </svg>
          </button>
        </div>
      </div>
    </nav>
  );
}
