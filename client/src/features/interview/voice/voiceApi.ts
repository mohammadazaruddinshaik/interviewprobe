import { apiRequest, apiRequestBlob } from '@/lib/api'

/** POST /voice/tts -> MP3 audio. The backend owns the Azure voice and credentials; only `default` is accepted. */
export const synthesizeSpeech = (text: string) =>
  apiRequestBlob('/voice/tts', { method: 'POST', body: JSON.stringify({ text, voice: 'default' }) })

export interface SttToken {
  access_token: string
  expires_in: number
}

/** POST /voice/stt/token -> a short-lived Deepgram token. The permanent key never leaves the backend. */
export const grantSttToken = () => apiRequest<SttToken>('/voice/stt/token', { method: 'POST' })
