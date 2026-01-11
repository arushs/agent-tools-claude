import { ref, onUnmounted } from 'vue'
import { useChatStore } from '../stores/chat'
import { useAppointmentsStore } from '../stores/appointments'
import { useDebugStore } from '../stores/debug'
import type { WebSocketMessage, ChatMessage, Appointment } from '../types'

export function useAdminWebSocket() {
  const ws = ref<WebSocket | null>(null)
  const connected = ref(false)
  const reconnectAttempts = ref(0)
  const maxReconnectAttempts = 5

  const chatStore = useChatStore()
  const appointmentsStore = useAppointmentsStore()
  const debugStore = useDebugStore()

  let reconnectTimeout: ReturnType<typeof setTimeout> | null = null

  function connect() {
    if (ws.value?.readyState === WebSocket.OPEN) {
      return
    }

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
      debugStore.recordConnect()
      debugStore.resetReconnectAttempts()
    }

    ws.value.onclose = () => {
      connected.value = false
      attemptReconnect()
    }

    ws.value.onerror = () => {
      connected.value = false
    }

    ws.value.onmessage = (event) => {
      // Log to debug store
      debugStore.logReceived(event.data)

      try {
        const data: WebSocketMessage = JSON.parse(event.data)
        handleMessage(data)
      } catch {
        console.error('Failed to parse WebSocket message')
      }
    }
  }

  function handleMessage(data: WebSocketMessage) {
    switch (data.type) {
      case 'connected':
        chatStore.setSessionId(data.session_id as string)
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
        chatStore.addMessage({
          role: 'assistant',
          content: `Error: ${data.message}`,
        })
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
      const payload = JSON.stringify({ type: 'message', content })
      debugStore.logSent(payload)
      ws.value.send(payload)
    }
  }

  function clearHistory() {
    if (ws.value?.readyState === WebSocket.OPEN) {
      const payload = JSON.stringify({ type: 'clear_history' })
      debugStore.logSent(payload)
      ws.value.send(payload)
    }
  }

  function sendPing() {
    if (ws.value?.readyState === WebSocket.OPEN) {
      const payload = JSON.stringify({ type: 'ping' })
      debugStore.logSent(payload)
      ws.value.send(payload)
    }
  }

  function attemptReconnect() {
    if (reconnectAttempts.value >= maxReconnectAttempts) {
      return
    }

    reconnectAttempts.value++
    debugStore.recordReconnectAttempt()
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
    reconnectAttempts,
    connect,
    disconnect,
    sendMessage,
    clearHistory,
    sendPing,
  }
}
