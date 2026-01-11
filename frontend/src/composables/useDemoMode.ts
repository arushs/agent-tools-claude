import { ref, computed } from 'vue'
import { useChatStore } from '../stores/chat'
import { useAppointmentsStore } from '../stores/appointments'
import type { Appointment } from '../types'
import { addDays, format, setHours, setMinutes, addHours, startOfDay, parseISO } from 'date-fns'

// Demo mode operates entirely client-side with mock calendar

const demoMode = ref(false)
const demoConnected = ref(false)

// Demo data - some pre-existing appointments
function generateDemoAppointments(): Appointment[] {
  const today = startOfDay(new Date())

  return [
    {
      id: 'demo-1',
      title: 'Team Standup',
      start: setMinutes(setHours(today, 9), 0).toISOString(),
      end: setMinutes(setHours(today, 9), 30).toISOString(),
      attendees: ['team@example.com'],
      description: 'Daily team sync',
      status: 'confirmed',
    },
    {
      id: 'demo-2',
      title: 'Lunch with Sarah',
      start: setMinutes(setHours(today, 12), 0).toISOString(),
      end: setMinutes(setHours(today, 13), 0).toISOString(),
      attendees: ['sarah@example.com'],
      description: 'Catch up over lunch',
      status: 'confirmed',
    },
    {
      id: 'demo-3',
      title: 'Project Review',
      start: setMinutes(setHours(addDays(today, 1), 14), 0).toISOString(),
      end: setMinutes(setHours(addDays(today, 1), 15), 0).toISOString(),
      attendees: ['manager@example.com', 'team@example.com'],
      description: 'Q1 project review',
      status: 'confirmed',
    },
    {
      id: 'demo-4',
      title: 'Client Call',
      start: setMinutes(setHours(addDays(today, 2), 10), 0).toISOString(),
      end: setMinutes(setHours(addDays(today, 2), 11), 0).toISOString(),
      attendees: ['client@acme.com'],
      description: 'Quarterly business review with Acme Corp',
      status: 'confirmed',
    },
  ]
}

// Parse natural language time expressions
function parseTimeExpression(text: string): { date: Date; duration: number } | null {
  const now = new Date()
  const today = startOfDay(now)
  let targetDate: Date | null = null
  let hour = 14 // default to 2pm
  let minute = 0
  let duration = 60 // default 1 hour

  // Parse relative days
  const lowerText = text.toLowerCase()

  if (lowerText.includes('today')) {
    targetDate = today
  } else if (lowerText.includes('tomorrow')) {
    targetDate = addDays(today, 1)
  } else if (lowerText.includes('monday')) {
    targetDate = getNextDayOfWeek(today, 1)
  } else if (lowerText.includes('tuesday')) {
    targetDate = getNextDayOfWeek(today, 2)
  } else if (lowerText.includes('wednesday')) {
    targetDate = getNextDayOfWeek(today, 3)
  } else if (lowerText.includes('thursday')) {
    targetDate = getNextDayOfWeek(today, 4)
  } else if (lowerText.includes('friday')) {
    targetDate = getNextDayOfWeek(today, 5)
  } else if (lowerText.includes('next week')) {
    targetDate = addDays(today, 7)
  } else {
    // Default to today
    targetDate = today
  }

  // Parse time
  const timeMatch = text.match(/(\d{1,2})(?::(\d{2}))?\s*(am|pm)?/i)
  if (timeMatch) {
    hour = parseInt(timeMatch[1])
    minute = timeMatch[2] ? parseInt(timeMatch[2]) : 0
    const ampm = timeMatch[3]?.toLowerCase()
    if (ampm === 'pm' && hour < 12) hour += 12
    if (ampm === 'am' && hour === 12) hour = 0
  }

  // Parse duration
  const durationMatch = text.match(/(\d+)\s*(hour|hr|minute|min)/i)
  if (durationMatch) {
    const value = parseInt(durationMatch[1])
    const unit = durationMatch[2].toLowerCase()
    if (unit.startsWith('hour') || unit.startsWith('hr')) {
      duration = value * 60
    } else {
      duration = value
    }
  }

  targetDate = setMinutes(setHours(targetDate, hour), minute)

  return { date: targetDate, duration }
}

