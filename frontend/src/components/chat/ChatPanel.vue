<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { useChatStore } from '../../stores/chat'
import { useWebSocket } from '../../composables/useWebSocket'
import { useVoice } from '../../composables/useVoice'
import VoiceButton from '../voice/VoiceButton.vue'
import AudioVisualizer from '../voice/AudioVisualizer.vue'

const chatStore = useChatStore()
const { connected: textConnected, connect: textConnect, sendMessage, clearHistory: textClearHistory } = useWebSocket()
const {
  connected: voiceConnected,
  voiceState,
  isRecording,
  canRecord,
  connect: voiceConnect,
  startRecording,
  stopRecording,
  clearHistory: voiceClearHistory,
  getAudioData,
  errorMessage: voiceError,
} = useVoice()

const inputMessage = ref('')
const messagesContainer = ref<HTMLElement | null>(null)
const inputMode = ref<'text' | 'voice'>('text')

const messages = computed(() => chatStore.messages)
const isProcessing = computed(() => chatStore.isProcessing || ['transcribing', 'thinking', 'synthesizing', 'playing'].includes(voiceState.value))
const connected = computed(() => inputMode.value === 'text' ? textConnected.value : voiceConnected.value)

// Connect on mount based on mode
textConnect()

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

// Connect voice when switching to voice mode
watch(inputMode, (mode) => {
  if (mode === 'voice' && !voiceConnected.value) {
    voiceConnect()
  }
})

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
    if (inputMode.value === 'text') {
      textClearHistory()
    } else {
      voiceClearHistory()
    }
  }
}

function toggleMode() {
  inputMode.value = inputMode.value === 'text' ? 'voice' : 'text'
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
      <div class="flex items-center gap-2">
        <!-- Mode toggle -->
        <button
          :class="[
            'p-2 rounded-lg transition-colors',
            inputMode === 'voice' ? 'bg-blue-100 text-blue-600' : 'text-gray-500 hover:bg-gray-100'
          ]"
          :title="inputMode === 'voice' ? 'Switch to text' : 'Switch to voice'"
          @click="toggleMode"
        >
          <svg v-if="inputMode === 'text'" class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 14c1.66 0 2.99-1.34 2.99-3L15 5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm5.3-3c0 3-2.54 5.1-5.3 5.1S6.7 14 6.7 11H5c0 3.41 2.72 6.23 6 6.72V21h2v-3.28c3.28-.48 6-3.3 6-6.72h-1.7z"/>
          </svg>
          <svg v-else class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
            <path d="M20 2H4c-1.1 0-1.99.9-1.99 2L2 22l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zM6 9h12v2H6V9zm8 5H6v-2h8v2zm4-6H6V6h12v2z"/>
          </svg>
        </button>
        <button
          class="text-sm text-gray-500 hover:text-gray-700 transition-colors"
          @click="handleClear"
        >
          Clear
        </button>
      </div>
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
          <div class="flex items-center gap-2">
            <div class="flex space-x-1">
              <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0ms"></div>
              <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 150ms"></div>
              <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 300ms"></div>
            </div>
            <span v-if="voiceState === 'transcribing'" class="text-xs text-gray-500">Transcribing...</span>
            <span v-else-if="voiceState === 'thinking'" class="text-xs text-gray-500">Thinking...</span>
            <span v-else-if="voiceState === 'synthesizing'" class="text-xs text-gray-500">Generating audio...</span>
            <span v-else-if="voiceState === 'playing'" class="text-xs text-gray-500">Speaking...</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Voice error -->
    <div v-if="voiceError && inputMode === 'voice'" class="px-4 py-2 bg-red-50">
      <p class="text-sm text-red-600">{{ voiceError }}</p>
    </div>

    <!-- Input area -->
    <div class="px-4 py-3 border-t border-gray-200">
      <!-- Text input mode -->
      <div v-if="inputMode === 'text'" class="flex gap-2">
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

      <!-- Voice input mode -->
      <div v-else class="flex flex-col items-center gap-3">
        <!-- Audio Visualizer -->
        <AudioVisualizer
          :is-active="isRecording"
          :get-audio-data="getAudioData"
          class="w-full"
        />

        <!-- Voice Button -->
        <VoiceButton
          :voice-state="voiceState"
          :connected="voiceConnected"
          :can-record="canRecord"
          @start-recording="startRecording"
          @stop-recording="stopRecording"
        />
      </div>
    </div>
  </div>
</template>
