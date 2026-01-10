<script setup lang="ts">
import { computed } from 'vue'
import FullCalendar from '@fullcalendar/vue3'
import dayGridPlugin from '@fullcalendar/daygrid'
import timeGridPlugin from '@fullcalendar/timegrid'
import interactionPlugin from '@fullcalendar/interaction'
import type { EventClickArg } from '@fullcalendar/core'
import { useAppointmentsStore } from '../../stores/appointments'

const emit = defineEmits<{
  eventClick: [id: string]
}>()

const appointmentsStore = useAppointmentsStore()

const calendarEvents = computed(() => {
  return appointmentsStore.appointments.map((apt) => ({
    id: apt.id,
    title: apt.title,
    start: apt.start,
    end: apt.end,
    backgroundColor: '#3b82f6',
    borderColor: '#2563eb',
  }))
})

const calendarOptions = computed(() => ({
  plugins: [dayGridPlugin, timeGridPlugin, interactionPlugin],
  initialView: 'timeGridWeek',
  headerToolbar: {
    left: 'prev,next today',
    center: 'title',
    right: 'dayGridMonth,timeGridWeek,timeGridDay',
  },
  events: calendarEvents.value,
  editable: false,
  selectable: true,
  selectMirror: true,
  dayMaxEvents: true,
  weekends: true,
  nowIndicator: true,
  slotMinTime: '07:00:00',
  slotMaxTime: '20:00:00',
  height: '100%',
  eventClick: handleEventClick,
}))

function handleEventClick(info: EventClickArg) {
  emit('eventClick', info.event.id)
}
</script>

<template>
  <div class="h-full bg-white rounded-lg shadow p-4">
    <FullCalendar :options="calendarOptions" />
  </div>
</template>
