<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useAppointmentsStore } from './stores/appointments'
import CalendarView from './components/calendar/CalendarView.vue'
import AppointmentList from './components/list/AppointmentList.vue'
import ChatPanel from './components/chat/ChatPanel.vue'
import type { Appointment } from './types'

const appointmentsStore = useAppointmentsStore()

const selectedAppointment = ref<Appointment | null>(null)
const activeView = ref<'calendar' | 'list'>('calendar')

onMounted(async () => {
  await appointmentsStore.fetchAppointments()
})

function handleEventClick(id: string) {
  const apt = appointmentsStore.appointments.find((a) => a.id === id)
  if (apt) {
    selectedAppointment.value = apt
  }
}

function handleSelectAppointment(apt: Appointment) {
  selectedAppointment.value = apt
}

async function handleDeleteAppointment(id: string) {
  await appointmentsStore.deleteAppointment(id)
  if (selectedAppointment.value?.id === id) {
    selectedAppointment.value = null
  }
}

function closeModal() {
  selectedAppointment.value = null
}
</script>

<template>
  <div class="min-h-screen bg-gray-100">
    <!-- Header -->
    <header class="bg-white shadow-sm">
      <div class="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
        <div class="flex items-center justify-between">
          <h1 class="text-2xl font-bold text-gray-900">Appointment Booking</h1>
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
              Calendar
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
              List
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

        <!-- Chat Panel -->
        <div class="h-full">
          <ChatPanel />
        </div>
      </div>
    </main>

    <!-- Appointment Detail Modal -->
    <div
      v-if="selectedAppointment"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      @click.self="closeModal"
    >
      <div class="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
        <div class="flex items-start justify-between mb-4">
          <h3 class="text-lg font-semibold text-gray-900">
            {{ selectedAppointment.title }}
          </h3>
          <button
            class="text-gray-400 hover:text-gray-600"
            @click="closeModal"
          >
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div class="space-y-3 text-sm">
          <div>
            <span class="text-gray-500">Start:</span>
            <span class="ml-2 text-gray-900">
              {{ new Date(selectedAppointment.start).toLocaleString() }}
            </span>
          </div>
          <div>
            <span class="text-gray-500">End:</span>
            <span class="ml-2 text-gray-900">
              {{ new Date(selectedAppointment.end).toLocaleString() }}
            </span>
          </div>
          <div v-if="selectedAppointment.attendees.length > 0">
            <span class="text-gray-500">Attendees:</span>
            <span class="ml-2 text-gray-900">
              {{ selectedAppointment.attendees.join(', ') }}
            </span>
          </div>
          <div v-if="selectedAppointment.location">
            <span class="text-gray-500">Location:</span>
            <span class="ml-2 text-gray-900">
              {{ selectedAppointment.location }}
            </span>
          </div>
          <div v-if="selectedAppointment.description">
            <span class="text-gray-500">Description:</span>
            <p class="mt-1 text-gray-900">
              {{ selectedAppointment.description }}
            </p>
          </div>
        </div>

        <div class="mt-6 flex justify-end gap-3">
          <button
            class="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
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
