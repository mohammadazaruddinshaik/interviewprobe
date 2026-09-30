import { ArrowRight, Play, Sparkles } from 'lucide-react'
import PaintHighlight from './PaintHighlight'

const PAPERS = [
  {
    src: '/assets/landing/papers/paper-left.png',
    className: 'left-[calc(50%-554px)] top-[109px] w-[99px] [transform:rotate(30deg)]',
  },
  {
    src: '/assets/landing/papers/paper-center.png',
    className: 'left-[calc(50%-494px)] top-[252px] w-[150px] [transform:rotate(-57deg)]',
  },
  {
    src: '/assets/landing/papers/paper-right.png',
    className: 'left-[calc(50%+443px)] top-[261px] w-[109px] [transform:rotate(8deg)]',
  },
]

function Hero() {
  return (
    <section className="relative px-4 pb-[15px] pt-[41px]">
      {PAPERS.map((paper) => (
        <img
          key={paper.src}
          src={paper.src}
          alt=""
          aria-hidden="true"
          data-anim="hero-paper"
          className={`pointer-events-none absolute hidden h-auto max-w-none select-none xl:block ${paper.className}`}
        />
      ))}

      <div className="relative mx-auto flex max-w-[1054px] flex-col items-center text-center">
        <p data-anim="hero-badge" className="inline-flex h-[27px] items-stretch overflow-hidden rounded-md bg-yellow text-[12.4px] font-medium text-forest lg:translate-x-[2px]">
          <span className="flex w-[29px] items-center justify-center bg-forest text-cream">
            <Sparkles size={15} aria-hidden="true" />
          </span>
          <span className="flex items-center pl-[16px] pr-[13px]">AI-Powered Interview Preparation</span>
        </p>

        <h1 data-anim="hero-title" className="mt-[18px] text-[31px] font-display font-extrabold leading-[1.1] tracking-[-0.02em] text-deep sm:text-5xl md:text-[66px] md:leading-[66px] lg:translate-x-[24px]">
          AI Interviewer for your
          <br />
          real technical{' '}
          <PaintHighlight anim="hero-paint" className="pl-3 pr-[2px] md:h-[66px] md:translate-y-[2px] md:leading-[66px]">
            growth
          </PaintHighlight>
          .
        </h1>

        <p data-anim="hero-text" className="mt-[14px] max-w-[600px] font-serif lg:translate-x-[9px] text-base leading-[1.32] text-ink sm:text-[19px] md:text-xl">
          Practice realistic, adaptive technical interviews tailored to your role, resume, and
          responses — then receive structured feedback that helps you improve.
        </p>

        <div
          data-anim="hero-cta"
          className="mt-5 flex w-full flex-col items-center justify-center gap-3 sm:w-auto sm:flex-row sm:flex-wrap sm:gap-[23px] lg:translate-x-[10px]"
        >
          <a
            href="#start-practicing"
            className="group inline-flex h-[51px] w-full max-w-[320px] items-center justify-center gap-[15px] rounded-[10px] bg-forest text-[15px] font-semibold tracking-[-0.005em] text-cream shadow-[inset_0_1px_0_rgb(255_255_255/0.12),0_1px_2px_rgb(20_42_11/0.3),0_8px_16px_-8px_rgb(20_42_11/0.5)] outline-offset-2 transition-[background-color,box-shadow,translate] duration-200 ease-out hover:-translate-y-0.5 hover:bg-forest-light hover:shadow-[inset_0_1px_0_rgb(255_255_255/0.18),0_2px_4px_rgb(20_42_11/0.3),0_14px_22px_-8px_rgb(20_42_11/0.6)] focus-visible:outline-[3px] focus-visible:outline-yellow active:translate-y-0 motion-reduce:transition-none motion-reduce:hover:translate-y-0 sm:w-auto sm:pl-[25px] sm:pr-[22px]"
          >
            Start Practicing Free
            <ArrowRight
              size={16}
              aria-hidden="true"
              className="transition-transform duration-200 ease-out group-hover:translate-x-[4px] motion-reduce:transition-none motion-reduce:group-hover:translate-x-0"
            />
          </a>

          <a
            href="#demo"
            className="group inline-flex h-[51px] w-full max-w-[320px] items-center justify-center gap-[14px] rounded-[10px] border-[1.5px] border-forest/75 bg-cream pl-[2px] pr-[22px] text-[15px] font-semibold tracking-[-0.005em] text-forest shadow-[0_1px_2px_rgb(20_42_11/0.06)] outline-offset-2 transition-[background-color,border-color] duration-200 ease-out hover:border-forest hover:bg-forest/[0.05] focus-visible:outline-2 focus-visible:outline-forest motion-reduce:transition-none sm:w-auto"
          >
            <span className="inline-flex h-[44px] w-[44px] items-center justify-center rounded-full border-[1.5px] border-forest/75 transition-colors duration-200 ease-out group-hover:border-forest group-hover:bg-forest group-hover:text-cream motion-reduce:transition-none">
              <Play
                size={17}
                fill="currentColor"
                aria-hidden="true"
                className="ml-0.5 transition-transform duration-200 ease-out group-hover:translate-x-[1px] motion-reduce:transition-none motion-reduce:group-hover:translate-x-0"
              />
            </span>
            Watch Demo
          </a>
        </div>

        <p data-anim="hero-trust" className="mt-[30px] text-xs font-medium text-ink lg:translate-x-[4px]">
          Built for realistic technical interview practice
        </p>

        <div data-anim="hero-image" className="mt-[22px] w-full rounded-[26px] bg-orange p-[14px] max-md:rounded-2xl max-md:p-2">
          <div className="relative aspect-[1026/268] w-full overflow-hidden rounded-[15px] max-md:aspect-[16/10] max-md:rounded-lg">
            <img
              src="/assets/landing/hero.png"
              alt="A software engineer speaking during a recorded interview practice session"
              className="absolute -left-[4%] -top-[15.7%] h-auto w-[118.1%] max-w-none max-md:left-[-16%] max-md:top-[-6%] max-md:w-[190%]"
            />
          </div>
        </div>
      </div>
    </section>
  )
}

export default Hero
