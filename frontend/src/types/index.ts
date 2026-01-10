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
