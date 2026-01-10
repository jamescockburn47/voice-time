# TimeBrief

Voice-first time recording for lawyers. Built with local AI - your data never leaves your machine.

## For New Users - Quick Setup

### Prerequisites
- **Windows 10/11**
- **Python 3.11+** - [Download from python.org](https://www.python.org/downloads/)
- **Rust** (for Tauri) - [Download from rustup.rs](https://rustup.rs/)
- **8GB+ RAM** recommended

### Step 1: Clone the Repository
```bash
git clone https://github.com/YOUR_USERNAME/voice_time.git
cd voice_time
```

### Step 2: Run TimeBrief
```bash
TimeBrief.bat
```

That's it! The batch file will automatically:
1. Create a Python virtual environment
2. Install all dependencies
3. Check/install Ollama and AI models
4. Launch the desktop app

### First Run Notes
- **First launch takes ~5 minutes** as it downloads AI models (~2GB)
- Allow microphone access when prompted
- The app will open in a native window

---

## How It Works

1. **Plan your day** - Tell TimeBrief what you're working on today
2. **Start a timer** - Say "working on Smith matter" and a timer begins
3. **Switch tasks** - Just say what you're doing next  
4. **Review and export** - Clean, billable entries ready for your system

## Features

- **Voice Control** - Click or Ctrl+Space to record, click again to stop
- **Local AI** - Ollama + Whisper run entirely on your machine
- **Smart Matching** - Recognizes matters, activities, and planned tasks
- **Voice Memos** - Dictate thoughts and action items per case
- **6-Minute Billing** - Automatic calculation of billable units
- **AI Chat** - Ask questions about your time data
- **Zero Cloud** - 100% private, offline-capable

## Technology

- Python + Flask (backend)
- Tauri (native desktop wrapper)
- Ollama with Qwen2.5 (local LLM)
- faster-whisper (speech-to-text)
- SQLite (local database)

## Configuration

Edit `config.yaml` to change:
- AI models (Whisper size, Ollama model)
- Working hours
- Matching thresholds

Models can also be changed in Settings within the app.

## Data Storage

All data stored locally at:
- **Windows**: `C:\Users\YOUR_NAME\.voice_time\voice_time.db`
- **Mac/Linux**: `~/.voice_time/voice_time.db`

## Building a Standalone Installer

To create a distributable `.exe` installer:

```bash
BUILD.bat
```

This creates `TimeBrief_x.x.x_x64-setup.exe` in `src-tauri/target/release/bundle/nsis/`

The installer includes everything - users don't need Python or Rust installed.

## Running Without Tauri (Browser Mode)

If you just want the web interface without the native wrapper:

```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run
python run.py
```

Then open http://localhost:5000 in your browser.

## Troubleshooting

### "Ollama not found"
The app will try to install Ollama automatically. If it fails:
1. Download from [ollama.com](https://ollama.com/download)
2. Install and run once
3. Restart TimeBrief

### "Model not downloaded"
Go to Settings page and click "Download" next to the model you want.

### Microphone not working
- Check browser/app has microphone permission
- Try Settings → Test Microphone
- Ensure no other app is using the microphone

## License

MIT

## Author

James Cockburn - [jamescockburn.io](https://jamescockburn.io)
