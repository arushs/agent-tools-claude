<script setup lang="ts">
import { computed } from 'vue'
import type { VoiceState } from '../../types'

const props = defineProps<{
  voiceState: VoiceState
  connected: boolean
  canRecord: boolean
}>()

const emit = defineEmits<{
  startRecording: []
  stopRecording: []
}>()

const buttonClass = computed(() => {
  const base = 'relative w-16 h-16 rounded-full flex items-center justify-center transition-all duration-200 focus:outline-none focus:ring-4'

  if (!props.connected) {
    return `${base} bg-gray-300 cursor-not-allowed`
  }

  switch (props.voiceState) {
    case 'recording':
      return `${base} bg-red-500 hover:bg-red-600 focus:ring-red-300 animate-pulse`
    case 'transcribing':
    case 'thinking':
    case 'synthesizing':
      return `${base} bg-blue-400 cursor-wait`
    case 'playing':
      return `${base} bg-green-500`
    default:
      return `${base} bg-blue-600 hover:bg-blue-700 focus:ring-blue-300`
  }
})

const statusText = computed(() => {
  if (!props.connected) return 'Disconnected'

  switch (props.voiceState) {
    case 'recording':
      return 'Recording...'
    case 'transcribing':
      return 'Transcribing...'
    case 'thinking':
      return 'Thinking...'
    case 'synthesizing':
      return 'Generating audio...'
    case 'playing':
      return 'Speaking...'
    default:
      return 'Push to talk'
  }
})

function handleClick() {
  if (!props.connected) return

  if (props.voiceState === 'recording') {
    emit('stopRecording')
  } else if (props.canRecord) {
    emit('startRecording')
  }
}

function handleMouseDown() {
  if (props.canRecord) {
    emit('startRecording')
  }
}

function handleMouseUp() {
  if (props.voiceState === 'recording') {
    emit('stopRecording')
  }
}

function handleKeyDown(event: KeyboardEvent) {
  if (event.code === 'Space' && props.canRecord) {
    event.preventDefault()
    emit('startRecording')
  }
}

function handleKeyUp(event: KeyboardEvent) {
  if (event.code === 'Space' && props.voiceState === 'recording') {
    event.preventDefault()
    emit('stopRecording')
  }
}
</script>

<template>
  <div class="flex flex-col items-center gap-2">
    <button
      :class="buttonClass"
      :disabled="!connected || (!canRecord && voiceState !== 'recording')"
      @click="handleClick"
      @mousedown="handleMouseDown"
      @mouseup="handleMouseUp"
      @mouseleave="handleMouseUp"
      @touchstart.prevent="handleMouseDown"
      @touchend.prevent="handleMouseUp"
      @keydown="handleKeyDown"
      @keyup="handleKeyUp"
    >
      <!-- Microphone icon -->
      <svg
        v-if="voiceState === 'idle' || voiceState === 'recording'"
        class="w-8 h-8 text-white"
        fill="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          d="M12 14c1.66 0 2.99-1.34 2.99-3L15 5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm5.3-3c0 3-2.54 5.1-5.3 5.1S6.7 14 6.7 11H5c0 3.41 2.72 6.23 6 6.72V21h2v-3.28c3.28-.48 6-3.3 6-6.72h-1.7z"
        />
      </svg>

      <!-- Processing spinner -->
      <svg
        v-else-if="voiceState === 'transcribing' || voiceState === 'thinking' || voiceState === 'synthesizing'"
        class="w-8 h-8 text-white animate-spin"
        fill="none"
        viewBox="0 0 24 24"
      >
        <circle
          class="opacity-25"
          cx="12"
          cy="12"
          r="10"
          stroke="currentColor"
          stroke-width="4"
        />
        <path
          class="opacity-75"
          fill="currentColor"
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
        />
      </svg>

      <!-- Speaker icon for playing -->
      <svg
        v-else-if="voiceState === 'playing'"
        class="w-8 h-8 text-white"
        fill="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"
        />
      </svg>

      <!-- Recording ring animation -->
      <div
        v-if="voiceState === 'recording'"
        class="absolute inset-0 rounded-full border-4 border-red-400 animate-ping"
      />
    </button>

    <span class="text-sm text-gray-600">{{ statusText }}</span>
  </div>
</template>
