import { useCallback, useEffect, useRef, useState } from 'react'

// The candidate's optional, purely visual self-view — entirely isolated
// from the voice architecture. This never touches useVoiceInterviewSession,
// the voice reducer, or any speech provider: it opens its own separate
// getUserMedia video-only stream (`audio: false`, explicitly — the
// candidate's actual answer audio still only ever goes through the
// existing Deepgram STT pipeline). Camera permission is never requested
// automatically and is never required; every failure mode (denied,
// unavailable, no camera hardware) just falls back to `state !== 'on'`,
// which callers render as the existing static placeholder — voice keeps
// working exactly as before regardless.
export function useCandidateCamera() {
  // 'off' | 'requesting' | 'on' | 'denied' | 'unavailable'
  const [state, setState] = useState('off')
  const streamRef = useRef(null)
  const videoRef = useRef(null)

  const attachStream = useCallback((stream) => {
    streamRef.current = stream
    if (videoRef.current) {
      videoRef.current.srcObject = stream
    }
  }, [])

  const stopTracks = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null
  }, [])

  const stop = useCallback(() => {
    stopTracks()
    setState('off')
  }, [stopTracks])

  const start = useCallback(async () => {
    if (typeof navigator === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
      setState('unavailable')
      return
    }
    setState('requesting')
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false })
      attachStream(stream)
      setState('on')
    } catch {
      // Denied, no device, already in use elsewhere, etc. — all read the
      // same to the candidate: the camera just isn't available right now.
      setState('denied')
    }
  }, [attachStream])

  const toggle = useCallback(() => {
    if (state === 'on') {
      stop()
    } else {
      start()
    }
  }, [state, start, stop])

  // A freshly mounted <video> (e.g. after a re-render) still needs the
  // already-open stream attached to it.
  useEffect(() => {
    if (state === 'on' && streamRef.current && videoRef.current) {
      videoRef.current.srcObject = streamRef.current
    }
  }, [state])

  // Release the camera on unmount (leaving the room) regardless of state.
  useEffect(() => () => stopTracks(), [stopTracks])

  return { state, videoRef, start, stop, toggle }
}
