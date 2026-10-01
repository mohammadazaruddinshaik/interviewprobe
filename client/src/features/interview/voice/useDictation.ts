import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError } from '@/lib/api'
import { createLevelMeter, type LevelMeter } from './audioLevel'
import { grantSttToken } from './voiceApi'

export type DictationProblem = 'permission' | 'noDevice' | 'unsupported' | 'unavailable' | 'connection'

export type DictationState =
  | { status: 'idle' }
  | { status: 'connecting' }
  | { status: 'live' }
  | { status: 'finishing' }
  | { status: 'error'; problem: DictationProblem }

// Deepgram live transcription. The browser connects directly using the short-lived token from our backend
// (the `bearer` subprotocol is how Deepgram accepts a temporary token); no provider key exists in the client.
const DEEPGRAM_URL = 'wss://api.deepgram.com/v1/listen?model=nova-3&language=en&smart_format=true&interim_results=true'
const FINALIZE_TIMEOUT_MS = 2500

interface DeepgramResult {
  type?: string
  is_final?: boolean
  from_finalize?: boolean
  channel?: { alternatives?: { transcript?: string }[] }
}

const supported = () =>
  typeof navigator !== 'undefined' &&
  !!navigator.mediaDevices?.getUserMedia &&
  typeof MediaRecorder !== 'undefined' &&
  typeof WebSocket !== 'undefined'

function pickMimeType(): string | undefined {
  return ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4'].find((t) => MediaRecorder.isTypeSupported(t))
}

/**
 * Live speech-to-text for ONE answer. Recording runs until the candidate explicitly calls `finish()`:
 * silence or a pause in the transcript never ends an answer.
 */
export function useDictation() {
  const [state, setState] = useState<DictationState>({ status: 'idle' })
  const [finalText, setFinalText] = useState('')
  const [interim, setInterim] = useState('')

  const finalsRef = useRef<string[]>([])
  const interimRef = useRef('')
  const streamRef = useRef<MediaStream | null>(null)
  const recorderRef = useRef<MediaRecorder | null>(null)
  const socketRef = useRef<WebSocket | null>(null)
  const meterRef = useRef<LevelMeter | null>(null)
  const runRef = useRef(0)
  const onFinalizedRef = useRef<(() => void) | null>(null)

  const teardown = useCallback(() => {
    const recorder = recorderRef.current
    recorderRef.current = null
    if (recorder && recorder.state !== 'inactive') {
      recorder.ondataavailable = null
      try {
        recorder.stop()
      } catch {
        /* already stopped */
      }
    }
    streamRef.current?.getTracks().forEach((track) => track.stop()) // releases the microphone
    streamRef.current = null
    meterRef.current?.close()
    meterRef.current = null
    const socket = socketRef.current
    socketRef.current = null
    if (socket) {
      socket.onopen = socket.onmessage = socket.onerror = socket.onclose = null
      if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) socket.close()
    }
    onFinalizedRef.current = null
  }, [])

  const reset = useCallback(() => {
    finalsRef.current = []
    interimRef.current = ''
    setFinalText('')
    setInterim('')
  }, [])

  const cancel = useCallback(() => {
    runRef.current += 1
    teardown()
    reset()
    setState({ status: 'idle' })
  }, [reset, teardown])

  const fail = useCallback(
    (run: number, problem: DictationProblem) => {
      if (run !== runRef.current) return
      teardown()
      setState({ status: 'error', problem })
    },
    [teardown],
  )

  const start = useCallback(async () => {
    const run = ++runRef.current
    teardown()
    reset()
    if (!supported()) return setState({ status: 'error', problem: 'unsupported' })
    setState({ status: 'connecting' })

    let stream: MediaStream
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } })
    } catch (error) {
      const name = error instanceof DOMException ? error.name : ''
      return fail(run, name === 'NotFoundError' || name === 'OverconstrainedError' ? 'noDevice' : 'permission')
    }
    if (run !== runRef.current) return stream.getTracks().forEach((t) => t.stop())
    streamRef.current = stream
    meterRef.current = createLevelMeter(stream)

    let token: string
    try {
      token = (await grantSttToken()).access_token
    } catch (error) {
      return fail(run, error instanceof ApiError && error.status < 500 && !error.isNetworkError && error.status !== 429 ? 'unavailable' : 'connection')
    }
    if (run !== runRef.current) return

    const socket = new WebSocket(DEEPGRAM_URL, ['bearer', token])
    socketRef.current = socket
    socket.onopen = () => {
      if (run !== runRef.current) return
      const mimeType = pickMimeType()
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined)
      recorderRef.current = recorder
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0 && socket.readyState === WebSocket.OPEN) socket.send(event.data)
      }
      recorder.start(250)
      setState({ status: 'live' })
    }
    socket.onmessage = (event) => {
      if (run !== runRef.current || typeof event.data !== 'string') return
      let message: DeepgramResult
      try {
        message = JSON.parse(event.data) as DeepgramResult
      } catch {
        return
      }
      if (message.type !== 'Results') return
      const transcript = message.channel?.alternatives?.[0]?.transcript?.trim() ?? ''
      if (message.is_final) {
        if (transcript) finalsRef.current.push(transcript)
        interimRef.current = ''
        setFinalText(finalsRef.current.join(' '))
        setInterim('')
        if (message.from_finalize) onFinalizedRef.current?.()
      } else {
        interimRef.current = transcript
        setInterim(transcript)
      }
    }
    socket.onerror = () => fail(run, 'connection')
    socket.onclose = () => {
      // Closing while we still expect audio (not finishing, not cancelled) is a lost connection.
      if (run === runRef.current && socketRef.current === socket) fail(run, 'connection')
    }
  }, [fail, reset, teardown])

  /**
   * Ends the answer (manual Finish is the only way): flushes the last audio, asks Deepgram to finalize
   * what it has, releases the microphone and resolves with the complete transcript.
   */
  const finish = useCallback(async (): Promise<string> => {
    const run = runRef.current
    const socket = socketRef.current
    const recorder = recorderRef.current
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      const text = finalsRef.current.join(' ').trim()
      cancel()
      return text
    }
    setState({ status: 'finishing' })
    if (recorder && recorder.state !== 'inactive') {
      await new Promise<void>((resolve) => {
        recorder.onstop = () => resolve()
        recorder.stop()
      })
    }
    await new Promise<void>((resolve) => {
      const timer = window.setTimeout(resolve, FINALIZE_TIMEOUT_MS)
      onFinalizedRef.current = () => {
        window.clearTimeout(timer)
        resolve()
      }
      try {
        socket.send(JSON.stringify({ type: 'Finalize' }))
      } catch {
        window.clearTimeout(timer)
        resolve()
      }
    })
    if (run !== runRef.current) return finalsRef.current.join(' ').trim()
    const text = [...finalsRef.current, interimRef.current].filter(Boolean).join(' ').trim()
    try {
      socket.send(JSON.stringify({ type: 'CloseStream' }))
    } catch {
      /* closing anyway */
    }
    runRef.current += 1
    teardown()
    setState({ status: 'idle' })
    return text
  }, [cancel, teardown])

  useEffect(
    () => () => {
      runRef.current += 1
      teardown()
    },
    [teardown],
  )

  return { state, finalText, interim, start, finish, cancel, meter: meterRef }
}
