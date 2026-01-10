# Voice Time Recording System

A voice-activated time recording system for litigation lawyers. The core insight: time recording becomes trivial when combined with morning planning - the system knows what you intended to do, so matching "done with that" to the right matter/task is easy.

🔗 **Repository:** [github.com/jamescockburn47/voice-time](https://github.com/jamescockburn47/voice-time)

## ✨ Features

- 🎙️ **Voice Control** - Press Ctrl+Space to talk (no wake words!)
- 🧠 **Smart Context** - Remembers what you're working on
- ⏱️ **Natural Duration** - "couple of hours", "since lunch", etc.
- 📊 **Morning Planning** - Describe your day, system structures it
- 🔄 **Interruption Handling** - Task stack for context switching
- 📝 **Professional Narratives** - Casual speech → billing-ready descriptions
- 💾 **Local-First** - All data stays on your machine
- 🎨 **Beautiful UI** - Inspired by Humane Calendar (navy/gold theme)

## 🚀 Quick Start

### One-Click Install

```bash
⭐ START HERE.bat
```

That's it! The launcher will:
- Install dependencies
- Start Ollama & download AI model
- Create database
- Launch the app

### Choose Your Mode

**Voice Mode (Recommended):**
- Press and hold `Ctrl+Space`
- Speak: "Working on Smith disclosure"
- Release
- System logs automatically!

**Web Mode (Type):**
- Opens in browser
- Type commands instead
- Same functionality

## 📖 Documentation

- **Quick Start:** `SIMPLE_INSTRUCTIONS.txt`
- **Voice Mode:** `VOICE_MODE_INSTRUCTIONS.md`
- **Architecture:** `ARCHITECTURE.md`
- **Development Plan:** `PLAN.md`

## 🛠️ Technology Stack

- **Python 3.11+** - Core application
- **Ollama (Qwen2.5-1.5B)** - Local LLM for parsing & narratives (~1GB)
- **faster-whisper** - Speech-to-text
- **Flask + HTMX** - Web interface
- **SQLite** - Local database
- **pynput** - Global hotkey support

## 💡 Usage Examples

### Morning Planning
```
Ctrl+Space → "Today I need to finish Smith disclosure, draft Brown skeleton, and call with counsel at 3"
✓ Planned 3 tasks across 2 matters
```

### During Day
```
Ctrl+Space → "Working on Smith disclosure"
▶ Started: Smith v Jones - Document Review

(2 hours later)

Ctrl+Space → "Done with the disclosure"
✓ Logged 2.0h to Smith v Jones - Document Review
```

### Interruptions
```
Ctrl+Space → "Quick call about Brown"
▶ Started: Brown v Welsh - Telephone

Ctrl+Space → "Back to what I was doing"
↩ Resumed: Smith v Jones
```

## 🎯 Why This Is Different

1. **Morning Context** - Knows your plan, resolves ambiguity
2. **Fast Path First** - 80% of commands process without LLM (sub-second)
3. **Hotkey Not Wake Word** - Professional, private, reliable
4. **Recency Weighting** - Recent matters score higher in matching
5. **Task Stack** - Elegant interruption handling
6. **Small LLM** - Runs locally, fast inference, excellent JSON output

## 📊 Architecture

```
Voice/Text Input → Intent Classification (Fast Path)
                ↓
         Matter Matching + Recency
                ↓
         Duration Inference
                ↓
         State Machine (Runtime Brain)
                ↓
         LLM (Slow Path - only when needed)
                ↓
         Professional Narrative
                ↓
         SQLite Database
```

## 🎨 UI Design

Inspired by [Humane Calendar](https://humanecalendar.com):
- Navy background (#0a192f)
- Gold accents (#f59e0b)
- Purple highlights (#a78bfa)
- Playfair Display + Inter fonts
- Professional, sophisticated aesthetic

## 📥 Installation

### Prerequisites
1. **Python 3.11+** - [python.org](https://www.python.org/downloads/)
2. **Ollama** - [ollama.ai](https://ollama.ai)
3. **Git** (optional) - [git-scm.com](https://git-scm.com/download/win)

### Install & Run

```bash
# 1. Clone repository
git clone https://github.com/jamescockburn47/voice-time.git
cd voice_time

# 2. Run setup (Windows)
⭐ START HERE.bat

# Or manual setup:
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
ollama pull qwen2.5:1.5b-instruct

# 3. Initialize database
python run.py --init

# 4. Run app
python run.py              # Web UI
python run_voice.py        # Voice mode
```

## 🔧 Configuration

Edit `config.yaml`:

```yaml
ollama:
  model: "qwen2.5:7b-instruct"
  host: "http://localhost:11434"

whisper:
  model: "base.en"
  device: "cpu"

matching:
  confidence_threshold: 0.7

temporal:
  working_day_start: "09:00"
  working_day_end: "18:00"
```

## 📤 Export

- **CSV Export** - Ready for billing systems
- **Professional narratives** - Client-ready descriptions
- **Matter summaries** - Totals by matter and activity

## 🔮 Future Enhancements

- [ ] Calendar integration (auto-import meetings)
- [ ] Desktop app (Tauri)
- [ ] Practice management system connectors
- [ ] Voice feedback
- [ ] Multi-device sync
- [ ] Team features

## 🤝 Contributing

This is a personal project, but feedback and suggestions are welcome!

## 📝 License

MIT License - See LICENSE file for details

## 👤 Author

**James Cockburn**
- GitHub: [@jamescockburn47](https://github.com/jamescockburn47)
- Website: [jamescockburn.io](https://jamescockburn.io)

## 🙏 Acknowledgments

- Design inspired by [Humane Calendar](https://humanecalendar.com)
- Built with [Ollama](https://ollama.ai) for local LLM
- Powered by [faster-whisper](https://github.com/guillaumekln/faster-whisper) for speech-to-text

---

**Made with ❤️ for lawyers who want better time tracking**
