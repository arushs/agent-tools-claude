<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAppointmentsStore } from '../stores/appointments'
import type { Appointment } from '../types'

const router = useRouter()
const appointmentsStore = useAppointmentsStore()

const searchQuery = ref('')
const statusFilter = ref<'all' | 'confirmed' | 'pending' | 'cancelled'>('all')
const selectedAppointment = ref<Appointment | null>(null)

// Sample data for demo mode
const sampleAppointments: Appointment[] = [
  {
    id: '1',
    title: 'Team Standup',
    start: new Date(Date.now() + 1000 * 60 * 60).toISOString(),
    end: new Date(Date.now() + 1000 * 60 * 90).toISOString(),
    attendees: ['alice@example.com', 'bob@example.com'],
    description: 'Daily standup meeting',
    status: 'confirmed'
  },
  {
    id: '2',
    title: 'Client Review',
    start: new Date(Date.now() + 1000 * 60 * 60 * 24).toISOString(),
    end: new Date(Date.now() + 1000 * 60 * 60 * 25).toISOString(),
    attendees: ['client@acme.com'],
    description: 'Quarterly review with ACME Corp',
    status: 'confirmed'
  },
  {
    id: '3',
    title: 'Project Planning',
    start: new Date(Date.now() + 1000 * 60 * 60 * 48).toISOString(),
    end: new Date(Date.now() + 1000 * 60 * 60 * 50).toISOString(),
    attendees: ['team@example.com'],
    description: 'Sprint planning session',
    status: 'pending'
  },
  {
    id: '4',
    title: 'Cancelled: Training Session',
    start: new Date(Date.now() - 1000 * 60 * 60 * 24).toISOString(),
    end: new Date(Date.now() - 1000 * 60 * 60 * 22).toISOString(),
    attendees: ['hr@example.com'],
    description: 'New employee training',
    status: 'cancelled'
  },
  {
    id: '5',
    title: 'Weekly Sync',
    start: new Date(Date.now() + 1000 * 60 * 60 * 72).toISOString(),
    end: new Date(Date.now() + 1000 * 60 * 60 * 73).toISOString(),
    attendees: ['manager@example.com'],
    description: 'Weekly team synchronization',
    status: 'confirmed'
  }
]

onMounted(() => {
  // Load sample data if appointments store is empty
  if (appointmentsStore.appointments.length === 0) {
    appointmentsStore.appointments = [...sampleAppointments]
  }
})

const allAppointments = computed(() => {
  return appointmentsStore.appointments.length > 0
    ? appointmentsStore.appointments
    : sampleAppointments
})

const filteredAppointments = computed(() => {
  let result = [...allAppointments.value]

  // Apply status filter
  if (statusFilter.value !== 'all') {
    result = result.filter((apt) => apt.status === statusFilter.value)
  }

  // Apply search filter
  if (searchQuery.value.trim()) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(
      (apt) =>
        apt.title.toLowerCase().includes(query) ||
        apt.attendees.some((a) => a.toLowerCase().includes(query)) ||
        apt.description?.toLowerCase().includes(query)
    )
  }

  // Sort by date
  return result.sort((a, b) => new Date(a.start).getTime() - new Date(b.start).getTime())
})

// Statistics
const stats = computed(() => {
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const tomorrow = new Date(today.getTime() + 24 * 60 * 60 * 1000)

  const appointments = allAppointments.value

  return {
    total: appointments.length,
    today: appointments.filter((apt) => {
      const start = new Date(apt.start)
      return start >= today && start < tomorrow && apt.status !== 'cancelled'
    }).length,
    upcoming: appointments.filter((apt) => {
      const start = new Date(apt.start)
      return start >= now && apt.status !== 'cancelled'
    }).length,
    cancelled: appointments.filter((apt) => apt.status === 'cancelled').length
  }
})

function goBack() {
  router.push('/')
}

function goToDemo() {
  router.push('/demo')
}

function formatDate(dateStr: string) {
  const date = new Date(dateStr)
  return date.toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric'
  })
}

function formatTime(dateStr: string) {
  const date = new Date(dateStr)
  return date.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit'
  })
}

function getStatusColor(status?: string) {
  switch (status) {
    case 'confirmed':
      return 'bg-green-100 text-green-800'
    case 'pending':
      return 'bg-yellow-100 text-yellow-800'
    case 'cancelled':
      return 'bg-red-100 text-red-800'
    default:
      return 'bg-gray-100 text-gray-800'
  }
}

