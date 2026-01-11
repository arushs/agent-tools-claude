import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface DebugMessage {
  id: number
  direction: 'sent' | 'received'
  type: string
  data: unknown
  timestamp: Date
  raw: string
}

export interface ConnectionStats {
  connectTime: Date | null
  reconnectAttempts: number
  messagesReceived: number
  messagesSent: number
  lastMessageTime: Date | null
}

export const useDebugStore = defineStore('debug', () => {
  const messages = ref<DebugMessage[]>([])
  const connectionStats = ref<ConnectionStats>({
    connectTime: null,
    reconnectAttempts: 0,
    messagesReceived: 0,
    messagesSent: 0,
    lastMessageTime: null
  })

  let nextId = 1
  const maxMessages = 200

  function logMessage(direction: 'sent' | 'received', raw: string) {
    let type = 'unknown'
    let data: unknown = raw

    try {
      const parsed = JSON.parse(raw)
      type = parsed.type || 'unknown'
      data = parsed
    } catch {
      // Keep raw string if not valid JSON
    }

    const message: DebugMessage = {
      id: nextId++,
      direction,
      type,
      data,
      timestamp: new Date(),
      raw
    }

    messages.value.push(message)

    // Trim old messages
    if (messages.value.length > maxMessages) {
      messages.value = messages.value.slice(-maxMessages)
    }

    if (direction === 'sent') {
      connectionStats.value.messagesSent++
    } else {
      connectionStats.value.messagesReceived++
    }
    connectionStats.value.lastMessageTime = new Date()
  }

  function logSent(data: string) {
    logMessage('sent', data)
  }

  function logReceived(data: string) {
    logMessage('received', data)
  }

  function recordConnect() {
    connectionStats.value.connectTime = new Date()
  }

  function recordReconnectAttempt() {
    connectionStats.value.reconnectAttempts++
  }

  function resetReconnectAttempts() {
    connectionStats.value.reconnectAttempts = 0
  }

  function clearMessages() {
    messages.value = []
  }

  function resetStats() {
    connectionStats.value = {
      connectTime: null,
      reconnectAttempts: 0,
      messagesReceived: 0,
      messagesSent: 0,
      lastMessageTime: null
    }
  }

  const recentMessages = computed(() => messages.value.slice(-50))

  const sentMessages = computed(() =>
    messages.value.filter(m => m.direction === 'sent')
  )

  const receivedMessages = computed(() =>
    messages.value.filter(m => m.direction === 'received')
  )

  return {
    messages,
    connectionStats,
    recentMessages,
    sentMessages,
    receivedMessages,
    logSent,
    logReceived,
    recordConnect,
    recordReconnectAttempt,
    resetReconnectAttempts,
    clearMessages,
    resetStats
  }
})
