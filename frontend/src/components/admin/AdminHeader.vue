<script setup lang="ts">
import { useRouter } from 'vue-router'

defineProps<{
  connected: boolean
  sessionId: string | null
}>()

const router = useRouter()

function goToDemo() {
  router.push('/demo')
}

function goToLanding() {
  router.push('/')
}
</script>

<template>
  <header class="bg-gray-800 border-b border-gray-700">
    <div class="px-4 py-3">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-4">
          <h1 class="text-lg font-semibold text-gray-100">Admin Portal</h1>
          <span class="px-2 py-0.5 text-xs font-mono bg-gray-700 text-gray-300 rounded">
            WebSocket Testing
          </span>
        </div>
        <div class="flex items-center gap-4">
          <div class="flex items-center gap-2 text-sm">
            <span
              :class="[
                'w-2 h-2 rounded-full',
                connected ? 'bg-green-500' : 'bg-red-500'
              ]"
            ></span>
            <span class="text-gray-400">
              {{ connected ? 'Connected' : 'Disconnected' }}
            </span>
            <span v-if="sessionId" class="text-gray-500 font-mono text-xs">
              {{ sessionId.slice(0, 8) }}...
            </span>
          </div>
          <nav class="flex gap-2">
            <button
              @click="goToDemo"
              class="px-3 py-1.5 text-sm text-gray-300 hover:text-white hover:bg-gray-700 rounded transition-colors"
            >
              Demo
            </button>
            <button
              @click="goToLanding"
              class="px-3 py-1.5 text-sm text-gray-300 hover:text-white hover:bg-gray-700 rounded transition-colors"
            >
              Home
            </button>
          </nav>
        </div>
      </div>
    </div>
  </header>
</template>