function viewAppointment(apt: Appointment) {
  selectedAppointment.value = apt
}

function closeModal() {
  selectedAppointment.value = null
}

function deleteAppointment(id: string) {
  appointmentsStore.appointments = appointmentsStore.appointments.filter((apt) => apt.id !== id)
  if (selectedAppointment.value?.id === id) {
    selectedAppointment.value = null
  }
}

function updateStatus(id: string, status: 'confirmed' | 'pending' | 'cancelled') {
  const apt = appointmentsStore.appointments.find((a) => a.id === id)
  if (apt) {
    apt.status = status
  }
}
</script>

<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Header -->
    <header class="bg-white shadow-sm border-b border-gray-200">
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
            <div>
              <h1 class="text-2xl font-bold text-gray-900">Admin Portal</h1>
              <p class="text-sm text-gray-500">Manage appointments and system settings</p>
            </div>
          </div>
          <button
            @click="goToDemo"
            class="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-2"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Open Demo
          </button>
        </div>
      </div>
    </header>

    <main class="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
      <!-- Stats Cards -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <div class="bg-white rounded-xl shadow-sm p-6 border border-gray-100">
          <div class="flex items-center gap-4">
            <div class="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center">
              <svg class="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
            </div>
            <div>
              <p class="text-sm text-gray-500">Total Appointments</p>
              <p class="text-2xl font-bold text-gray-900">{{ stats.total }}</p>
            </div>
          </div>
        </div>

        <div class="bg-white rounded-xl shadow-sm p-6 border border-gray-100">
          <div class="flex items-center gap-4">
            <div class="w-12 h-12 bg-green-100 rounded-xl flex items-center justify-center">
              <svg class="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div>
              <p class="text-sm text-gray-500">Today</p>
              <p class="text-2xl font-bold text-gray-900">{{ stats.today }}</p>
            </div>
          </div>
        </div>

        <div class="bg-white rounded-xl shadow-sm p-6 border border-gray-100">
          <div class="flex items-center gap-4">
            <div class="w-12 h-12 bg-indigo-100 rounded-xl flex items-center justify-center">
              <svg class="w-6 h-6 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
              </svg>
            </div>
            <div>
              <p class="text-sm text-gray-500">Upcoming</p>
              <p class="text-2xl font-bold text-gray-900">{{ stats.upcoming }}</p>
            </div>
          </div>
        </div>

        <div class="bg-white rounded-xl shadow-sm p-6 border border-gray-100">
          <div class="flex items-center gap-4">
            <div class="w-12 h-12 bg-red-100 rounded-xl flex items-center justify-center">
              <svg class="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>
            <div>
              <p class="text-sm text-gray-500">Cancelled</p>
              <p class="text-2xl font-bold text-gray-900">{{ stats.cancelled }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Appointments Table -->
      <div class="bg-white rounded-xl shadow-sm border border-gray-100">
        <!-- Table Header -->
        <div class="px-6 py-4 border-b border-gray-100">
          <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <h2 class="text-lg font-semibold text-gray-900">All Appointments</h2>
            <div class="flex flex-col sm:flex-row gap-3">
              <!-- Search -->
              <div class="relative">
                <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                <input
                  v-model="searchQuery"
                  type="text"
                  placeholder="Search appointments..."
                  class="pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent w-full sm:w-64"
                />
              </div>
              <!-- Filter -->
              <select
                v-model="statusFilter"
                class="px-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="all">All Status</option>
                <option value="confirmed">Confirmed</option>
                <option value="pending">Pending</option>
                <option value="cancelled">Cancelled</option>
              </select>
            </div>
          </div>
        </div>

        <!-- Table Body -->
        <div class="overflow-x-auto">
          <table class="w-full">
            <thead>
              <tr class="bg-gray-50">
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Appointment</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date & Time</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Attendees</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-100">
              <tr
                v-for="apt in filteredAppointments"
                :key="apt.id"
                class="hover:bg-gray-50 transition-colors"
              >
                <td class="px-6 py-4">
                  <div>
                    <p class="text-sm font-medium text-gray-900">{{ apt.title }}</p>
                    <p class="text-xs text-gray-500 mt-1">{{ apt.description || 'No description' }}</p>
                  </div>
                </td>
                <td class="px-6 py-4">
                  <div>
                    <p class="text-sm text-gray-900">{{ formatDate(apt.start) }}</p>
                    <p class="text-xs text-gray-500">{{ formatTime(apt.start) }} - {{ formatTime(apt.end) }}</p>
                  </div>
                </td>
                <td class="px-6 py-4">
                  <div class="flex flex-wrap gap-1">
                    <span
                      v-for="attendee in apt.attendees.slice(0, 2)"
                      :key="attendee"
                      class="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded-full"
                    >
                      {{ attendee.split('@')[0] }}
                    </span>
                    <span
                      v-if="apt.attendees.length > 2"
                      class="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded-full"
                    >
                      +{{ apt.attendees.length - 2 }}
                    </span>
                  </div>
                </td>
                <td class="px-6 py-4">
                  <span :class="['px-2 py-1 text-xs font-medium rounded-full', getStatusColor(apt.status)]">
                    {{ apt.status || 'confirmed' }}
                  </span>
                </td>
                <td class="px-6 py-4 text-right">
                  <div class="flex items-center justify-end gap-2">
                    <button
                      @click="viewAppointment(apt)"
                      class="p-1.5 text-gray-400 hover:text-blue-600 transition-colors"
                      title="View details"
                    >
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                      </svg>
                    </button>
                    <button
                      @click="deleteAppointment(apt.id)"
                      class="p-1.5 text-gray-400 hover:text-red-600 transition-colors"
                      title="Delete"
                    >
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>
                </td>
              </tr>
              <tr v-if="filteredAppointments.length === 0">
                <td colspan="5" class="px-6 py-12 text-center">
                  <div class="text-gray-500">
                    <svg class="w-12 h-12 mx-auto mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                    <p class="text-sm font-medium">No appointments found</p>
                    <p class="text-xs mt-1">Try adjusting your search or filter</p>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </main>

    <!-- Appointment Detail Modal -->
    <div
      v-if="selectedAppointment"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      @click.self="closeModal"
    >
      <div class="bg-white rounded-xl shadow-2xl max-w-lg w-full mx-4 overflow-hidden">
        <div class="bg-gradient-to-r from-indigo-500 to-purple-600 px-6 py-4">
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
                {{ formatDate(selectedAppointment.start) }}
              </p>
              <p class="text-gray-500">
                {{ formatTime(selectedAppointment.start) }} - {{ formatTime(selectedAppointment.end) }}
              </p>
            </div>
          </div>

          <div class="flex items-center gap-3 text-sm">
            <svg class="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span :class="['px-2 py-1 text-xs font-medium rounded-full', getStatusColor(selectedAppointment.status)]">
              {{ selectedAppointment.status || 'confirmed' }}
            </span>
          </div>

          <div v-if="selectedAppointment.attendees.length > 0" class="flex items-start gap-3 text-sm">
            <svg class="w-5 h-5 text-gray-400 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            <div class="flex flex-wrap gap-2">
              <span
                v-for="attendee in selectedAppointment.attendees"
                :key="attendee"
                class="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded-full"
              >
                {{ attendee }}
              </span>
            </div>
          </div>

          <div v-if="selectedAppointment.description" class="flex items-start gap-3 text-sm">
            <svg class="w-5 h-5 text-gray-400 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h7" />
            </svg>
            <p class="text-gray-700">{{ selectedAppointment.description }}</p>
          </div>
        </div>

        <div class="px-6 py-4 bg-gray-50 border-t border-gray-100">
          <div class="flex flex-col sm:flex-row gap-3">
            <div class="flex-1 flex gap-2">
              <button
                v-if="selectedAppointment.status !== 'confirmed'"
                @click="updateStatus(selectedAppointment.id, 'confirmed'); closeModal()"
                class="flex-1 px-3 py-2 text-sm font-medium text-green-700 bg-green-50 border border-green-200 rounded-lg hover:bg-green-100 transition-colors"
              >
                Confirm
              </button>
              <button
                v-if="selectedAppointment.status !== 'pending'"
                @click="updateStatus(selectedAppointment.id, 'pending'); closeModal()"
                class="flex-1 px-3 py-2 text-sm font-medium text-yellow-700 bg-yellow-50 border border-yellow-200 rounded-lg hover:bg-yellow-100 transition-colors"
              >
                Mark Pending
              </button>
            </div>
            <div class="flex gap-2">
              <button
                class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                @click="closeModal"
              >
                Close
              </button>
              <button
                class="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
                @click="deleteAppointment(selectedAppointment.id)"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
