# Agent Tools Claude

Demos showcasing AI agent tools with Claude, including voice processing and calendar integration.

## Installation

```bash
pip install -e ".[dev]"
```

## Configuration

Copy `.env.example` to `.env` and fill in your API keys:

```bash
cp .env.example .env
```

Required API keys:
- `ANTHROPIC_API_KEY` - Your Anthropic API key for Claude
- `OPENAI_API_KEY` - Your OpenAI API key for speech-to-text/text-to-speech
- `GOOGLE_CREDENTIALS_PATH` - Path to your Google OAuth credentials JSON file

## Project Structure

```
src/agent_demos/
  core/           # Core infrastructure (Claude client wrapper, etc.)
  voice/          # Voice processing utilities
  scheduling/     # Calendar integration
  demos/
    appointment_booking/  # Appointment booking demo
```

## Development

Run tests:
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

## License

MIT