function getNextDayOfWeek(fromDate: Date, dayOfWeek: number): Date {
  const date = new Date(fromDate)
  const currentDay = date.getDay()
  const daysUntil = (dayOfWeek - currentDay + 7) % 7 || 7
  return addDays(date, daysUntil)
}

// Extract meeting title from natural language
function extractTitle(text: string): string {
  const lowerText = text.toLowerCase()

  // Try to extract "with [name]" pattern
  const withMatch = text.match(/(?:meeting|appointment|call|chat)\s+with\s+([A-Za-z\s]+?)(?:\s+(?:at|on|tomorrow|today|monday|tuesday|wednesday|thursday|friday|for|\d))/i)
  if (withMatch) {
    return `Meeting with ${withMatch[1].trim()}`
  }

  // Try to extract quoted title
  const quotedMatch = text.match(/"([^"]+)"/)
  if (quotedMatch) {
    return quotedMatch[1]
  }

  // Try to extract "a [something] meeting" pattern
  const typeMatch = text.match(/(?:a|an)\s+([A-Za-z\s]+?)\s+(?:meeting|call|appointment)/i)
  if (typeMatch) {
    const type = typeMatch[1].trim()
    return type.charAt(0).toUpperCase() + type.slice(1) + ' Meeting'
  }

  // Default titles based on keywords
  if (lowerText.includes('standup')) return 'Standup Meeting'
  if (lowerText.includes('review')) return 'Review Meeting'
  if (lowerText.includes('call')) return 'Phone Call'
  if (lowerText.includes('lunch')) return 'Lunch Meeting'
  if (lowerText.includes('coffee')) return 'Coffee Chat'
  if (lowerText.includes('interview')) return 'Interview'
  if (lowerText.includes('1:1') || lowerText.includes('1-1')) return '1:1 Meeting'

  return 'Meeting'
}

// Check for conflicts
function checkConflicts(appointments: Appointment[], start: Date, end: Date): Appointment[] {
  return appointments.filter(apt => {
    const aptStart = parseISO(apt.start)
    const aptEnd = parseISO(apt.end)

    // Check if there's any overlap
    return (
      (start >= aptStart && start < aptEnd) ||
      (end > aptStart && end <= aptEnd) ||
      (start <= aptStart && end >= aptEnd)
    )
  })
}

