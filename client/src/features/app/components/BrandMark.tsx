import { hideOnError } from '@/lib/image'

/** The InterviewProbe logo, cropped from the shared brand image exactly as the rest of the app does. */
function BrandMark({ className = '' }: { className?: string }) {
  return (
    <span className={`relative block h-[36px] w-[180px] overflow-hidden ${className}`}>
      <img src="/assets/landing/logo-510.webp" alt="InterviewProbe" width={510} height={190} decoding="async" onError={hideOnError} className="absolute -left-[29px] -top-[25px] h-[87px] w-[234px] max-w-none" />
    </span>
  )
}

export default BrandMark
