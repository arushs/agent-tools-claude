import { test, expect } from '@playwright/test'

test.describe('Landing Page', () => {
  test('should display landing page with welcome content', async ({ page }) => {
    await page.goto('/')

    // Check landing page elements - the title is split across lines
    await expect(page.getByText('AI Scheduling')).toBeVisible()
    await expect(page.getByText('Assistant')).toBeVisible()
    await expect(page.getByText(/Book meetings with natural language/i)).toBeVisible()

    // Check feature pills are displayed (exact match to avoid ambiguity)
    await expect(page.getByText('Natural Language', { exact: true })).toBeVisible()
    await expect(page.getByText('Instant Updates', { exact: true })).toBeVisible()
    await expect(page.getByText('Conflict Detection', { exact: true })).toBeVisible()
  })

  test('should have working Try the Demo button', async ({ page }) => {
    await page.goto('/')

    // Find and click the Try the Demo button
    const startButton = page.getByRole('button', { name: /Try the Demo/i })
    await expect(startButton).toBeVisible()
    await startButton.click()

    // Should navigate to demo app
    await expect(page.getByRole('heading', { name: /AI Scheduling Assistant/i })).toBeVisible()
    await expect(page.getByText(/Demo Mode/i)).toBeVisible()
  })
})

test.describe('Calendar View', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await page.getByRole('button', { name: /Try the Demo/i }).click()
  })

  test('should display calendar with demo appointments', async ({ page }) => {
    // Calendar should be visible
    await expect(page.locator('.fc')).toBeVisible() // FullCalendar container

    // Should show calendar navigation
    await expect(page.locator('.fc-toolbar')).toBeVisible()

    // Demo appointments should appear (Team Standup is scheduled for today)
    await expect(page.getByText(/Team Standup/i)).toBeVisible({ timeout: 5000 })
  })

  test('should switch between calendar and list views', async ({ page }) => {
    // Calendar view should be active by default
    const calendarButton = page.getByRole('button', { name: /Calendar/i })
    const listButton = page.getByRole('button', { name: /List/i })

    await expect(calendarButton).toBeVisible()
    await expect(listButton).toBeVisible()

    // Switch to list view
    await listButton.click()

    // List view should show appointments
    await expect(page.getByText(/Team Standup/i)).toBeVisible()
    await expect(page.getByText(/Lunch with Sarah/i)).toBeVisible()

    // Switch back to calendar
    await calendarButton.click()
    await expect(page.locator('.fc')).toBeVisible()
  })

  test('should click on appointment to view details', async ({ page }) => {
    // Click on an appointment in calendar
    await page.getByText(/Team Standup/i).first().click()

    // Modal should open with appointment details
    await expect(page.getByText(/Daily team sync/i)).toBeVisible()
    await expect(page.getByRole('button', { name: /Close/i })).toBeVisible()
    await expect(page.getByRole('button', { name: /Cancel Appointment/i })).toBeVisible()

    // Close modal
    await page.getByRole('button', { name: /Close/i }).click()
    await expect(page.getByText(/Daily team sync/i)).not.toBeVisible()
  })
})

