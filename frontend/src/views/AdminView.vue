<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { useChatStore } from '../stores/chat'
import { useDebugStore } from '../stores/debug'
import { useAdminWebSocket } from '../composables/useAdminWebSocket'
import AdminHeader from '../components/admin/AdminHeader.vue'
import ConnectionStatus from '../components/admin/ConnectionStatus.vue'
import DebugPanel from '../components/admin/DebugPanel.vue'

const chatStore = useChatStore()
const debugStore = useDebugStore()
const { connected, connect, disconnect, sendMessage, clearHistory, sendPing } = useAdminWebSocket()

const inputMessage = ref('')
const messagesContainer = ref<HTMLElement | null>(null)

const messages = computed(() => chatStore.messages)
const sessionId = computed(() => chatStore.sessionId)
const isProcessing = computed(() => chatStore.isProcessing)
const debugMessages = computed(() => debugStore.recentMessages)
const connectionStats = computed(() => debugStore.connectionStats)

onMounted(() => {
  connect()
})

onUnmounted(() => {
  disconnect()
  chatStore.clearMessages()
  debugStore.clearMessages()
  debugStore.resetStats()
})

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

function handleClearDebug() {
  debugStore.clearMessages()
}

function handlePing() {
  sendPing()
}

function handleReconnect() {
  disconnect()
  setTimeout(() => connect(), 100)
}
</script>

<template>
  <div class="min-h-screen bg-gray-900 flex flex-col">
    <AdminHeader
      :connected="connected"
      :session-id="sessionId"
    />

    <main class="flex-1 p-4 overflow-hidden">
      <div class="h-full grid grid-cols-1 lg:grid-cols-3 gap-4" style="height: calc(100vh - 80px)">
        <!-- Left: Chat Panel -->
        <div class="lg:col-span-2 flex flex-col bg-gray-800 rounded-lg overflow-hidden">
          <!-- Chat Header -->
          <div class="px-4 py-3 border-b border-gray-700 flex items-center justify-between">
            <div class="flex items-center gap-3">
              <h2 class="text-sm font-semibold text-gray-200">Chat (Real WebSocket)</h2>
              <span
                :class="[
                  'w-2 h-2 rounded-full',
                  connected ? 'bg-green-500' : 'bg-red-500'
                ]"
              ></span>
            </div>
            <div class="flex items-center gap-2">
              <button
                @click="handlePing"
                :disabled="!connected"
                class="text-xs px-2 py-1 text-gray-400 hover:text-gray-200 hover:bg-gray-700 rounded transition-colors disabled:opacity-50"
              >
                Ping
              </button>
              <button
                @click="handleReconnect"
                class="text-xs px-2 py-1 text-gray-400 hover:text-gray-200 hover:bg-gray-700 rounded transition-colors"
              >
                Reconnect
              </button>
              <button
                @click="handleClear"
                class="text-xs px-2 py-1 text-gray-400 hover:text-gray-200 hover:bg-gray-700 rounded transition-colors"
              >
                Clear
              </button>
            </div>
          </div>

          <!-- Messages -->
          <div ref="messagesContainer" class="flex-1 overflow-y-auto p-4 space-y-3">
            <div v-if="messages.length === 0" class="text-center text-gray-500 py-8">
              <p class="text-sm">No messages yet.</p>
              <p class="text-xs mt-1">Send a message to test the WebSocket connection.</p>
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
                  'max-w-[85%] rounded-lg px-3 py-2',
                  msg.role === 'user'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-700 text-gray-100'
                ]"
              >
                <p class="whitespace-pre-wrap text-sm">{{ msg.content }}</p>
              </div>
            </div>

            <!-- Typing indicator -->
            <div v-if="isProcessing" class="flex justify-start">
              <div class="bg-gray-700 rounded-lg px-3 py-2">
                <div class="flex items-center gap-1">
                  <div class="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0ms"></div>
                  <div class="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 150ms"></div>
                  <div class="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 300ms"></div>
                </div>
              </div>
            </div>
          </div>

          <!-- Input area -->
          <div class="px-4 py-3 border-t border-gray-700">
            <div class="flex gap-2">
              <input
                v-model="inputMessage"
                type="text"
                placeholder="Type a message..."
                class="flex-1 px-3 py-2 bg-gray-700 border border-gray-600 text-gray-100 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 text-sm placeholder-gray-400"
                :disabled="!connected || isProcessing"
                @keydown="handleKeyDown"
              />
              <button
                class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                :disabled="!connected || isProcessing || !inputMessage.trim()"
                @click="handleSend"
              >
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
              </button>
            </div>
          </div>
        </div>

        <!-- Right: Debug Sidebar -->
        <div class="flex flex-col gap-4 overflow-hidden">
          <ConnectionStatus
            :connected="connected"
            :session-id="sessionId"
            :stats="connectionStats"
          />

          <div class="flex-1 overflow-hidden">
            <DebugPanel
              :messages="debugMessages"
              @clear="handleClearDebug"
            />
          </div>
        </div>
      </div>
    </main>
  </div>
</template>
