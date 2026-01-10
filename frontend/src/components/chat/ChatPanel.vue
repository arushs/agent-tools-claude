<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { useChatStore } from '../../stores/chat'
import { useWebSocket } from '../../composables/useWebSocket'

const chatStore = useChatStore()
const { connected, connect, sendMessage, clearHistory } = useWebSocket()

const inputMessage = ref('')
const messagesContainer = ref<HTMLElement | null>(null)

const messages = computed(() => chatStore.messages)
const isProcessing = computed(() => chatStore.isProcessing)

// Connect on mount
connect()

// Auto-scroll to bottom when new messages arrive
watch(
  () => messages.value.length,
  async () => {
    await nextTick()
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  }
)

function handleSend() {
  const message = inputMessage.value.trim()
  if (message && !isProcessing.value) {
    sendMessage(message)
    inputMessage.value = ''
  }
}

function handleKeyDown(event: KeyboardEvent) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    handleSend()
  }
}

function handleClear() {
  if (confirm('Clear chat history?')) {
    clearHistory()
  }
}
</script>

<template>
  <div class="bg-white rounded-lg shadow h-full flex flex-col">
    <!-- Header -->
    <div class="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
      <div class="flex items-center gap-2">
        <h2 class="text-lg font-semibold text-gray-900">Chat with AI</h2>
        <span
          :class="[
            'w-2 h-2 rounded-full',
            connected ? 'bg-green-500' : 'bg-red-500'
          ]"
          :title="connected ? 'Connected' : 'Disconnected'"
        ></span>
      </div>
      <button
        class="text-sm text-gray-500 hover:text-gray-700 transition-colors"
        @click="handleClear"
      >
        Clear
      </button>
    </div>

    <!-- Messages -->
    <div ref="messagesContainer" class="flex-1 overflow-y-auto p-4 space-y-4 chat-messages">
      <div v-if="messages.length === 0" class="text-center text-gray-500 py-8">
        <p class="mb-2">Welcome! I can help you manage your calendar.</p>
        <p class="text-sm">Try asking:</p>
        <ul class="text-sm mt-2 space-y-1">
          <li>"What's on my schedule today?"</li>
          <li>"Book a meeting tomorrow at 2pm"</li>
          <li>"When am I free this week?"</li>
        </ul>
      </div>

      <div
        v-for="(msg, index) in messages"
        :key="index"
        :class="[
          'flex',
          msg.role === 'user' ? 'justify-end' : 'justify-start'
        ]"
      >
        <div
          :class="[
            'max-w-[80%] rounded-lg px-4 py-2',
            msg.role === 'user'
              ? 'bg-blue-600 text-white'
              : 'bg-gray-100 text-gray-900'
          ]"
        >
          <p class="whitespace-pre-wrap">{{ msg.content }}</p>
        </div>
      </div>

      <!-- Typing indicator -->
      <div v-if="isProcessing" class="flex justify-start">
        <div class="bg-gray-100 rounded-lg px-4 py-2">
          <div class="flex space-x-1">
            <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0ms"></div>
            <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 150ms"></div>
            <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 300ms"></div>
          </div>
        </div>
      </div>
    </div>

    <!-- Input -->
    <div class="px-4 py-3 border-t border-gray-200">
      <div class="flex gap-2">
        <input
          v-model="inputMessage"
          type="text"
          placeholder="Type your message..."
          class="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          :disabled="!connected || isProcessing"
          @keydown="handleKeyDown"
        />
        <button
          class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          :disabled="!connected || isProcessing || !inputMessage.trim()"
          @click="handleSend"
        >
          Send
        </button>
      </div>
    </div>
  </div>
</template>
