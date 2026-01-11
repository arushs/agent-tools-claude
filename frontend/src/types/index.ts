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

// Error types - matches backend exception structure
export type ErrorCode =
  | 'AGENT_ERROR'
  | 'VALIDATION_ERROR'
  | 'NOT_FOUND'
  | 'CONFLICT'
  | 'SERVICE_UNAVAILABLE'
  | 'CALENDAR_ERROR'
  | 'CALENDAR_AUTH_ERROR'
  | 'CALENDAR_API_ERROR'
  | 'SCHEDULING_CONFLICT'
  | 'VOICE_ERROR'
  | 'TRANSCRIPTION_ERROR'
  | 'SYNTHESIS_ERROR'
  | 'AUDIO_PROCESSING_ERROR'
  | 'TOOL_ERROR'
  | 'TOOL_NOT_FOUND'
  | 'TOOL_EXECUTION_ERROR'
  | 'TOOL_VALIDATION_ERROR'
  | 'WEBSOCKET_ERROR'
  | 'WEBSOCKET_MESSAGE_ERROR'
  | 'INTERNAL_ERROR'

export interface ApiError {
  error: ErrorCode
  message: string
  details: Record<string, unknown>
}

export interface ErrorMessage extends WebSocketMessage {
  type: 'error'
  error_code: ErrorCode
  message: string
  details: Record<string, unknown>
}

// Helper function to check if a response is an API error
export function isApiError(data: unknown): data is ApiError {
  return (
    typeof data === 'object' &&
    data !== null &&
    'error' in data &&
    'message' in data
  )
}

// Helper function to get a user-friendly error message
export function getUserFriendlyErrorMessage(error: ApiError | ErrorMessage): string {
  const errorCode = 'error_code' in error ? error.error_code : error.error

  switch (errorCode) {
    case 'VALIDATION_ERROR':
      return `Invalid input: ${error.message}`
    case 'NOT_FOUND':
      return error.message
    case 'CALENDAR_AUTH_ERROR':
      return 'Calendar authentication failed. Please reconnect your calendar.'
    case 'CALENDAR_API_ERROR':
      return 'Unable to connect to calendar service. Please try again.'
    case 'SCHEDULING_CONFLICT':
      return 'This time slot conflicts with an existing appointment.'
    case 'TRANSCRIPTION_ERROR':
      return 'Unable to transcribe audio. Please try speaking again.'
    case 'SYNTHESIS_ERROR':
      return 'Unable to generate audio response. Please try again.'
    case 'SERVICE_UNAVAILABLE':
      return 'Service temporarily unavailable. Please try again later.'
    case 'INTERNAL_ERROR':
    default:
      return 'An unexpected error occurred. Please try again.'
  }
}
