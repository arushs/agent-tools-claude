<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import type { DebugMessage } from '../../stores/debug'

const props = defineProps<{
  messages: DebugMessage[]
}>()

defineEmits<{
  clear: []
}>()

const filter = ref<'all' | 'sent' | 'received'>('all')
const expandedIds = ref<Set<number>>(new Set())
const container = ref<HTMLElement | null>(null)
const autoScroll = ref(true)

const filteredMessages = () => {
  if (filter.value === 'all') return props.messages
  return props.messages.filter(m => m.direction === filter.value)
}

function toggleExpanded(id: number) {
  if (expandedIds.value.has(id)) {
    expandedIds.value.delete(id)
  } else {
    expandedIds.value.add(id)
  }
}

function formatTime(date: Date) {
  return date.toLocaleTimeString('en-US', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  }) + '.' + String(date.getMilliseconds()).padStart(3, '0')
}

function formatJson(data: unknown) {
  try {
    return JSON.stringify(data, null, 2)
  } catch {
    return String(data)
  }
}

// Auto-scroll when new messages arrive
watch(
  () => props.messages.length,
  async () => {
    if (autoScroll.value) {
      await nextTick()
      if (container.value) {
        container.value.scrollTop = container.value.scrollHeight
      }
    }
  }
)
</script>

<template>
  <div class="bg-gray-800 rounded-lg flex flex-col h-full">
    <div class="px-4 py-3 border-b border-gray-700 flex items-center justify-between">
      <h3 class="text-sm font-semibold text-gray-300">WebSocket Traffic</h3>
      <div class="flex items-center gap-2">
        <select
          v-model="filter"
          class="text-xs bg-gray-700 border-0 text-gray-300 rounded px-2 py-1 focus:ring-1 focus:ring-blue-500"
        >
          <option value="all">All</option>
          <option value="sent">Sent</option>
          <option value="received">Received</option>
        </select>
        <label class="flex items-center gap-1 text-xs text-gray-400">
          <input
            v-model="autoScroll"
            type="checkbox"
            class="rounded border-gray-600 bg-gray-700 text-blue-500 focus:ring-blue-500 focus:ring-offset-0"
          />
          Auto-scroll
        </label>
        <button
          @click="$emit('clear')"
          class="text-xs text-gray-400 hover:text-gray-200 px-2 py-1 rounded hover:bg-gray-700 transition-colors"
        >
          Clear
        </button>
      </div>
    </div>

    <div ref="container" class="flex-1 overflow-y-auto p-2 space-y-1 font-mono text-xs">
      <div
        v-for="msg in filteredMessages()"
        :key="msg.id"
        class="rounded hover:bg-gray-700/50"
      >
        <div
          class="flex items-start gap-2 p-2 cursor-pointer"
          @click="toggleExpanded(msg.id)"
        >
          <span
            :class="[
              'w-4 text-center flex-shrink-0',
              msg.direction === 'sent' ? 'text-blue-400' : 'text-green-400'
            ]"
          >
            {{ msg.direction === 'sent' ? '↑' : '↓' }}
          </span>
          <span class="text-gray-500 flex-shrink-0">{{ formatTime(msg.timestamp) }}</span>
          <span
            :class="[
              'px-1.5 py-0.5 rounded text-[10px] font-medium flex-shrink-0',
              msg.direction === 'sent'
                ? 'bg-blue-900/50 text-blue-300'
                : 'bg-green-900/50 text-green-300'
            ]"
          >
            {{ msg.type }}
          </span>
          <span class="text-gray-400 truncate flex-1">
            {{ msg.raw.length > 60 ? msg.raw.slice(0, 60) + '...' : msg.raw }}
          </span>
          <span class="text-gray-500 flex-shrink-0">
            {{ expandedIds.has(msg.id) ? '▼' : '▶' }}
          </span>
        </div>

        <div
          v-if="expandedIds.has(msg.id)"
          class="mx-2 mb-2 p-2 bg-gray-900 rounded border border-gray-700"
        >
          <pre class="text-gray-300 whitespace-pre-wrap break-all">{{ formatJson(msg.data) }}</pre>
        </div>
      </div>

      <div v-if="filteredMessages().length === 0" class="text-center text-gray-500 py-8">
        No messages yet. Send a message to see traffic.
      </div>
    </div>
  </div>
</template>