test.describe('Chat Interface', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await page.getByRole('button', { name: /Try the Demo/i }).click()
  })

  test('should display chat panel with welcome message', async ({ page }) => {
    // Chat panel should be visible
    await expect(page.getByText(/Chat with AI/i)).toBeVisible()

    // Connection indicator should show connected (green)
    const connectionDot = page.locator('[title="Connected"]')
    await expect(connectionDot).toBeVisible()

    // Welcome message should display
    await expect(page.getByText(/Welcome! I'm your scheduling assistant/i)).toBeVisible()
    await expect(page.getByText(/Book a meeting tomorrow at 2pm/i)).toBeVisible()
  })

  test('should send message and receive response', async ({ page }) => {
    // Type a greeting
    const input = page.getByPlaceholder(/Type a message/i)
    await expect(input).toBeVisible()

    await input.fill('Hello')
    await page.getByRole('button').filter({ has: page.locator('svg') }).last().click()

    // User message should appear
    await expect(page.getByText('Hello').last()).toBeVisible()

    // Should show typing indicator, then response
    await expect(page.getByText(/scheduling assistant/i).last()).toBeVisible({ timeout: 5000 })
  })

  test('should handle schedule query', async ({ page }) => {
    const input = page.getByPlaceholder(/Type a message/i)

    await input.fill("What's on my schedule today?")
    await input.press('Enter')

    // Wait for response
    await expect(page.getByText(/Team Standup/i).last()).toBeVisible({ timeout: 5000 })
    await expect(page.getByText(/Lunch with Sarah/i).last()).toBeVisible()
  })

  test('should clear chat history', async ({ page }) => {
    const input = page.getByPlaceholder(/Type a message/i)

    // Send a message first
    await input.fill('Hello')
    await input.press('Enter')

    // Wait for response
    await expect(page.getByText(/scheduling assistant/i).last()).toBeVisible({ timeout: 5000 })

    // Clear chat
    page.on('dialog', dialog => dialog.accept())
    await page.getByRole('button', { name: /Clear/i }).click()

    // Chat should be cleared, welcome message should reappear
    await expect(page.getByText(/Welcome! I'm your scheduling assistant/i)).toBeVisible()
  })
})

test.describe('Booking Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await page.getByRole('button', { name: /Try the Demo/i }).click()
  })

  test('should book appointment via chat and see it in calendar', async ({ page }) => {
    const input = page.getByPlaceholder(/Type a message/i)

    // Book a meeting
    await input.fill('Book a meeting with John tomorrow at 3pm')
    await input.press('Enter')

    // Wait for confirmation response
    await expect(page.getByText(/Done! I've booked/i)).toBeVisible({ timeout: 5000 })
    await expect(page.getByText(/Meeting with John/i).last()).toBeVisible()

    // Navigate calendar to tomorrow to verify (if needed)
    // The meeting should appear in the calendar
    await page.locator('.fc-next-button').click() // Go to next day/week
    await expect(page.getByText(/Meeting with John/i).first()).toBeVisible({ timeout: 5000 })
  })

  test('should check availability before booking', async ({ page }) => {
    const input = page.getByPlaceholder(/Type a message/i)

    // Check if free
    await input.fill('Am I free tomorrow at 3pm?')
    await input.press('Enter')

    // Should get availability response
    await expect(page.getByText(/you're free/i)).toBeVisible({ timeout: 5000 })
  })

  test('should detect conflicts when booking', async ({ page }) => {
    const input = page.getByPlaceholder(/Type a message/i)

    // Try to book at a time that conflicts with Team Standup (9am today)
    await input.fill('Book a meeting today at 9am')
    await input.press('Enter')

    // Should report conflict
    await expect(page.getByText(/conflict/i)).toBeVisible({ timeout: 5000 })
  })

  test('should delete appointment from modal', async ({ page }) => {
    // Click on an appointment
    await page.getByText(/Team Standup/i).first().click()

    // Wait for modal and click Cancel Appointment
    await expect(page.getByRole('button', { name: /Cancel Appointment/i })).toBeVisible()
    await page.getByRole('button', { name: /Cancel Appointment/i }).click()

    // Modal should close and appointment should be removed
    await expect(page.getByRole('button', { name: /Cancel Appointment/i })).not.toBeVisible()

    // Appointment should no longer appear in calendar
    await expect(page.locator('.fc-event').filter({ hasText: /Team Standup/i })).not.toBeVisible()
  })
})

test.describe('Navigation', () => {
  test('should go back to landing page', async ({ page }) => {
    await page.goto('/')
    await page.getByRole('button', { name: /Try the Demo/i }).click()

    // Find and click back button
    const backButton = page.getByRole('button', { name: /Back to landing/i })
    await expect(backButton).toBeVisible()
    await backButton.click()

    // Should be back on landing page
    await expect(page.getByRole('button', { name: /Try the Demo/i })).toBeVisible()
  })
})

test.describe('Error-free Operation', () => {
  test('should complete full demo flow without console errors', async ({ page }) => {
    const consoleErrors: string[] = []

    // Listen for console errors
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text())
      }
    })

    // Landing page
    await page.goto('/')
    await page.getByRole('button', { name: /Try the Demo/i }).click()

    // Wait for demo to load
    await expect(page.getByText(/Demo Mode/i)).toBeVisible()
    await expect(page.locator('.fc')).toBeVisible()

    // Interact with chat
    const input = page.getByPlaceholder(/Type a message/i)
    await input.fill('Hello')
    await input.press('Enter')
    await expect(page.getByText(/scheduling assistant/i).last()).toBeVisible({ timeout: 5000 })

    // Book an appointment
    await input.fill('Book a meeting tomorrow at 4pm')
    await input.press('Enter')
    await expect(page.getByText(/Done! I've booked/i)).toBeVisible({ timeout: 5000 })

    // Switch views
    await page.getByRole('button', { name: /List/i }).click()
    await expect(page.getByText(/Team Standup/i)).toBeVisible()

    await page.getByRole('button', { name: /Calendar/i }).click()
    await expect(page.locator('.fc')).toBeVisible()

    // Navigate back
    await page.getByRole('button', { name: /Back to landing/i }).click()
    await expect(page.getByRole('button', { name: /Try the Demo/i })).toBeVisible()

    // Verify no console errors occurred
    expect(consoleErrors).toEqual([])
  })
})
