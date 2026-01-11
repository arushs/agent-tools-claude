import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Appointment } from '../types'
import { isApiError, getUserFriendlyErrorMessage } from '../types'

export const useAppointmentsStore = defineStore('appointments', () => {
  const appointments = ref<Appointment[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  const sortedAppointments = computed(() => {
    return [...appointments.value].sort(
      (a, b) => new Date(a.start).getTime() - new Date(b.start).getTime()
    )
  })

  const upcomingAppointments = computed(() => {
    const now = new Date()
    return sortedAppointments.value.filter(
      (apt) => new Date(apt.start) >= now
    )
  })

  async function fetchAppointments() {
    loading.value = true
    error.value = null

    try {
      const response = await fetch('/api/appointments')
      const data = await response.json()

      if (!response.ok) {
        if (isApiError(data)) {
          error.value = getUserFriendlyErrorMessage(data)
        } else {
          error.value = `Failed to fetch appointments (${response.status})`
        }
        return
      }

      appointments.value = data
    } catch (e) {
      if (e instanceof TypeError && e.message.includes('fetch')) {
        error.value = 'Unable to connect to server. Please check your connection.'
      } else {
        error.value = e instanceof Error ? e.message : 'Unknown error'
      }
    } finally {
      loading.value = false
    }
  }

  async function createAppointment(appointment: Omit<Appointment, 'id'>) {
    loading.value = true
    error.value = null

    try {
      const response = await fetch('/api/appointments', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(appointment),
      })

      const data = await response.json()

      if (!response.ok) {
        if (isApiError(data)) {
          error.value = getUserFriendlyErrorMessage(data)
        } else {
          error.value = `Failed to create appointment (${response.status})`
        }
        throw new Error(error.value)
      }

      appointments.value.push(data)
      return data
    } catch (e) {
      if (!error.value) {
        if (e instanceof TypeError && e.message.includes('fetch')) {
          error.value = 'Unable to connect to server. Please check your connection.'
        } else {
          error.value = e instanceof Error ? e.message : 'Unknown error'
        }
      }
      throw e
    } finally {
      loading.value = false
    }
  }

  async function deleteAppointment(id: string) {
    loading.value = true
    error.value = null

    try {
      const response = await fetch(`/api/appointments/${id}`, {
        method: 'DELETE',
      })

      // DELETE returns 204 No Content on success
      if (!response.ok) {
        // Try to parse error response
        try {
          const data = await response.json()
          if (isApiError(data)) {
            error.value = getUserFriendlyErrorMessage(data)
          } else {
            error.value = `Failed to delete appointment (${response.status})`
          }
        } catch {
          error.value = `Failed to delete appointment (${response.status})`
        }
        throw new Error(error.value)
      }

      appointments.value = appointments.value.filter((apt) => apt.id !== id)
    } catch (e) {
      if (!error.value) {
        if (e instanceof TypeError && e.message.includes('fetch')) {
          error.value = 'Unable to connect to server. Please check your connection.'
        } else {
          error.value = e instanceof Error ? e.message : 'Unknown error'
        }
      }
      throw e
    } finally {
      loading.value = false
    }
  }

  function handleAppointmentCreated(appointment: Appointment) {
    const exists = appointments.value.some((apt) => apt.id === appointment.id)
    if (!exists) {
      appointments.value.push(appointment)
    }
  }

  function handleAppointmentCancelled(data: { id: string }) {
    appointments.value = appointments.value.filter((apt) => apt.id !== data.id)
  }

  function handleAppointmentsChanged() {
    // Refetch appointments when notified of changes
    fetchAppointments()
  }

  return {
    appointments,
    loading,
    error,
    sortedAppointments,
    upcomingAppointments,
    fetchAppointments,
    createAppointment,
    deleteAppointment,
    handleAppointmentCreated,
    handleAppointmentCancelled,
    handleAppointmentsChanged,
  }
})
