import { ref, onUnmounted } from 'vue'
import { useChatStore } from '../stores/chat'
import { useAppointmentsStore } from '../stores/appointments'
import { useDebugStore } from '../stores/debug'
import type { WebSocketMessage, ChatMessage, Appointment, ErrorMessage } from '../types'
import { getUserFriendlyErrorMessage } from '../types'

interface UseWebSocketOptions {
  enableDebug?: boolean
}

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const { enableDebug = false } = options

  const ws = ref<WebSocket | null>(null)
  const connected = ref(false)
  const reconnectAttempts = ref(0)
  const maxReconnectAttempts = 5

  const chatStore = useChatStore()
  const appointmentsStore = useAppointmentsStore()
  const debugStore = enableDebug ? useDebugStore() : null

  let reconnectTimeout: ReturnType<typeof setTimeout> | null = null

  function connect() {
    if (ws.value?.readyState === WebSocket.OPEN) {
      return
    }

    debugStore?.setConnectionState('connecting')

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const sessionId = chatStore.sessionId
    const url = sessionId
      ? `${protocol}//${host}/ws/chat?session_id=${sessionId}`
      : `${protocol}//${host}/ws/chat`

    ws.value = new WebSocket(url)

    ws.value.onopen = () => {
      connected.value = true
      reconnectAttempts.value = 0
      debugStore?.setConnectionState('connected')
      debugStore?.setReconnectAttempts(0)
    }

    ws.value.onclose = () => {
      connected.value = false
      debugStore?.setConnectionState('disconnected')
      attemptReconnect()
    }

    ws.value.onerror = (_event) => {
      connected.value = false
      debugStore?.setConnectionState('disconnected')
      debugStore?.setLastError('WebSocket connection error')
    }

    ws.value.onmessage = (event) => {
      const rawData = event.data as string
      try {
        const data: WebSocketMessage = JSON.parse(rawData)
        debugStore?.addMessage('received', data.type, data, rawData)
        handleMessage(data)
      } catch {
        console.error('Failed to parse WebSocket message')
        debugStore?.setLastError('Failed to parse WebSocket message')
      }
    }
  }

  function handleMessage(data: WebSocketMessage) {
    switch (data.type) {
      case 'connected':
        chatStore.setSessionId(data.session_id as string)
        debugStore?.setSessionId(data.session_id as string)
        break

      case 'history':
        chatStore.setHistory(data.messages as ChatMessage[])
        break

      case 'ack':
        chatStore.setProcessing(true)
        break

      case 'response':
        chatStore.setProcessing(false)
        chatStore.addMessage({
          role: 'assistant',
          content: data.content as string,
        })
        if (data.appointments_changed) {
          appointmentsStore.fetchAppointments()
        }
        break

      case 'error':
        chatStore.setProcessing(false)
        // Handle structured error messages from the new error handling system
        const errorData = data as ErrorMessage
        const errorMessage = errorData.error_code
          ? getUserFriendlyErrorMessage(errorData)
          : String(data.message || 'An error occurred')
        chatStore.addMessage({
          role: 'assistant',
          content: `Error: ${errorMessage}`,
        })
        debugStore?.setLastError(errorMessage)
        break

      case 'notification':
        handleNotification(data)
        break

      case 'history_cleared':
        chatStore.clearMessages()
        break

      case 'pong':
        // Heartbeat response, no action needed
        break
    }
  }

  function handleNotification(data: WebSocketMessage) {
    const event = data.event as string
    const eventData = data.data as Record<string, unknown>

    switch (event) {
      case 'appointment_created':
        appointmentsStore.handleAppointmentCreated(eventData as unknown as Appointment)
        break

      case 'appointment_cancelled':
        appointmentsStore.handleAppointmentCancelled(eventData as { id: string })
        break

      case 'appointments_changed':
        appointmentsStore.handleAppointmentsChanged()
        break
    }
  }

  function sendMessage(content: string) {
    if (ws.value?.readyState === WebSocket.OPEN) {
      chatStore.addMessage({ role: 'user', content })
      const payload = { type: 'message', content }
      const rawData = JSON.stringify(payload)
      debugStore?.addMessage('sent', 'message', payload, rawData)
      ws.value.send(rawData)
    }
  }

  function clearHistory() {
    if (ws.value?.readyState === WebSocket.OPEN) {
      const payload = { type: 'clear_history' }
      const rawData = JSON.stringify(payload)
      debugStore?.addMessage('sent', 'clear_history', payload, rawData)
      ws.value.send(rawData)
    }
  }

  function attemptReconnect() {
    if (reconnectAttempts.value >= maxReconnectAttempts) {
      debugStore?.setLastError(`Max reconnection attempts (${maxReconnectAttempts}) reached`)
      return
    }

    reconnectAttempts.value++
    debugStore?.setReconnectAttempts(reconnectAttempts.value)
    const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.value), 30000)

    reconnectTimeout = setTimeout(() => {
      connect()
    }, delay)
  }

  function disconnect() {
    if (reconnectTimeout) {
      clearTimeout(reconnectTimeout)
    }
    if (ws.value) {
      ws.value.close()
      ws.value = null
    }
    connected.value = false
  }

  onUnmounted(() => {
    disconnect()
  })

  return {
    connected,
    connect,
    disconnect,
    sendMessage,
    clearHistory,
  }
}
