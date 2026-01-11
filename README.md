# Agent Tools Claude

Demos showcasing AI agent tools with Claude, including voice processing and calendar integration.

## Quick Start: Standalone Demo

Run the appointment booking demo **without any API keys** - everything runs in the browser:

```bash
cd frontend
npm install
npm run dev
```

Then open http://localhost:5173 and click "Try the Demo".

**What you can do in demo mode:**
- View calendar with sample appointments
- Chat with the AI to book meetings (e.g., "Book a meeting tomorrow at 2pm")
- Check availability (e.g., "Am I free Friday at 3pm?")
- View your schedule (e.g., "What's on my calendar today?")
- Switch between calendar and list views
- Click appointments to view/cancel them

## Full Installation (with Backend)

For full functionality including voice and real Google Calendar integration:

```bash
pip install -e ".[dev]"
```

### Configuration

Copy `.env.example` to `.env` and fill in your API keys:

```bash
cp .env.example .env
```

Required API keys:
- `ANTHROPIC_API_KEY` - Your Anthropic API key for Claude
- `OPENAI_API_KEY` - Your OpenAI API key for speech-to-text/text-to-speech
- `GOOGLE_CREDENTIALS_PATH` - Path to your Google OAuth credentials JSON file

### Running the Full Stack

```bash
# Terminal 1: Backend
uvicorn agent_demos.demos.appointment_booking.app:app --reload

# Terminal 2: Frontend
cd frontend && npm run dev
```

## Project Structure

```
src/agent_demos/
  core/           # Core infrastructure (Claude client wrapper, etc.)
  voice/          # Voice processing utilities
  scheduling/     # Calendar integration
  demos/
    appointment_booking/  # Appointment booking demo

frontend/         # Vue.js SPA
  src/
    components/   # Vue components (Calendar, Chat, Voice)
    composables/  # Shared logic (useDemoMode, useWebSocket)
    stores/       # Pinia state management
  e2e/           # Playwright E2E tests
```

## Development

### Backend Tests

Run Python unit/integration tests:
```bash
pytest
```

Run linter:
```bash
ruff check .
```

Run type checker:
```bash
mypy src/
```

### Frontend E2E Tests

The frontend includes Playwright end-to-end tests that verify the demo works correctly:

```bash
cd frontend

# Run all E2E tests (headless)
npm run test:e2e

# Run tests with browser UI
npm run test:e2e:headed

# Run tests with Playwright UI for debugging
npm run test:e2e:ui

# Debug tests step-by-step
npm run test:e2e:debug
```

**Test coverage includes:**
- Landing page loads correctly
- Calendar view displays appointments
- Chat interface sends/receives messages
- Booking flow creates appointments visible in calendar
- Conflict detection works
- List view toggle works
- Navigation between views
- No console errors during operation

## License

MIT
