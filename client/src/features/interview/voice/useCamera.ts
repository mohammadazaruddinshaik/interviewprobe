import { useCallback, useEffect, useRef, useState } from 'react'

export type CameraState =
  | { status: 'off' }
  | { status: 'starting' }
  | { status: 'on'; stream: MediaStream }
  | { status: 'error'; problem: 'permission' | 'noDevice' | 'inUse' | 'unsupported' }

/** Optional, LOCAL-ONLY camera preview. The stream is only ever attached to a <video>; nothing is sent or stored. */
export function useCamera() {
  const [state, setState] = useState<CameraState>({ status: 'off' })
  const streamRef = useRef<MediaStream | null>(null)
  const runRef = useRef(0)

  const stop = useCallback(() => {
    runRef.current += 1
    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null
    setState({ status: 'off' })
  }, [])

  const start = useCallback(async () => {
    if (!navigator.mediaDevices?.getUserMedia) return setState({ status: 'error', problem: 'unsupported' })
    const run = ++runRef.current
    setState({ status: 'starting' })
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' }, audio: false })
      if (run !== runRef.current) return stream.getTracks().forEach((t) => t.stop())
      streamRef.current = stream
      setState({ status: 'on', stream })
    } catch (error) {
      if (run !== runRef.current) return
      const name = error instanceof DOMException ? error.name : ''
      const problem = name === 'NotFoundError' || name === 'OverconstrainedError' ? 'noDevice' : name === 'NotReadableError' ? 'inUse' : 'permission'
      setState({ status: 'error', problem })
    }
  }, [])

  useEffect(
    () => () => {
      runRef.current += 1
      streamRef.current?.getTracks().forEach((track) => track.stop())
      streamRef.current = null
    },
    [],
  )

  return { state, start, stop }
}
