import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { ChatMessage } from '../types'

export const useChatStore = defineStore('chat', () => {
  const messages = ref<ChatMessage[]>([])
  const sessionId = ref<string | null>(null)
  const isProcessing = ref(false)

  function setSessionId(id: string) {
    sessionId.value = id
  }

  function addMessage(message: ChatMessage) {
    messages.value.push(message)
  }

  function setHistory(history: ChatMessage[]) {
    messages.value = history
  }

  function clearMessages() {
    messages.value = []
  }

  function setProcessing(value: boolean) {
    isProcessing.value = value
  }

  return {
    messages,
    sessionId,
    isProcessing,
    setSessionId,
    addMessage,
    setHistory,
    clearMessages,
    setProcessing,
  }
})
