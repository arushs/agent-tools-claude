export interface Appointment {
  id: string
  title: string
  start: string
  end: string
  attendees: string[]
  description?: string
  location?: string
  status?: 'confirmed' | 'cancelled' | 'pending'
}

export interface TimeSlot {
  start: string
  end: string
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp?: string
}

export interface WebSocketMessage {
  type: string
  [key: string]: unknown
}

export interface ConnectedMessage extends WebSocketMessage {
  type: 'connected'
  session_id: string
}

export interface ResponseMessage extends WebSocketMessage {
  type: 'response'
  content: string
  appointments_changed: boolean
}

export interface NotificationMessage extends WebSocketMessage {
  type: 'notification'
  event: string
  data: Record<string, unknown>
}

// Voice-related types
export type VoiceState = 'idle' | 'recording' | 'transcribing' | 'thinking' | 'synthesizing' | 'playing'

export type Voice = 'alloy' | 'echo' | 'fable' | 'onyx' | 'nova' | 'shimmer'

export interface VoiceConnectedMessage extends WebSocketMessage {
  type: 'connected'
  session_id: string
  voices: Voice[]
}

export interface VoiceProcessingMessage extends WebSocketMessage {
  type: 'processing'
  stage: 'transcribing' | 'thinking' | 'synthesizing'
}

export interface VoiceTranscriptionMessage extends WebSocketMessage {
  type: 'transcription'
  text: string
}

export interface VoiceResponseMessage extends WebSocketMessage {
  type: 'response'
  transcription: string
  text: string
  audio: string
  mime_type: string
  appointments_changed: boolean
  error?: string
}

export interface VoiceAudioMessage extends WebSocketMessage {
  type: 'audio'
  data: string
  mime_type: string
}

// Debug types
export interface DebugMessage {
  id: string
  timestamp: string
  direction: 'sent' | 'received'
  type: string
  data: unknown
  rawData: string
}
