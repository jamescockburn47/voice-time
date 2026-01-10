# TimeBrief

Voice-first time recording for lawyers. Built with local AI - your data never leaves your machine.

## Quick Start

**Windows:**
```
TimeBrief.bat
```

This launches the native desktop app with full voice control.

## How It Works

1. **Plan your day** - Tell TimeBrief what you're working on today
2. **Start a timer** - Say "working on Smith matter" and a timer begins
3. **Switch tasks** - Just say what you're doing next
4. **Review and export** - Clean, billable entries ready for your system

## Features

- **Voice Control** - Ctrl+Space to talk, no typing required
- **Local AI** - Ollama + Whisper run entirely on your machine
- **Smart Matching** - Recognizes matters, activities, and planned tasks
- **6-Minute Billing** - Automatic calculation of billable units
- **AI Chat** - Ask questions about your time data
- **Zero Cloud** - 100% private, offline-capable

## Technology

- Python + Flask (backend)
- Tauri (native desktop wrapper)
- Ollama with Qwen2.5 (local LLM)
- faster-whisper (speech-to-text)
- SQLite (local database)

## Requirements

- Windows 10/11
- Python 3.11+
- 8GB+ RAM recommended
- Microphone for voice input

## Building

**Development:**
```
TimeBrief.bat
```

**Production installer:**
```
BUILD.bat
```

Creates `TimeBrief_x.x.x_x64-setup.exe` in `src-tauri/target/release/bundle/nsis/`

## Configuration

Edit `config.yaml` to change:
- AI models (Whisper size, Ollama model)
- Working hours
- Matching thresholds

## Data Storage

All data stored locally at `~/.voice_time/voice_time.db`

## License

MIT

## Author

James Cockburn - [jamescockburn.io](https://jamescockburn.io)
