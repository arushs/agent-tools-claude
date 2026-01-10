import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Appointment } from '../types'

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
      if (!response.ok) {
        throw new Error('Failed to fetch appointments')
      }
      appointments.value = await response.json()
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Unknown error'
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

      if (!response.ok) {
        throw new Error('Failed to create appointment')
      }

      const created = await response.json()
      appointments.value.push(created)
      return created
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Unknown error'
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

      if (!response.ok) {
        throw new Error('Failed to delete appointment')
      }

      appointments.value = appointments.value.filter((apt) => apt.id !== id)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Unknown error'
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
