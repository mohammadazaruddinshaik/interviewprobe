import { useRef, useState } from 'react'
import { ApiError } from '../../api/client.js'
import { uploadResume } from '../../api/interviews.js'
import { ResumeIcon } from '../ui/interviewIcons.jsx'
import InterviewProbeLoader from '../ui/InterviewProbeLoader.jsx'

const ACCEPTED_EXTENSIONS = ['.pdf', '.docx']
const GENERIC_UPLOAD_ERROR = "Couldn't read this resume."

function hasAcceptedExtension(filename) {
  const lower = (filename || '').toLowerCase()
  return ACCEPTED_EXTENSIONS.some((ext) => lower.endsWith(ext))
}

// Resume upload — entirely optional, and never a second dashboard bolted
// onto Setup. Owns only its own small state machine (idle -> uploading ->
// ready|failed) and the file input; it never creates or knows about an
// interview session itself. `ensureSessionId` is provided by the parent
// (InterviewNew.jsx) — called only the first time the candidate actually
// picks a file, so a candidate who never touches this component never
// causes a session to be created early. Skipping is the default: simply
// never interacting with this component is already a complete, valid
// path (Step 13 — no upload request, no fake profile), so "Skip for now"
// just collapses this section rather than calling any API.
function ResumeUpload({ ensureSessionId }) {
  const [status, setStatus] = useState('idle') // 'idle' | 'uploading' | 'ready' | 'failed' | 'skipped'
  const [filename, setFilename] = useState('')
  const [errorMessage, setErrorMessage] = useState('')
  const [isDragOver, setIsDragOver] = useState(false)
  const inputRef = useRef(null)

  async function handleFile(file) {
    if (!file) return
    if (!hasAcceptedExtension(file.name)) {
      setFilename(file.name)
      setErrorMessage('Only PDF or DOCX files are supported.')
      setStatus('failed')
      return
    }

    setFilename(file.name)
    setStatus('uploading')
    setErrorMessage('')

    try {
      const sessionId = await ensureSessionId()
      const resume = await uploadResume(sessionId, file)
      if (resume.status === 'READY') {
        setStatus('ready')
      } else {
        setErrorMessage(resume.extraction_error || GENERIC_UPLOAD_ERROR)
        setStatus('failed')
      }
    } catch (error) {
      setErrorMessage(error instanceof ApiError ? error.message : GENERIC_UPLOAD_ERROR)
      setStatus('failed')
    }
  }

  function handleInputChange(event) {
    handleFile(event.target.files?.[0])
    event.target.value = ''
  }

  function handleDrop(event) {
    event.preventDefault()
    setIsDragOver(false)
    handleFile(event.dataTransfer.files?.[0])
  }

  function openFilePicker() {
    inputRef.current?.click()
  }

  function handleReplace() {
    setStatus('idle')
    setFilename('')
    setErrorMessage('')
    openFilePicker()
  }

  const hiddenInput = (
    <input
      ref={inputRef}
      type="file"
      accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
      onChange={handleInputChange}
      className="sr-only"
      aria-label="Upload your resume"
    />
  )

  if (status === 'skipped') {
    return (
      <div>
        <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted">Resume · Optional</p>
        <button
          type="button"
          onClick={() => setStatus('idle')}
          className="text-xs font-medium text-primary hover:underline"
        >
          Add a resume
        </button>
      </div>
    )
  }

  if (status === 'uploading') {
    return (
      <div>
        <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted">Resume · Optional</p>
        <div className="rounded-2xl border border-glass/70 bg-glass/40 px-4 py-5">
          <InterviewProbeLoader label="Reading your resume" size="sm" />
        </div>
      </div>
    )
  }

  if (status === 'ready') {
    return (
      <div>
        <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted">Resume · Optional</p>
        <div className="flex items-center gap-3 rounded-2xl border border-primary/25 bg-primary-light/60 px-4 py-3">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-glass text-primary">
            <ResumeIcon className="h-4.5 w-4.5" />
          </span>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold text-primary">Resume ready</p>
            <p className="truncate text-xs text-muted">{filename}</p>
          </div>
          <button
            type="button"
            onClick={handleReplace}
            className="shrink-0 text-xs font-medium text-muted underline-offset-2 hover:text-ink hover:underline"
          >
            Replace
          </button>
        </div>
        {hiddenInput}
      </div>
    )
  }

  if (status === 'failed') {
    return (
      <div>
        <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted">Resume · Optional</p>
        <div className="rounded-2xl border border-danger/30 bg-glass/60 px-4 py-3">
          <p className="text-sm font-semibold text-ink">{errorMessage || GENERIC_UPLOAD_ERROR}</p>
          <p className="mt-0.5 text-xs text-muted">Try another PDF or DOCX.</p>
          <div className="mt-2 flex items-center gap-3">
            <button
              type="button"
              onClick={handleReplace}
              className="text-xs font-medium text-primary hover:underline"
            >
              Replace resume
            </button>
            <button
              type="button"
              onClick={() => setStatus('skipped')}
              className="text-xs font-medium text-muted hover:text-ink"
            >
              Skip for now
            </button>
          </div>
        </div>
        {hiddenInput}
      </div>
    )
  }

  // 'idle' — the dropzone itself.
  return (
    <div>
      <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted">Resume · Optional</p>
      <button
        type="button"
        onClick={openFilePicker}
        onDragOver={(event) => {
          event.preventDefault()
          setIsDragOver(true)
        }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={handleDrop}
        className={`flex w-full flex-col items-center gap-1.5 rounded-2xl border border-dashed px-4 py-5 text-center transition-colors duration-150 ${
          isDragOver ? 'border-primary bg-primary-light/50' : 'border-line bg-glass/30 hover:border-primary/40'
        }`}
      >
        <ResumeIcon className="h-5 w-5 text-primary" />
        <span className="text-sm font-medium text-ink">Drop your resume here, or browse</span>
        <span className="text-xs text-muted">PDF or DOCX</span>
      </button>
      <button
        type="button"
        onClick={() => setStatus('skipped')}
        className="mt-2 text-xs font-medium text-muted hover:text-ink"
      >
        Skip for now
      </button>
      {hiddenInput}
    </div>
  )
}

export default ResumeUpload
