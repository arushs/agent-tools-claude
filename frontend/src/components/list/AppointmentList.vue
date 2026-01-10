<script setup lang="ts">
import { computed } from 'vue'
import { format } from 'date-fns'
import { useAppointmentsStore } from '../../stores/appointments'
import type { Appointment } from '../../types'

const emit = defineEmits<{
  select: [appointment: Appointment]
  delete: [id: string]
}>()

const appointmentsStore = useAppointmentsStore()

const appointments = computed(() => appointmentsStore.upcomingAppointments)
const loading = computed(() => appointmentsStore.loading)

function formatDateTime(dateStr: string): string {
  return format(new Date(dateStr), 'MMM d, yyyy h:mm a')
}

function formatDuration(start: string, end: string): string {
  const startDate = new Date(start)
  const endDate = new Date(end)
  const diffMs = endDate.getTime() - startDate.getTime()
  const diffMins = Math.round(diffMs / 60000)

  if (diffMins < 60) {
    return `${diffMins} min`
  }
  const hours = Math.floor(diffMins / 60)
  const mins = diffMins % 60
  return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`
}

function handleDelete(id: string, event: Event) {
  event.stopPropagation()
  if (confirm('Are you sure you want to cancel this appointment?')) {
    emit('delete', id)
  }
}
</script>

<template>
  <div class="bg-white rounded-lg shadow h-full flex flex-col">
    <div class="px-4 py-3 border-b border-gray-200">
      <h2 class="text-lg font-semibold text-gray-900">Upcoming Appointments</h2>
    </div>

    <div class="flex-1 overflow-y-auto">
      <div v-if="loading" class="flex items-center justify-center h-32">
        <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>

      <div v-else-if="appointments.length === 0" class="p-4 text-center text-gray-500">
        No upcoming appointments
      </div>

      <ul v-else class="divide-y divide-gray-200">
        <li
          v-for="apt in appointments"
          :key="apt.id"
          class="px-4 py-3 hover:bg-gray-50 cursor-pointer transition-colors"
          @click="emit('select', apt)"
        >
          <div class="flex items-start justify-between">
            <div class="flex-1 min-w-0">
              <p class="text-sm font-medium text-gray-900 truncate">
                {{ apt.title }}
              </p>
              <p class="text-sm text-gray-500">
                {{ formatDateTime(apt.start) }}
              </p>
              <p class="text-xs text-gray-400">
                {{ formatDuration(apt.start, apt.end) }}
              </p>
              <p v-if="apt.attendees.length > 0" class="text-xs text-gray-400 mt-1">
                {{ apt.attendees.join(', ') }}
              </p>
            </div>
            <button
              class="ml-2 p-1 text-gray-400 hover:text-red-600 transition-colors"
              title="Cancel appointment"
              @click="handleDelete(apt.id, $event)"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </li>
      </ul>
    </div>
  </div>
</template>
