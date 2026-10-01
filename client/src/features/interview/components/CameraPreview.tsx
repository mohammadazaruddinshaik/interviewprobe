import { useEffect, useRef, useState } from 'react'
import { Camera, CameraOff, ChevronDown, ChevronUp } from 'lucide-react'
import type { CameraState } from '../voice/useCamera'

interface CameraPreviewProps {
  state: CameraState
  onStart: () => void
  onStop: () => void
}

const PROBLEMS: Record<string, string> = {
  permission: 'Camera access was blocked. You can allow it in your browser’s site settings, or carry on without it.',
  noDevice: 'No camera was found. Your interview works fine without one.',
  inUse: 'Your camera is being used by another app. Close it and try again, or carry on without it.',
  unsupported: 'This browser can’t show a camera preview. Your interview works fine without one.',
}

const button =
  'inline-flex min-h-9 items-center gap-1.5 rounded-lg px-2.5 text-[12.5px] font-semibold text-cream outline-offset-2 transition-colors hover:bg-cream/10 focus-visible:outline-[3px] focus-visible:outline-yellow motion-reduce:transition-none'

/** Optional, local-only self view. Nothing from the camera leaves this component's <video>. */
function CameraPreview({ state, onStart, onStop }: CameraPreviewProps) {
  const video = useRef<HTMLVideoElement>(null)
  const [minimized, setMinimized] = useState(false)
  const stream = state.status === 'on' ? state.stream : null

  useEffect(() => {
    const el = video.current
    if (!el) return
    el.srcObject = stream
    return () => {
      el.srcObject = null
    }
  }, [stream, minimized])

  return (
    <aside
      aria-label="Your camera preview (local only)"
      className={`fixed bottom-[112px] right-4 z-20 w-[132px] overflow-hidden rounded-2xl border border-cream/15 bg-[#0b1a10]/85 text-cream shadow-[0_16px_40px_-18px_rgb(0_0_0/0.7)] backdrop-blur-md xl:bottom-4 xl:w-[220px] ${stream ? '' : 'max-xl:w-auto'}`}
    >
      {stream && !minimized && (
        <video ref={video} autoPlay playsInline muted aria-label="Your camera" className="aspect-[4/3] w-full -scale-x-100 bg-ink object-cover" />
      )}

      {!stream && (
        <div className={`p-3 ${state.status === 'error' ? '' : 'max-xl:p-1'}`}>
          <p className={`flex items-center gap-1.5 text-[12.5px] font-semibold text-cream ${state.status === 'error' ? '' : 'max-xl:hidden'}`}>
            <CameraOff size={14} aria-hidden="true" /> Camera off
          </p>
          <p className={`mt-1 text-[12px] leading-snug text-cream/60 ${state.status === 'error' ? '' : 'max-xl:hidden'}`}>
            {state.status === 'error'
              ? PROBLEMS[state.problem]
              : 'Turn on your camera to make this feel more like a real interview. It stays on your device — never recorded or sent.'}
          </p>
          <button
            type="button"
            onClick={onStart}
            disabled={state.status === 'starting'}
            title="Turn on camera. It stays on your device — never recorded or sent."
            className={`${button} mt-2 -ml-2.5 ${state.status === 'error' ? '' : 'max-xl:m-0 max-xl:min-h-11 max-xl:min-w-11 max-xl:justify-center'}`}
          >
            <Camera size={14} aria-hidden="true" />
            <span className={state.status === 'error' ? '' : 'max-xl:sr-only'}>
              {state.status === 'starting' ? 'Starting…' : state.status === 'error' ? 'Try again' : 'Turn on camera'}
            </span>
          </button>
        </div>
      )}

      {stream && (
        <div className="flex items-center justify-between gap-1 border-t border-cream/10 px-1.5 py-0.5">
          <button type="button" onClick={onStop} className={button} aria-label="Turn camera off">
            <CameraOff size={14} aria-hidden="true" /> Off
          </button>
          <button
            type="button"
            onClick={() => setMinimized((m) => !m)}
            className={button}
            aria-expanded={!minimized}
            aria-label={minimized ? 'Show camera preview' : 'Minimize camera preview'}
          >
            {minimized ? <ChevronUp size={14} aria-hidden="true" /> : <ChevronDown size={14} aria-hidden="true" />}
            {minimized ? 'Show' : 'Hide'}
          </button>
        </div>
      )}
    </aside>
  )
}

export default CameraPreview
