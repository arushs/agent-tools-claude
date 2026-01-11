import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { DebugMessage } from '../types'

export const useDebugStore = defineStore('debug', () => {
  const messages = ref<DebugMessage[]>([])
  const maxMessages = 100
  const connectionState = ref<'disconnected' | 'connecting' | 'connected'>('disconnected')
  const sessionId = ref<string | null>(null)
  const reconnectAttempts = ref(0)
  const lastError = ref<string | null>(null)

  const sentCount = computed(() => messages.value.filter(m => m.direction === 'sent').length)
  const receivedCount = computed(() => messages.value.filter(m => m.direction === 'received').length)

  function addMessage(direction: 'sent' | 'received', type: string, data: unknown, rawData: string) {
    const message: DebugMessage = {
      id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      timestamp: new Date().toISOString(),
      direction,
      type,
      data,
      rawData
    }
    messages.value.push(message)

    // Keep only the last maxMessages
    if (messages.value.length > maxMessages) {
      messages.value = messages.value.slice(-maxMessages)
    }
  }

  function setConnectionState(state: 'disconnected' | 'connecting' | 'connected') {
    connectionState.value = state
  }

  function setSessionId(id: string | null) {
    sessionId.value = id
  }

  function setReconnectAttempts(attempts: number) {
    reconnectAttempts.value = attempts
  }

  function setLastError(error: string | null) {
    lastError.value = error
  }

  function clearMessages() {
    messages.value = []
  }

  function reset() {
    messages.value = []
    connectionState.value = 'disconnected'
    sessionId.value = null
    reconnectAttempts.value = 0
    lastError.value = null
  }

  return {
    messages,
    connectionState,
    sessionId,
    reconnectAttempts,
    lastError,
    sentCount,
    receivedCount,
    addMessage,
    setConnectionState,
    setSessionId,
    setReconnectAttempts,
    setLastError,
    clearMessages,
    reset
  }
})
