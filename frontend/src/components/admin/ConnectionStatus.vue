<script setup lang="ts">
import { computed } from 'vue'
import type { ConnectionStats } from '../../stores/debug'

const props = defineProps<{
  connected: boolean
  sessionId: string | null
  stats: ConnectionStats
}>()

const uptime = computed(() => {
  if (!props.stats.connectTime) return '-'
  const seconds = Math.floor((Date.now() - props.stats.connectTime.getTime()) / 1000)
  if (seconds < 60) return `${seconds}s`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ${seconds % 60}s`
  const hours = Math.floor(minutes / 60)
  return `${hours}h ${minutes % 60}m`
})

const lastActivity = computed(() => {
  if (!props.stats.lastMessageTime) return '-'
  const seconds = Math.floor((Date.now() - props.stats.lastMessageTime.getTime()) / 1000)
  if (seconds < 5) return 'just now'
  if (seconds < 60) return `${seconds}s ago`
  const minutes = Math.floor(seconds / 60)
  return `${minutes}m ago`
})
</script>

<template>
  <div class="bg-gray-800 rounded-lg p-4">
    <h3 class="text-sm font-semibold text-gray-300 mb-3">Connection Status</h3>
    <div class="space-y-3">
      <div class="flex items-center justify-between">
        <span class="text-sm text-gray-400">Status</span>
        <span
          :class="[
            'px-2 py-0.5 text-xs font-medium rounded',
            connected
              ? 'bg-green-900/50 text-green-400'
              : 'bg-red-900/50 text-red-400'
          ]"
        >
          {{ connected ? 'Connected' : 'Disconnected' }}
        </span>
      </div>
      <div class="flex items-center justify-between">
        <span class="text-sm text-gray-400">Session ID</span>
        <span class="text-sm font-mono text-gray-300">
          {{ sessionId ? sessionId.slice(0, 12) + '...' : '-' }}
        </span>
      </div>
      <div class="flex items-center justify-between">
        <span class="text-sm text-gray-400">Uptime</span>
        <span class="text-sm font-mono text-gray-300">{{ uptime }}</span>
      </div>
      <div class="flex items-center justify-between">
        <span class="text-sm text-gray-400">Reconnects</span>
        <span class="text-sm font-mono text-gray-300">{{ stats.reconnectAttempts }}</span>
      </div>
      <div class="border-t border-gray-700 pt-3 mt-3">
        <div class="flex items-center justify-between mb-2">
          <span class="text-sm text-gray-400">Messages Sent</span>
          <span class="text-sm font-mono text-blue-400">{{ stats.messagesSent }}</span>
        </div>
        <div class="flex items-center justify-between mb-2">
          <span class="text-sm text-gray-400">Messages Received</span>
          <span class="text-sm font-mono text-green-400">{{ stats.messagesReceived }}</span>
        </div>
        <div class="flex items-center justify-between">
          <span class="text-sm text-gray-400">Last Activity</span>
          <span class="text-sm font-mono text-gray-300">{{ lastActivity }}</span>
        </div>
      </div>
    </div>
  </div>
</template>
