# Windows Setup Guide

## Quick Start (Double-Click Method)

### Step 1: First Time Setup

1. **Double-click** `START_HERE.bat`
2. Choose option **1** (First Time Setup)
3. Wait for dependencies to install
4. Follow the Ollama instructions if needed

### Step 2: Initialize Database

1. In the menu, choose option **4** (Initialize Database)
2. Sample matters will be created

### Step 3: Start Application

1. Make sure Ollama is running (see below)
2. In the menu, choose option **2** (Start Web UI)
3. Open browser to http://localhost:5000

## Executable Files Created

### `START_HERE.bat` ⭐ MAIN LAUNCHER
Interactive menu with all options:
- First time setup
- Start web UI
- Start CLI mode
- Initialize database
- Check Ollama status

**Just double-click this file to get started!**

### `setup.bat`
First-time setup:
- Creates virtual environment
- Installs Python dependencies
- Checks Ollama installation
- Downloads AI model

### `start.bat`
Starts the web interface:
- Activates virtual environment
- Checks Ollama connection
- Launches Flask server
- Opens on http://localhost:5000

### `start_cli.bat`
Starts CLI mode for testing:
- Good for quick testing
- Terminal-based interface

### `init_database.bat`
Initialize/reset database:
- Creates database
- Adds sample matters
- Seeds activity types

## Running Ollama (Required)

Before using Voice Time, Ollama must be running:

### Option 1: Using Command Prompt
1. Open Command Prompt
2. Type: `ollama serve`
3. Leave this window open

### Option 2: Using Windows Terminal
1. Open Windows Terminal
2. Type: `ollama serve`
3. Leave this tab open

### Option 3: Check if Already Running
- Double-click `START_HERE.bat`
- Choose option 5 to check status

## Troubleshooting

### "Python is not installed"
1. Install Python from https://www.python.org/downloads/
2. During installation, check "Add Python to PATH"
3. Run `setup.bat` again

### "Ollama is not running"
1. Open a new terminal
2. Run: `ollama serve`
3. Keep that terminal open
4. Run `start.bat` again

### "Model not found"
Open Command Prompt and run:
```
ollama pull qwen2.5:7b-instruct
```

### "Virtual environment not found"
Run `setup.bat` to create it

### Port 5000 already in use
Edit `run.py` and change port from 5000 to another (e.g., 5001)

## Daily Usage

Once set up, your daily workflow is:

1. **Morning:**
   - Open terminal → Run `ollama serve`
   - Double-click `start.bat`
   - Open http://localhost:5000
   - Type your daily plan

2. **During day:**
   - Keep browser tab open
   - Enter work as you go
   - "Done with Smith disclosure"
   - "Quick call about Brown"

3. **End of day:**
   - Click "Review" in web UI
   - Verify time entries
   - Click "Export to CSV"
   - Import to billing system

## File Locations

- **Database:** `C:\Users\YourName\.voice_time\voice_time.db`
- **Config:** `config.yaml` (in project folder)
- **Logs:** Check console output

## Advanced Usage

### Running from Command Line

If you prefer command line:

```batch
REM Activate virtual environment
venv\Scripts\activate

REM Run web UI
python run.py

REM Run CLI
python run.py --cli

REM Initialize database
python run.py --init
```

### Customization

Edit `config.yaml` to change:
- Ollama model
- Working hours
- Confidence thresholds
- Database location

## Need Help?

1. Check `QUICKSTART.md` for detailed instructions
2. Check `README.md` for usage examples
3. Check `ARCHITECTURE.md` for technical details

## What's Next?

After setup:
1. Replace sample matters with your real cases
2. Try the example workflows
3. Customize settings in `config.yaml`
4. Set up voice input (optional)

Enjoy your voice-activated time tracking! 🎉
