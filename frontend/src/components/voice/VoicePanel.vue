<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useVoice } from '../../composables/useVoice'
import VoiceButton from './VoiceButton.vue'
import AudioVisualizer from './AudioVisualizer.vue'

const {
  connected,
  voiceState,
  lastTranscription,
  errorMessage,
  isRecording,
  canRecord,
  connect,
  startRecording,
  stopRecording,
  getAudioData,
  clearHistory,
} = useVoice()

// Connect on mount
onMounted(() => {
  connect()
})

const showTranscription = computed(() =>
  lastTranscription.value && ['transcribing', 'thinking', 'synthesizing', 'playing'].includes(voiceState.value)
)
</script>

<template>
  <div class="bg-white rounded-lg shadow p-4">
    <div class="flex flex-col items-center gap-4">
      <!-- Header -->
      <div class="flex items-center justify-between w-full">
        <div class="flex items-center gap-2">
          <h3 class="text-lg font-semibold text-gray-900">Voice Chat</h3>
          <span
            :class="[
              'w-2 h-2 rounded-full',
              connected ? 'bg-green-500' : 'bg-red-500'
            ]"
            :title="connected ? 'Connected' : 'Disconnected'"
          />
        </div>
        <button
          class="text-sm text-gray-500 hover:text-gray-700 transition-colors"
          @click="clearHistory"
        >
          Clear
        </button>
      </div>

      <!-- Audio Visualizer -->
      <div class="w-full">
        <AudioVisualizer
          :is-active="isRecording"
          :get-audio-data="getAudioData"
        />
      </div>

      <!-- Voice Button -->
      <VoiceButton
        :voice-state="voiceState"
        :connected="connected"
        :can-record="canRecord"
        @start-recording="startRecording"
        @stop-recording="stopRecording"
      />

      <!-- Transcription preview -->
      <div v-if="showTranscription" class="w-full">
        <div class="bg-blue-50 rounded-lg p-3">
          <p class="text-sm text-gray-500 mb-1">You said:</p>
          <p class="text-gray-900">{{ lastTranscription }}</p>
        </div>
      </div>

      <!-- Error message -->
      <div v-if="errorMessage" class="w-full">
        <div class="bg-red-50 rounded-lg p-3 text-red-700 text-sm">
          {{ errorMessage }}
        </div>
      </div>

      <!-- Instructions -->
      <p class="text-xs text-gray-500 text-center">
        Hold the button or press Space to talk
      </p>
    </div>
  </div>
</template>
