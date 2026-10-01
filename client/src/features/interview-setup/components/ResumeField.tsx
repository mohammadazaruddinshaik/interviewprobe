import { useRef } from 'react'
import { formatFileSize, RESUME_ACCEPT } from '../lib/resumeFile'

interface ResumeFieldProps {
  file: File | null
  error: string | null
  onChange: (file: File | null) => void
  disabled: boolean
}

const button =
  'rounded-xl border border-forest/30 bg-cream px-5 py-2.5 text-[14px] font-semibold text-forest outline-offset-[3px] transition-colors duration-200 hover:bg-forest/[0.05] focus-visible:outline-[3px] focus-visible:outline-yellow disabled:cursor-not-allowed disabled:opacity-50 motion-reduce:transition-none'

/** Optional resume: one quiet button, then a single filename row. Validation is client-side; upload happens on Start. */
function ResumeField({ file, error, onChange, disabled }: ResumeFieldProps) {
  const input = useRef<HTMLInputElement>(null)

  return (
    <div>
      <input
        ref={input}
        type="file"
        accept={RESUME_ACCEPT}
        aria-label="Resume file"
        className="sr-only"
        tabIndex={-1}
        onChange={(e) => {
          onChange(e.target.files?.[0] ?? null)
          e.target.value = '' // allow choosing the same file again after removing it
        }}
      />
      {file ? (
        <div className="flex items-center justify-between gap-4 rounded-xl border border-ink/12 bg-white/55 px-4 py-3">
          <div className="min-w-0">
            <p className="truncate text-[14.5px] font-semibold text-deep">{file.name}</p>
            <p className="mt-0.5 text-[12.5px] text-ink/55">{formatFileSize(file.size)}</p>
          </div>
          <button
            type="button"
            onClick={() => onChange(null)}
            disabled={disabled}
            className="shrink-0 rounded-lg px-1.5 py-1 text-[13px] font-semibold text-forest outline-offset-2 hover:underline focus-visible:outline-[3px] focus-visible:outline-yellow disabled:opacity-50"
          >
            Remove
          </button>
        </div>
      ) : (
        <button type="button" onClick={() => input.current?.click()} disabled={disabled} className={button}>
          Upload resume
        </button>
      )}
      <p role="alert" className="mt-2 min-h-[18px] text-[12.5px] text-orange">
        {error}
      </p>
    </div>
  )
}

export default ResumeField
