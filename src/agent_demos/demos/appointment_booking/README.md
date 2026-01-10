# Appointment Booking Demo

A voice-enabled appointment booking assistant that combines the VoiceAgent with Google Calendar integration. Speak naturally to book meetings, check availability, and manage your schedule.

## Features

- **Voice interaction**: Uses speech-to-text and text-to-speech for natural conversation
- **Calendar integration**: Connects to Google Calendar to check availability and create events
- **Natural language processing**: Understands relative dates like "tomorrow", "next Monday"
- **Smart scheduling**: Checks for conflicts before booking

## Prerequisites

1. **API Keys**: Set up the following in your `.env` file:
   ```
   ANTHROPIC_API_KEY=your_anthropic_api_key
   OPENAI_API_KEY=your_openai_api_key
   GOOGLE_CREDENTIALS_PATH=/path/to/credentials.json
   ```

2. **Google Calendar OAuth Setup**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one
   - Enable the Google Calendar API
   - Create OAuth 2.0 credentials (Desktop application type)
   - Download the credentials JSON file
   - Set `GOOGLE_CREDENTIALS_PATH` to the file location

3. **Audio Setup**: Ensure your system has a working microphone and speakers

## Installation

From the project root:

```bash
pip install -e ".[dev]"
```

## Usage

### Voice Mode (Default)

Run the demo with voice interaction:

```bash
python -m agent_demos.demos.appointment_booking.main
```

Or directly:

```bash
cd src
python -m agent_demos.demos.appointment_booking.main
```

The assistant will greet you and listen for your requests. Say "goodbye" or "exit" to end.

### Text Mode

For testing without audio hardware:

```bash
python -m agent_demos.demos.appointment_booking.main --text
```

## Example Interactions

| You Say | What Happens |
|---------|--------------|
| "Book me a meeting with John tomorrow at 2pm" | Checks availability, creates a 1-hour meeting |
| "Am I free on Friday at 3pm?" | Returns availability status |
| "Schedule a team standup for Monday at 9am for 30 minutes" | Creates a 30-minute event |
| "What's on my calendar today?" | Lists today's events |

## Architecture

```
main.py
├── VoiceAgent (from agent_demos.voice)
│   ├── SpeechToText (OpenAI Whisper)
│   ├── ClaudeClient (Anthropic API)
│   └── TextToSpeech (OpenAI TTS)
│
├── SchedulingToolExecutor
│   └── Google Calendar API
│
└── Tools registered with Claude:
    ├── get_todays_date
    ├── check_calendar_availability
    └── create_calendar_event
```

## Flow

1. **Listen**: VoiceAgent records and transcribes user speech
2. **Process**: Claude interprets the request and calls scheduling tools
3. **Execute**: Tools interact with Google Calendar API
4. **Respond**: Claude generates a response based on tool results
5. **Speak**: VoiceAgent synthesizes and plays the response

## First Run

On first run, you'll be prompted to authorize the app with your Google account:

1. A browser window will open for Google OAuth
2. Sign in and grant calendar access
3. The app saves a `token.json` for future sessions

## Troubleshooting

**"GOOGLE_CREDENTIALS_PATH environment variable not set"**
- Ensure your `.env` file contains the path to your OAuth credentials JSON

**"Audio device not found"**
- Check that your microphone is connected and permissions are granted
- Use `--text` mode to test without audio

**"API key required"**
- Verify `ANTHROPIC_API_KEY` and `OPENAI_API_KEY` are set in `.env`

**Calendar authorization fails**
- Ensure the Google Calendar API is enabled in your GCP project
- Verify OAuth credentials are for "Desktop application" type
