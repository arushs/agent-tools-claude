<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAppointmentsStore } from '../stores/appointments'
import { useChatStore } from '../stores/chat'
import { useDemoMode } from '../composables/useDemoMode'
import CalendarView from '../components/calendar/CalendarView.vue'
import AppointmentList from '../components/list/AppointmentList.vue'
import type { Appointment } from '../types'

const router = useRouter()
const appointmentsStore = useAppointmentsStore()
const chatStore = useChatStore()
const { connected, enableDemoMode, sendMessage, clearHistory } = useDemoMode()

const selectedAppointment = ref<Appointment | null>(null)
const activeView = ref<'calendar' | 'list'>('calendar')
const inputMessage = ref('')
const messagesContainer = ref<HTMLElement | null>(null)

const messages = computed(() => chatStore.messages)
const isProcessing = computed(() => chatStore.isProcessing)

// Enable demo mode when component mounts
onMounted(() => {
  enableDemoMode()
})

// Cleanup when leaving
onUnmounted(() => {
  chatStore.clearMessages()
  appointmentsStore.appointments = []
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

function handleEventClick(id: string) {
  const apt = appointmentsStore.appointments.find((a) => a.id === id)
  if (apt) {
    selectedAppointment.value = apt
  }
}

function handleSelectAppointment(apt: Appointment) {
  selectedAppointment.value = apt
}

function handleDeleteAppointment(id: string) {
  appointmentsStore.appointments = appointmentsStore.appointments.filter((apt) => apt.id !== id)
  if (selectedAppointment.value?.id === id) {
    selectedAppointment.value = null
  }
}

function closeModal() {
  selectedAppointment.value = null
}

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

function goBack() {
  router.push('/')
}

function goToAdmin() {
  router.push('/admin')
}
</script>

<template>
  <div class="min-h-screen bg-gray-100">
    <!-- Header -->
    <header class="bg-white shadow-sm">
      <div class="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-4">
            <button
              @click="goBack"
              class="text-gray-500 hover:text-gray-700 transition-colors"
              title="Back to landing"
            >
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
            </button>
            <h1 class="text-2xl font-bold text-gray-900">AI Scheduling Assistant</h1>
            <span class="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-700 rounded-full">Demo Mode</span>
            <button
              @click="goToAdmin"
              class="px-2 py-1 text-xs font-medium text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded transition-colors"
              title="Admin Portal"
            >
              Admin
            </button>
          </div>
          <div class="flex gap-2">
            <button
              :class="[
                'px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                activeView === 'calendar'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              ]"
              @click="activeView = 'calendar'"
            >
              <span class="flex items-center gap-2">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
                Calendar
              </span>
            </button>
            <button
              :class="[
                'px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                activeView === 'list'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              ]"
              @click="activeView = 'list'"
            >
              <span class="flex items-center gap-2">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 10h16M4 14h16M4 18h16" />
                </svg>
                List
              </span>
            </button>
          </div>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main class="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6" style="height: calc(100vh - 140px)">
        <!-- Calendar/List View -->
        <div class="lg:col-span-2 h-full">
          <CalendarView
            v-if="activeView === 'calendar'"
            @event-click="handleEventClick"
          />
          <AppointmentList
            v-else
            @select="handleSelectAppointment"
            @delete="handleDeleteAppointment"
          />
        </div>

        <!-- Chat Panel (Demo Mode) -->
        <div class="h-full">
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
                <div class="w-16 h-16 mx-auto mb-4 bg-blue-100 rounded-full flex items-center justify-center">
                  <svg class="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                  </svg>
                </div>
                <p class="mb-2 font-medium">Welcome! I'm your scheduling assistant.</p>
                <p class="text-sm">Try asking:</p>
                <ul class="text-sm mt-2 space-y-1">
                  <li class="text-blue-600">"Book a meeting tomorrow at 2pm"</li>
                  <li class="text-blue-600">"What's on my schedule today?"</li>
                  <li class="text-blue-600">"Am I free on Friday at 3pm?"</li>
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
                    'max-w-[85%] rounded-2xl px-4 py-3',
                    msg.role === 'user'
                      ? 'bg-blue-600 text-white rounded-br-md'
                      : 'bg-gray-100 text-gray-900 rounded-bl-md'
                  ]"
                >
                  <p class="whitespace-pre-wrap text-sm">{{ msg.content }}</p>
                </div>
              </div>

              <!-- Typing indicator -->
              <div v-if="isProcessing" class="flex justify-start">
                <div class="bg-gray-100 rounded-2xl rounded-bl-md px-4 py-3">
                  <div class="flex items-center gap-1">
                    <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0ms"></div>
                    <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 150ms"></div>
                    <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 300ms"></div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Input area -->
            <div class="px-4 py-3 border-t border-gray-200">
              <div class="flex gap-2">
                <input
                  v-model="inputMessage"
                  type="text"
                  placeholder="Type a message..."
                  class="flex-1 px-4 py-2.5 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                  :disabled="!connected || isProcessing"
                  @keydown="handleKeyDown"
                />
                <button
                  class="px-4 py-2.5 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
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
        </div>
      </div>
    </main>

    <!-- Appointment Detail Modal -->
    <div
      v-if="selectedAppointment"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      @click.self="closeModal"
    >
      <div class="bg-white rounded-xl shadow-2xl max-w-md w-full mx-4 overflow-hidden">
        <div class="bg-gradient-to-r from-blue-500 to-indigo-600 px-6 py-4">
          <div class="flex items-start justify-between">
            <h3 class="text-lg font-semibold text-white">
              {{ selectedAppointment.title }}
            </h3>
            <button
              class="text-white/80 hover:text-white"
              @click="closeModal"
            >
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        <div class="p-6 space-y-4">
          <div class="flex items-center gap-3 text-sm">
            <svg class="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div>
              <p class="text-gray-900 font-medium">
                {{ new Date(selectedAppointment.start).toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' }) }}
              </p>
              <p class="text-gray-500">
                {{ new Date(selectedAppointment.start).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' }) }} -
                {{ new Date(selectedAppointment.end).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' }) }}
              </p>
            </div>
          </div>

          <div v-if="selectedAppointment.attendees.length > 0" class="flex items-center gap-3 text-sm">
            <svg class="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            <p class="text-gray-700">
              {{ selectedAppointment.attendees.join(', ') }}
            </p>
          </div>

          <div v-if="selectedAppointment.description" class="flex items-start gap-3 text-sm">
            <svg class="w-5 h-5 text-gray-400 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h7" />
            </svg>
            <p class="text-gray-700">{{ selectedAppointment.description }}</p>
          </div>
        </div>

        <div class="px-6 py-4 bg-gray-50 flex justify-end gap-3">
          <button
            class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
            @click="closeModal"
          >
            Close
          </button>
          <button
            class="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
            @click="handleDeleteAppointment(selectedAppointment.id); closeModal()"
          >
            Cancel Appointment
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
