# TimeBrief

**Voice-powered time tracking for lawyers.** Built with 100% local AI - your data never leaves your machine.

> ⚡ Vibe-coded in 24 hours as a proof of concept

---

## Download & Install

### For End Users (Easiest)

1. Go to [Releases](https://github.com/jamescockburn47/voice-time/releases)
2. Download `TimeBrief_x.x.x_x64-setup.exe`
3. Run the installer
4. Launch TimeBrief from your desktop

**First launch:** The app automatically installs AI models (~400MB). This takes 2-5 minutes - just wait for the main window to appear.

**Requirements:** Windows 10/11, 4GB+ RAM. Works on any machine - **no GPU required**.

---

## What It Does

1. **Plan your day** → Tell TimeBrief what you're working on
2. **Start a timer** → Say "working on Smith matter, research"
3. **Switch tasks** → Just say what you're doing next
4. **Voice memos** → Dictate case notes and action items
5. **Review & export** → Clean billable entries ready for your system

---

## Key Features

| Feature | Description |
|---------|-------------|
| 🎤 **Voice Control** | Click or Ctrl+Space to record |
| 🔒 **100% Local** | AI runs on your machine, zero cloud |
| 🧠 **Smart Matching** | Recognizes matters, activities, and tasks |
| 📝 **Voice Memos** | Dictate thoughts and actions per case |
| ⏱️ **6-Minute Billing** | Automatic billable unit calculation |
| 💬 **AI Chat** | Ask questions about your time data |

---

## Technology

- **Ollama** - Local LLM (qwen2.5) for understanding intent
- **faster-whisper** - Local speech-to-text
- **Tauri** - Native Windows app
- **SQLite** - Local database

Everything runs on CPU. If you have an NVIDIA GPU, it's used automatically for faster performance.

---

## For Developers

### Running from Source

```bash
git clone https://github.com/jamescockburn47/voice-time.git
cd voice-time
TimeBrief.bat
```

The batch file handles:
- Python virtual environment
- Dependencies installation
- Ollama setup
- Launching the app

### Building the Installer

```bash
BUILD.bat
```

Creates `TimeBrief_x.x.x_x64-setup.exe` in `src-tauri/target/release/bundle/nsis/`

Requires: Python 3.11+, Rust/Cargo

---

## Data Storage

All data stored locally:
```
C:\Users\YOU\.voice_time\
├── timebrief.db      # Your time entries
└── config.yaml       # Auto-generated settings
```

---

## Troubleshooting

**App shows blank screen?**  
Wait 30 seconds - the backend is still starting.

**Voice not working?**  
Allow microphone permission when prompted.

**Ollama errors?**  
Download manually from [ollama.com](https://ollama.com/download), then restart TimeBrief.

---

## Links

- **Author:** [jamescockburn.io](https://www.jamescockburn.io)
- **Other Projects:** [Humane Calendar](https://www.humanecalendar.com)

---

MIT License
