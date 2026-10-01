import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError } from '@/lib/api'
import { createLevelMeter, type LevelMeter } from './audioLevel'
import { synthesizeSpeech } from './voiceApi'

export type SpeechState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'playing' }
  | { status: 'ended' }
  | { status: 'blocked' } // the browser refused autoplay: needs a tap
  | { status: 'error'; message: string }

function describeTtsFailure(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 429) return 'Voice is catching its breath. Try again in a moment.'
    if (error.isNetworkError) return 'We couldn’t reach the voice service. Check your connection.'
  }
  return 'We couldn’t play the interviewer’s voice.'
}

/** Plays interviewer speech from the backend's TTS endpoint. One utterance at a time; always cleans up. */
export function useSpeech() {
  const [state, setState] = useState<SpeechState>({ status: 'idle' })
  const [finished, setFinished] = useState(0) // counts completed utterances (an event, unlike the sticky 'ended' status)
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const urlRef = useRef<string | null>(null)
  const meterRef = useRef<LevelMeter | null>(null)
  const runRef = useRef(0) // invalidates an in-flight speak() when a newer one (or stop) starts
  const cacheRef = useRef<{ text: string; blob: Blob } | null>(null) // replay without another TTS request

  const release = useCallback(() => {
    meterRef.current?.close()
    meterRef.current = null
    const audio = audioRef.current
    if (audio) {
      audio.onended = null
      audio.onerror = null
      audio.pause()
      audio.removeAttribute('src')
      audio.load()
    }
    audioRef.current = null
    if (urlRef.current) URL.revokeObjectURL(urlRef.current)
    urlRef.current = null
  }, [])

  const stop = useCallback(() => {
    runRef.current += 1
    release()
    setState((s) => (s.status === 'loading' || s.status === 'playing' ? { status: 'idle' } : s))
  }, [release])

  const speak = useCallback(
    async (text: string) => {
      const run = ++runRef.current
      release()
      setState({ status: 'loading' })
      try {
        let blob = cacheRef.current?.text === text ? cacheRef.current.blob : null
        if (!blob) {
          blob = await synthesizeSpeech(text)
          if (run !== runRef.current) return
          cacheRef.current = { text, blob }
        }
        const audio = new Audio()
        const url = URL.createObjectURL(blob)
        audioRef.current = audio
        urlRef.current = url
        audio.src = url
        audio.onended = () => {
          if (run !== runRef.current) return
          setState({ status: 'ended' })
          setFinished((n) => n + 1)
        }
        audio.onerror = () => {
          if (run === runRef.current) setState({ status: 'error', message: 'We couldn’t play the interviewer’s voice.' })
        }
        meterRef.current = createLevelMeter(audio)
        await audio.play()
        if (run === runRef.current) setState({ status: 'playing' })
      } catch (error) {
        if (run !== runRef.current) return
        release()
        if (error instanceof DOMException && error.name === 'NotAllowedError') setState({ status: 'blocked' })
        else setState({ status: 'error', message: describeTtsFailure(error) })
      }
    },
    [release],
  )

  useEffect(
    () => () => {
      runRef.current += 1
      release()
    },
    [release],
  )

  return { state, finished, speak, stop, meter: meterRef }
}
