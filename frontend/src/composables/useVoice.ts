import { ref, computed, onUnmounted } from 'vue'
import { useChatStore } from '../stores/chat'
import { useAppointmentsStore } from '../stores/appointments'
import type {
  WebSocketMessage,
  VoiceState,
  Voice,
  VoiceProcessingMessage,
  VoiceTranscriptionMessage,
  VoiceResponseMessage,
} from '../types'

export function useVoice() {
  const ws = ref<WebSocket | null>(null)
  const connected = ref(false)
  const voiceState = ref<VoiceState>('idle')
  const availableVoices = ref<Voice[]>([])
  const lastTranscription = ref('')
  const lastResponse = ref('')
  const errorMessage = ref('')

  // Audio recording state
  const mediaRecorder = ref<MediaRecorder | null>(null)
  const audioChunks = ref<Blob[]>([])
  const audioStream = ref<MediaStream | null>(null)
  const analyserNode = ref<AnalyserNode | null>(null)
  const audioContext = ref<AudioContext | null>(null)

  const chatStore = useChatStore()
  const appointmentsStore = useAppointmentsStore()

  let reconnectTimeout: ReturnType<typeof setTimeout> | null = null
  const maxReconnectAttempts = 5
  const reconnectAttempts = ref(0)

  // Computed states for UI
  const isRecording = computed(() => voiceState.value === 'recording')
  const isProcessing = computed(() =>
    ['transcribing', 'thinking', 'synthesizing'].includes(voiceState.value)
  )
  const isPlaying = computed(() => voiceState.value === 'playing')
  const canRecord = computed(() =>
    connected.value && voiceState.value === 'idle'
  )

  function connect() {
    if (ws.value?.readyState === WebSocket.OPEN) {
      return
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const sessionId = chatStore.sessionId
    const url = sessionId
      ? `${protocol}//${host}/ws/voice?session_id=${sessionId}`
      : `${protocol}//${host}/ws/voice`

    ws.value = new WebSocket(url)

    ws.value.onopen = () => {
      connected.value = true
      reconnectAttempts.value = 0
      errorMessage.value = ''
    }

    ws.value.onclose = () => {
      connected.value = false
      voiceState.value = 'idle'
      attemptReconnect()
    }

    ws.value.onerror = () => {
      connected.value = false
      errorMessage.value = 'Connection error'
    }

    ws.value.onmessage = (event) => {
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
        availableVoices.value = (data.voices as Voice[]) || []
        break

      case 'history':
        chatStore.setHistory(data.messages as { role: 'user' | 'assistant'; content: string }[])
        break

      case 'processing': {
        const msg = data as VoiceProcessingMessage
        voiceState.value = msg.stage
        break
      }

      case 'transcription': {
        const msg = data as VoiceTranscriptionMessage
        lastTranscription.value = msg.text
        // Add user message to chat
        if (msg.text.trim()) {
          chatStore.addMessage({ role: 'user', content: msg.text })
        }
        break
      }

      case 'response': {
        const msg = data as VoiceResponseMessage
        lastResponse.value = msg.text

        if (msg.error) {
          errorMessage.value = msg.error
          voiceState.value = 'idle'
          return
        }

        // Add assistant message to chat
        if (msg.text.trim()) {
          chatStore.addMessage({ role: 'assistant', content: msg.text })
        }

        // Play audio response
        if (msg.audio) {
          playAudio(msg.audio, msg.mime_type)
        } else {
          voiceState.value = 'idle'
        }

        // Refresh appointments if changed
        if (msg.appointments_changed) {
          appointmentsStore.fetchAppointments()
        }
        break
      }

      case 'audio': {
        const audioData = data.data as string
        const mimeType = data.mime_type as string
        playAudio(audioData, mimeType)
        break
      }

      case 'error':
        errorMessage.value = data.message as string
        voiceState.value = 'idle'
        break

      case 'history_cleared':
        chatStore.clearMessages()
        break

      case 'pong':
        // Heartbeat response
        break
    }
  }

  async function startRecording() {
    if (!canRecord.value) return

    try {
      // Request microphone access
      audioStream.value = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 16000,
        }
      })

      // Set up audio analysis for visualizer
      audioContext.value = new AudioContext()
      const source = audioContext.value.createMediaStreamSource(audioStream.value)
      analyserNode.value = audioContext.value.createAnalyser()
      analyserNode.value.fftSize = 256
      source.connect(analyserNode.value)

      // Set up media recorder
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : 'audio/webm'

      mediaRecorder.value = new MediaRecorder(audioStream.value, { mimeType })
      audioChunks.value = []

      mediaRecorder.value.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunks.value.push(event.data)
        }
      }

      mediaRecorder.value.onstop = () => {
        sendAudio()
      }

      mediaRecorder.value.start()
      voiceState.value = 'recording'
      errorMessage.value = ''
    } catch (error) {
      console.error('Error starting recording:', error)
      errorMessage.value = 'Could not access microphone'
      voiceState.value = 'idle'
    }
  }

  function stopRecording() {
    if (mediaRecorder.value && voiceState.value === 'recording') {
      mediaRecorder.value.stop()

      // Clean up audio stream
      if (audioStream.value) {
        audioStream.value.getTracks().forEach(track => track.stop())
        audioStream.value = null
      }

      // Clean up audio context
      if (audioContext.value) {
        audioContext.value.close()
        audioContext.value = null
      }
      analyserNode.value = null
    }
  }

  async function sendAudio() {
    if (audioChunks.value.length === 0) {
      voiceState.value = 'idle'
      return
    }

    const audioBlob = new Blob(audioChunks.value, { type: 'audio/webm' })
    audioChunks.value = []

    // Convert to base64
    const reader = new FileReader()
    reader.onloadend = () => {
      const base64 = (reader.result as string).split(',')[1]

      if (ws.value?.readyState === WebSocket.OPEN) {
        ws.value.send(JSON.stringify({
          type: 'audio',
          data: base64,
          mime_type: 'audio/webm',
        }))
        voiceState.value = 'transcribing'
      } else {
        errorMessage.value = 'Not connected'
        voiceState.value = 'idle'
      }
    }
    reader.readAsDataURL(audioBlob)
  }

  function playAudio(base64Audio: string, mimeType: string) {
    voiceState.value = 'playing'

    const audio = new Audio(`data:${mimeType};base64,${base64Audio}`)

    audio.onended = () => {
      voiceState.value = 'idle'
    }

    audio.onerror = () => {
      errorMessage.value = 'Failed to play audio'
      voiceState.value = 'idle'
    }

    audio.play().catch((error) => {
      console.error('Error playing audio:', error)
      errorMessage.value = 'Failed to play audio'
      voiceState.value = 'idle'
    })
  }

  function clearHistory() {
    if (ws.value?.readyState === WebSocket.OPEN) {
      ws.value.send(JSON.stringify({ type: 'clear_history' }))
    }
  }

  function attemptReconnect() {
    if (reconnectAttempts.value >= maxReconnectAttempts) {
      return
    }

    reconnectAttempts.value++
    const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.value), 30000)

    reconnectTimeout = setTimeout(() => {
      connect()
    }, delay)
  }

  function disconnect() {
    if (reconnectTimeout) {
      clearTimeout(reconnectTimeout)
    }

    // Stop any ongoing recording
    if (mediaRecorder.value && voiceState.value === 'recording') {
      mediaRecorder.value.stop()
    }

    // Clean up audio resources
    if (audioStream.value) {
      audioStream.value.getTracks().forEach(track => track.stop())
    }
    if (audioContext.value) {
      audioContext.value.close()
    }

    if (ws.value) {
      ws.value.close()
      ws.value = null
    }

    connected.value = false
    voiceState.value = 'idle'
  }

  // Get audio data for visualizer
  function getAudioData(): Uint8Array {
    if (!analyserNode.value) {
      return new Uint8Array(0)
    }

    const dataArray = new Uint8Array(analyserNode.value.frequencyBinCount)
    analyserNode.value.getByteFrequencyData(dataArray)
    return dataArray
  }

  onUnmounted(() => {
    disconnect()
  })

  return {
    // State
    connected,
    voiceState,
    availableVoices,
    lastTranscription,
    lastResponse,
    errorMessage,

    // Computed
    isRecording,
    isProcessing,
    isPlaying,
    canRecord,

    // Methods
    connect,
    disconnect,
    startRecording,
    stopRecording,
    clearHistory,
    getAudioData,
  }
}
