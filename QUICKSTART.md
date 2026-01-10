# Quick Start Guide

## 1. First Time Setup

```bash
# Make sure you're in the voice_time directory
cd voice_time

# Activate your virtual environment
# On Windows:
venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate

# Verify Ollama is installed
ollama --version

# If not installed, install from https://ollama.ai
```

## 2. Start Ollama

Open a **separate terminal** and run:

```bash
# Start the Ollama server
ollama serve

# This should show: "Ollama is running on http://localhost:11434"
```

Keep this terminal open while using Voice Time.

## 3. Pull the AI Model

In another terminal (or the same Ollama terminal with Ctrl+C first):

```bash
# Download the model (first time only, ~4GB)
ollama pull qwen2.5:7b-instruct

# Verify it's installed
ollama list
```

## 4. Initialize the Database

```bash
# In your voice_time directory with venv activated
python run.py --init
```

You should see:

```
✓ Database created at: C:\Users\James\.voice_time\voice_time.db
✓ Created 4 sample matters:
  - Smith v Jones (2024/001)
  - Brown v Welsh (2024/002)
  - Acme Corp Ltd (2024/003)
  - R v Johnson (2024/004)
```

## 5. Choose Your Interface

### Option A: Web UI (Recommended)

```bash
python run.py
```

Then open your browser to: **http://localhost:5000**

You'll see a dashboard where you can:
- Enter text or (later) voice commands
- See today's plan and logged time
- Review and export your work

### Option B: CLI (For Testing)

```bash
python run.py --cli
```

You'll see a text interface where you can type commands directly.

## 6. Try It Out!

### Morning Planning

In the web UI or CLI, type:

```
Today I need to finish Smith disclosure, draft Brown skeleton, and call with counsel at 3
```

You should see the system parse this into 3 structured tasks.

### Start Working

```
Working on Smith disclosure
```

The system starts tracking time for Smith v Jones.

### Complete a Task

```
Done with the disclosure
```

The system:
1. Infers the duration (time since you started)
2. Generates a professional narrative
3. Creates a work log entry
4. Shows you the logged time

### Handle Interruptions

```
Quick call about Brown
```

The system pushes Smith to a stack and switches to Brown.

```
Back to what I was doing
```

The system pops Smith from the stack and resumes.

### Check Status

```
What's left?
```

Shows your remaining planned tasks.

### Review Your Day

Navigate to **Review** in the web UI, or visit: http://localhost:5000/review

You'll see:
- Total hours by matter
- Breakdown by activity type
- Detailed log with narratives
- Export to CSV button

## 7. Export to CSV

Click "Export to CSV" on the review page, or visit:
http://localhost:5000/export/csv

You'll get a CSV file with:
```
Date,Matter Ref,Matter,Activity,Hours,Narrative
2026-01-10,2024/001,Smith v Jones,DOCREV,2.5,"Review and analysis of disclosure bundle"
```

Perfect for importing into your billing system!

## Common Issues

### "Error: Ollama is not running"

**Solution:** Make sure Ollama is running in a separate terminal:
```bash
ollama serve
```

### "Model not available"

**Solution:** Pull the model:
```bash
ollama pull qwen2.5:7b-instruct
```

### Can't access http://localhost:5000

**Solution:** 
1. Check if Flask is running (you should see "Running on http://0.0.0.0:5000")
2. Try http://127.0.0.1:5000 instead
3. Check if another app is using port 5000

### Database errors

**Solution:** Re-initialize the database:
```bash
python run.py --init
```

## Next Steps

1. **Add Real Matters**: Replace the sample matters with your actual cases
2. **Configure**: Edit `config.yaml` to customize settings
3. **Voice Input**: Set up voice capture for true voice-first experience
4. **Explore**: Try different natural language patterns
5. **Review**: Check end-of-day review to ensure accuracy

## Tips for Best Results

1. **Plan in the morning** - The system works best when it knows what you intend to do
2. **Use natural language** - "Done with Smith" works as well as "Completed work on Smith v Jones matter"
3. **Be specific about duration** - "Spent 2 hours on..." is more accurate than letting it infer
4. **Review before export** - Always check the end-of-day review before exporting
5. **Use consistent names** - Once you say "Smith", keep using "Smith" rather than switching to "Smith v Jones"

Enjoy your new voice-activated time tracking system! 🎉
