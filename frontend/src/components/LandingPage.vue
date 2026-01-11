<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

function startDemo() {
  router.push('/demo')
}

function goToAdmin() {
  router.push('/admin')
}
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900">
    <!-- Animated background pattern -->
    <div class="absolute inset-0 overflow-hidden">
      <div class="absolute w-96 h-96 -top-48 -left-48 bg-blue-500/20 rounded-full blur-3xl animate-pulse"></div>
      <div class="absolute w-96 h-96 -bottom-48 -right-48 bg-indigo-500/20 rounded-full blur-3xl animate-pulse" style="animation-delay: 1s"></div>
      <div class="absolute w-64 h-64 top-1/2 left-1/3 bg-cyan-500/10 rounded-full blur-3xl animate-pulse" style="animation-delay: 2s"></div>
    </div>

    <!-- Content -->
    <div class="relative z-10 flex flex-col items-center justify-center min-h-screen px-6">
      <!-- Logo/Brand -->
      <div class="mb-8">
        <div class="w-20 h-20 mx-auto bg-gradient-to-br from-blue-400 to-indigo-600 rounded-2xl flex items-center justify-center shadow-xl shadow-blue-500/30">
          <svg class="w-12 h-12 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
        </div>
      </div>

      <!-- Hero Text -->
      <h1 class="text-5xl md:text-6xl font-bold text-white text-center mb-6 tracking-tight">
        AI Scheduling
        <span class="block text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-cyan-400">
          Assistant
        </span>
      </h1>

      <p class="text-xl text-slate-300 text-center max-w-2xl mb-12 leading-relaxed">
        Book meetings with natural language. Just type what you need and watch your calendar update in real-time.
      </p>

      <!-- Feature pills -->
      <div class="flex flex-wrap justify-center gap-3 mb-12">
        <span class="px-4 py-2 bg-white/10 backdrop-blur-sm rounded-full text-sm text-slate-300 border border-white/10">
          Natural Language
        </span>
        <span class="px-4 py-2 bg-white/10 backdrop-blur-sm rounded-full text-sm text-slate-300 border border-white/10">
          Instant Updates
        </span>
        <span class="px-4 py-2 bg-white/10 backdrop-blur-sm rounded-full text-sm text-slate-300 border border-white/10">
          Conflict Detection
        </span>
        <span class="px-4 py-2 bg-white/10 backdrop-blur-sm rounded-full text-sm text-slate-300 border border-white/10">
          Smart Suggestions
        </span>
      </div>

      <!-- CTA Button -->
      <button
        @click="startDemo"
        class="group relative px-8 py-4 bg-gradient-to-r from-blue-500 to-indigo-600 text-white font-semibold text-lg rounded-xl shadow-xl shadow-blue-500/30 hover:shadow-blue-500/50 transition-all duration-300 hover:-translate-y-1"
      >
        <span class="relative z-10 flex items-center gap-2">
          Try the Demo
          <svg class="w-5 h-5 group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6" />
          </svg>
        </span>
      </button>

      <!-- Demo hint -->
      <p class="mt-8 text-slate-400 text-sm text-center max-w-md">
        Try saying: <span class="text-slate-300">"Book a meeting with Alex tomorrow at 2pm"</span>
      </p>

      <!-- Example cards -->
      <div class="mt-16 grid grid-cols-1 md:grid-cols-3 gap-4 max-w-4xl">
        <div class="p-6 bg-white/5 backdrop-blur-sm rounded-xl border border-white/10">
          <div class="w-10 h-10 bg-blue-500/20 rounded-lg flex items-center justify-center mb-4">
            <svg class="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h3 class="text-white font-semibold mb-2">Quick Booking</h3>
          <p class="text-slate-400 text-sm">"Schedule standup for Monday 9am"</p>
        </div>

        <div class="p-6 bg-white/5 backdrop-blur-sm rounded-xl border border-white/10">
          <div class="w-10 h-10 bg-green-500/20 rounded-lg flex items-center justify-center mb-4">
            <svg class="w-5 h-5 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h3 class="text-white font-semibold mb-2">Check Availability</h3>
          <p class="text-slate-400 text-sm">"Am I free Friday at 3pm?"</p>
        </div>

        <div class="p-6 bg-white/5 backdrop-blur-sm rounded-xl border border-white/10">
          <div class="w-10 h-10 bg-purple-500/20 rounded-lg flex items-center justify-center mb-4">
            <svg class="w-5 h-5 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 10h16M4 14h16M4 18h16" />
            </svg>
          </div>
          <h3 class="text-white font-semibold mb-2">View Schedule</h3>
          <p class="text-slate-400 text-sm">"What's on my calendar today?"</p>
        </div>
      </div>

      <!-- Footer -->
      <div class="absolute bottom-6 flex items-center gap-4 text-slate-500 text-sm">
        <span>Built with Claude AI</span>
        <span class="text-slate-600">|</span>
        <button
          @click="goToAdmin"
          class="text-slate-500 hover:text-slate-300 transition-colors"
        >
          Admin
        </button>
      </div>
    </div>
  </div>
</template>
