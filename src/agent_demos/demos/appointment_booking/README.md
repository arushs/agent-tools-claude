# AI Scheduling Assistant Demo

A voice-enabled appointment booking assistant that demonstrates natural language scheduling with Claude AI. This demo showcases a complete calendar integration with chat interface.

## Quick Start (Demo Mode)

The demo runs entirely in the browser with mock data - no API keys or backend required!

```bash
# From the project root
./scripts/run-demo.sh

# Or manually:
cd frontend
npm install
npm run dev
```

Then open http://localhost:5173 in your browser.

## Features

- **Natural Language Booking**: Type "Book a meeting tomorrow at 2pm" and see it appear on your calendar
- **Smart Time Parsing**: Understands "tomorrow", "next Monday", "3pm", etc.
- **Conflict Detection**: Warns you about scheduling conflicts
- **Interactive Calendar**: Click events to view details or cancel them
- **List View**: Toggle between calendar and list views

## Example Commands

| You Type | What Happens |
|----------|--------------|
| "Book a meeting with John tomorrow at 2pm" | Creates a 1-hour meeting at 2pm tomorrow |
| "Am I free on Friday at 3pm?" | Checks your availability |
| "What's on my schedule today?" | Lists today's appointments |
| "Schedule a team standup for Monday at 9am" | Creates a morning standup |

## Demo Architecture

```
Frontend (Vue 3 + TypeScript)
├── LandingPage.vue          # Welcome page with feature overview
├── App.vue                  # Main app with calendar + chat
├── CalendarView.vue         # FullCalendar integration
├── composables/
│   └── useDemoMode.ts       # Mock AI responses & calendar logic
└── stores/
    ├── appointments.ts      # Pinia store for calendar events
    └── chat.ts              # Pinia store for messages
```

The demo uses client-side mock data - no backend connection needed.

## Full Backend Mode

For production use with real Google Calendar integration:

### Prerequisites

1. **API Keys** in `.env`:
   ```
   ANTHROPIC_API_KEY=your_anthropic_api_key
   OPENAI_API_KEY=your_openai_api_key
   GOOGLE_CREDENTIALS_PATH=/path/to/credentials.json
   ```

2. **Google Calendar OAuth Setup**:
   - Create OAuth 2.0 credentials in [Google Cloud Console](https://console.cloud.google.com/)
   - Enable the Google Calendar API
   - Download credentials and set `GOOGLE_CREDENTIALS_PATH`

### Running with Backend

```bash
# Terminal 1: Start backend
pip install -e ".[dev]"
uvicorn agent_demos.demos.appointment_booking.app:app --reload

# Terminal 2: Start frontend
cd frontend
npm run dev
```

## Voice Mode

The full version supports voice interaction with:
- **Speech-to-Text**: OpenAI Whisper
- **Text-to-Speech**: OpenAI TTS
- **VoiceAgent**: Integrated voice processing pipeline

Enable voice mode by clicking the microphone icon in the chat panel (requires backend).

## Technology Stack

**Frontend**:
- Vue 3 with Composition API
- TypeScript
- Pinia for state management
- FullCalendar for calendar UI
- TailwindCSS for styling
- Vite for build tooling

**Backend**:
- FastAPI with async support
- WebSocket for real-time chat
- Claude API for natural language
- Google Calendar API integration
