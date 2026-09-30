import type { GreetingView } from '../data/dashboardViewModel'
import Skeleton from './Skeleton'

function WelcomeHeader({ greeting, loading }: { greeting: GreetingView; loading: boolean }) {
  return (
    <section data-dash="greeting" aria-labelledby="dashboard-greeting">
      <h1
        id="dashboard-greeting"
        className="font-display text-[30px] font-extrabold leading-[1.1] tracking-[-0.025em] text-deep sm:text-[38px] xl:text-[42px]"
      >
        {loading ? <Skeleton>{greeting.greeting}</Skeleton> : greeting.greeting}
        <span className="block text-deep/45">{greeting.prompt || ' '}</span>
      </h1>
      <p className="mt-3 max-w-[520px] font-serif text-[16px] leading-[1.5] text-ink/70 sm:mt-4 sm:text-[17px]">
        {greeting.intro || ' '}
      </p>
    </section>
  )
}

export default WelcomeHeader