// Generate AI-like responses
function generateResponse(
  message: string,
  appointments: Appointment[]
): { response: string; newAppointment?: Appointment } {
  const lowerMessage = message.toLowerCase()

  // Handle schedule/calendar queries
  if (lowerMessage.includes('schedule') || lowerMessage.includes("what's on") || lowerMessage.includes('calendar')) {
    const today = startOfDay(new Date())
    const todayEnd = addHours(today, 24)

    let targetDate = today
    let targetEnd = todayEnd
    let dateLabel = 'today'

    if (lowerMessage.includes('tomorrow')) {
      targetDate = addDays(today, 1)
      targetEnd = addDays(todayEnd, 1)
      dateLabel = 'tomorrow'
    } else if (lowerMessage.includes('this week')) {
      targetEnd = addDays(today, 7)
      dateLabel = 'this week'
    }

    const relevant = appointments.filter(apt => {
      const aptDate = parseISO(apt.start)
      return aptDate >= targetDate && aptDate < targetEnd
    })

    if (relevant.length === 0) {
      return { response: `You have no appointments scheduled for ${dateLabel}. Would you like me to book something?` }
    }

    const aptList = relevant.map(apt => {
      const start = parseISO(apt.start)
      return `• ${apt.title} at ${format(start, 'h:mm a')}`
    }).join('\n')

    return { response: `Here's your schedule for ${dateLabel}:\n\n${aptList}` }
  }

  // Handle availability queries
  if (lowerMessage.includes('free') || lowerMessage.includes('available') || lowerMessage.includes('availability')) {
    const timeInfo = parseTimeExpression(message)
    if (timeInfo) {
      const start = timeInfo.date
      const end = addHours(start, 1)
      const conflicts = checkConflicts(appointments, start, end)

      if (conflicts.length === 0) {
        return { response: `Yes, you're free at ${format(start, 'h:mm a')} on ${format(start, 'EEEE, MMMM d')}. Would you like me to book something?` }
      } else {
        return { response: `You have ${conflicts[0].title} scheduled at that time. Would you like to check another time?` }
      }
    }
    return { response: "I can check your availability. What day and time are you interested in?" }
  }

  // Handle booking requests
  if (lowerMessage.includes('book') || lowerMessage.includes('schedule') || lowerMessage.includes('set up') ||
      lowerMessage.includes('create') || lowerMessage.includes('add')) {
    const timeInfo = parseTimeExpression(message)
    if (timeInfo) {
      const start = timeInfo.date
      const end = new Date(start.getTime() + timeInfo.duration * 60000)
      const title = extractTitle(message)

      // Check for conflicts
      const conflicts = checkConflicts(appointments, start, end)
      if (conflicts.length > 0) {
        return {
          response: `There's a conflict with "${conflicts[0].title}" at that time. Would you like to book a different time?`
        }
      }

      // Create the appointment
      const newAppointment: Appointment = {
        id: `demo-${Date.now()}`,
        title,
        start: start.toISOString(),
        end: end.toISOString(),
        attendees: [],
        description: '',
        status: 'confirmed',
      }

      return {
        response: `Done! I've booked "${title}" for ${format(start, 'EEEE, MMMM d')} at ${format(start, 'h:mm a')}. You can see it on your calendar now.`,
        newAppointment,
      }
    }
    return { response: "I'd be happy to book that for you. What day and time would you like?" }
  }

  // Handle cancellation
  if (lowerMessage.includes('cancel') || lowerMessage.includes('delete') || lowerMessage.includes('remove')) {
    return { response: "To cancel an appointment, click on it in the calendar and select 'Cancel Appointment'." }
  }

  // Handle greetings
  if (lowerMessage.includes('hello') || lowerMessage.includes('hi') || lowerMessage.includes('hey')) {
    return { response: "Hello! I'm your scheduling assistant. I can help you:\n\n• Book new meetings\n• Check your schedule\n• Find available time slots\n\nWhat would you like to do?" }
  }

  // Handle thanks
  if (lowerMessage.includes('thank')) {
    return { response: "You're welcome! Let me know if you need anything else." }
  }

  // Default response
  return {
    response: "I can help you manage your calendar. Try asking me to:\n\n• \"Book a meeting tomorrow at 2pm\"\n• \"What's on my schedule today?\"\n• \"Am I free on Friday at 3pm?\""
  }
}

export function useDemoMode() {
  const chatStore = useChatStore()
  const appointmentsStore = useAppointmentsStore()

  function enableDemoMode() {
    demoMode.value = true
    // Initialize with demo appointments
    const demoAppointments = generateDemoAppointments()
    appointmentsStore.appointments = demoAppointments
    demoConnected.value = true
    chatStore.setSessionId('demo-session')
  }

  function disableDemoMode() {
    demoMode.value = false
    demoConnected.value = false
  }

  async function sendDemoMessage(content: string) {
    if (!demoMode.value) return

    // Add user message
    chatStore.addMessage({ role: 'user', content })
    chatStore.setProcessing(true)

    // Simulate AI thinking delay
    await new Promise(resolve => setTimeout(resolve, 800 + Math.random() * 700))

    // Generate response
    const { response, newAppointment } = generateResponse(content, appointmentsStore.appointments)

    if (newAppointment) {
      appointmentsStore.appointments.push(newAppointment)
    }

    chatStore.setProcessing(false)
    chatStore.addMessage({ role: 'assistant', content: response })
  }

  function clearDemoHistory() {
    chatStore.clearMessages()
  }

  return {
    demoMode: computed(() => demoMode.value),
    connected: computed(() => demoConnected.value),
    enableDemoMode,
    disableDemoMode,
    sendMessage: sendDemoMessage,
    clearHistory: clearDemoHistory,
  }
}
