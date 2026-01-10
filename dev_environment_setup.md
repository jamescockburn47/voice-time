# Voice Time Recording - Development Environment Setup

## Overview

You have two excellent options for this project, and they can work **together**:

1. **Cursor 2.0** - Best for iterative development with visual UI, parallel agents, and integrated browser testing
2. **Claude Code** - Best for autonomous long-running tasks, subagents, and terminal-native workflow

This guide covers optimal setup for both, plus hotkey activation for the voice time tool itself.

---

## Part 1: Cursor 2.0 Setup

### Initial Configuration

#### 1. Install & Import Settings
```
Download from cursor.com
On first launch: Import VS Code settings, extensions, keybindings
```

#### 2. Essential Settings (Cmd/Ctrl + Shift + P → "Settings")

**Privacy & Data**
```
Settings → Privacy Mode: ON (for client work)
  - Zero data retention with model providers
  - Note: Disables some features like Background Agents and Memories

Settings → Privacy Mode: OFF (for personal projects like this)
  - Enables Background Agents
  - Enables Memories (auto-remembers your preferences)
  - Enables faster model responses
```

**Model Selection**
```
Settings → Models:
  - Default: Claude Sonnet 4.5 (best balance)
  - For complex architecture: Claude Opus 4.5
  - For simple edits: Composer (Cursor's native model - very fast)
  
Settings → Auto Mode: ON
  - Lets Cursor pick optimal model per task
```

**Agent Settings**
```
Settings → Agent:
  - Auto-run mode: ON (with restrictions)
  - Allowed commands: npm run, pip, python, pytest, uvicorn, flask
  - Denied commands: npm install, pip install, rm -rf, git push
  
Settings → Terminal Sandbox: ON (macOS)
  - Isolates agent commands for safety
```

**Indexing**
```
Settings → Codebase Indexing: ON
  - Index your voice_time directory
  - Exclude: venv/, __pycache__/, *.pyc, .git/
```

### Project Rules Setup

Create `.cursor/rules/` directory in your project:

#### `.cursor/rules/python-project.mdc`
```yaml
---
description: Python project conventions for voice time recording tool
globs:
  - "**/*.py"
alwaysApply: true
---

## Project: Voice Time Recording System

### Tech Stack
- Python 3.11+
- SQLAlchemy 2.0 (async optional)
- Flask + HTMX for web UI
- Ollama for local LLM
- faster-whisper for STT
- pynput for global hotkeys

### Code Standards
- Type hints on all functions
- Docstrings on public functions (Google style)
- Black formatting, 100 char line length
- pytest for testing

### Architecture Principles
- LLM is parser/synthesizer, NOT runtime brain
- Fast path (no LLM) for during-day logging
- State machine for session management
- SQLite for persistence

### Key Files
- ARCHITECTURE.md - System design
- PLAN.md - Development phases
- voice_time/core/state_machine.py - Runtime brain
- voice_time/core/matcher.py - Matter/task matching
- voice_time/llm/prompts.py - All LLM prompts

### Commands
- `python run.py` - Start application
- `pytest tests/ -v` - Run tests
- `flask run --debug` - Dev server
```

#### `.cursor/rules/testing.mdc`
```yaml
---
description: Testing conventions
globs:
  - "tests/**/*.py"
alwaysApply: false
---

## Testing Rules
- Use pytest fixtures (conftest.py)
- Mock Ollama calls for unit tests
- Test fast path separately from LLM path
- Include edge cases for duration inference
- Test matter matching with fuzzy inputs
```

### Parallel Agents in Cursor 2.0

Cursor 2.0 supports up to **8 parallel agents**. Each uses git worktrees for isolation.

#### Launch Parallel Agents

**Method 1: From Chat (Cmd/Ctrl + L)**
```
Click cloud icon → "Run in background"
- Agent clones repo to separate branch
- Works independently
- Opens PR when done
```

**Method 2: Keyboard Shortcut**
```
Cmd/Ctrl + E → Launch background agent
```

**Method 3: Multi-Agent from Single Prompt**
```
In chat, describe parallel tasks:
"Run these in parallel:
1. Build the matter matching module
2. Build the temporal inference module  
3. Create test fixtures

Use separate branches for each."
```

#### Monitor Parallel Agents
```
Agent sidebar (left panel):
- See all running agents
- Click to view progress
- Send follow-up instructions
- Take over manually if needed

When agents complete:
- Cursor auto-judges best solution
- Recommends which to merge
```

### Key Hotkeys for Cursor

| Action | macOS | Windows |
|--------|-------|---------|
| Open Agent Chat | Cmd + L | Ctrl + L |
| Inline Edit | Cmd + K | Ctrl + K |
| Background Agent | Cmd + E | Ctrl + E |
| Switch Layout | Cmd + Opt + Tab | Ctrl + Alt + Tab |
| Accept All Changes | Cmd + Enter | Ctrl + Enter |
| Toggle Agent Panel | Cmd + Shift + A | Ctrl + Shift + A |

---

## Part 2: Claude Code Setup

### Installation

```bash
# Install Claude Code
npm install -g @anthropic-ai/claude-code

# Verify installation
claude --version

# Set theme
claude config set -g theme dark

# Set default model (Sonnet 4.5 recommended)
export ANTHROPIC_MODEL="claude-sonnet-4-5-20250929"
# Or for complex tasks: claude-opus-4-5-20250514
```

### Project Configuration

#### Create CLAUDE.md (Project Memory)

Create `CLAUDE.md` in your project root:

```markdown
# Voice Time Recording System

## Purpose
Voice-activated time recording for litigation lawyers. Morning planning + during-day logging + end-of-day review.

## Tech Stack
- Python 3.11+, SQLAlchemy, Flask + HTMX
- Ollama (Qwen2.5-7B-Instruct) for local LLM
- faster-whisper for speech-to-text
- pynput for global hotkey activation
- SQLite for persistence

## Architecture Principles
1. **LLM is parser/synthesizer, not runtime brain**
   - Fast path handles 80% of during-day utterances
   - LLM only for morning planning, narrative generation, ambiguous cases
2. **Sub-second response for during-day logging**
3. **Never silently misallocate time** - ask if uncertain
4. **Task stack for interruptions** - handle nested work switches

## Key Directories
- `voice_time/core/` - State machine, matcher, temporal inference
- `voice_time/llm/` - Ollama client, prompts, parsers
- `voice_time/voice/` - Whisper integration, audio capture
- `voice_time/web/` - Flask routes, templates
- `tests/` - pytest tests with fixtures

## Commands
```bash
# Development
python run.py              # Start CLI
flask run --debug          # Start web UI
pytest tests/ -v           # Run tests

# Ollama
ollama serve               # Start Ollama server
ollama run qwen2.5:7b-instruct  # Test model
```

## Testing Approach
- Mock Ollama for unit tests
- Test fast path separately from LLM path
- Include fuzzy matching edge cases
- Test temporal inference with various natural language inputs

## Current Focus
Weekend MVP: Core intelligence (matching, temporal, state machine) + basic web UI

## Notes for Claude
- Read ARCHITECTURE.md before making structural changes
- Read PLAN.md for implementation phases
- Check existing code patterns before creating new ones
- Keep LLM out of the hot path for during-day logging
```

#### Settings File `.claude/settings.json`

```json
{
  "permissions": {
    "allow": [
      "Bash(python:*)",
      "Bash(pytest:*)",
      "Bash(flask:*)",
      "Bash(pip install --break-system-packages:*)",
      "Bash(ollama:*)",
      "Read",
      "Write"
    ],
    "deny": [
      "Bash(rm -rf:*)",
      "Bash(git push:*)",
      "Read(.env)",
      "Read(.env.*)"
    ]
  }
}
```

### Subagents for Parallel Work

Claude Code subagents run in separate context windows, enabling parallel development.

#### Create Subagent: Code Reviewer

Create `.claude/agents/code-reviewer.md`:

```yaml
---
name: code-reviewer
description: Reviews code for quality, patterns, and potential issues
model: claude-sonnet-4-5-20250929
tools:
  - Read
  - Grep
  - Glob
allowedCommands: []
---

You are a code reviewer specializing in Python. Your task is to:
1. Identify code quality issues
2. Check for adherence to project patterns
3. Suggest improvements for readability and performance
4. Verify type hints and docstrings are present

Focus on constructive feedback. Output a structured review with:
- Critical issues (must fix)
- Suggestions (should consider)
- Positive observations
```

#### Create Subagent: Test Writer

Create `.claude/agents/test-writer.md`:

```yaml
---
name: test-writer
description: Creates comprehensive pytest tests for modules
model: claude-sonnet-4-5-20250929
tools:
  - Read
  - Write
allowedCommands:
  - "pytest"
---

You are a test engineer. When given a module:
1. Analyze the public interface
2. Identify edge cases
3. Create pytest tests with appropriate fixtures
4. Include both happy path and error cases
5. Mock external dependencies (Ollama, file system)

Place tests in tests/ directory following existing patterns.
```

#### Launch Parallel Subagents

```bash
# Method 1: Prompt Claude to use subagents
"Explore the codebase using 3 tasks in parallel:
- Task 1: Analyze voice_time/core/ modules
- Task 2: Analyze voice_time/llm/ modules  
- Task 3: Review test coverage"

# Method 2: Use /agents command
/agents  # Interactive subagent management

# Method 3: Background tasks (prefix with &)
& review the matcher.py module for edge cases
& create tests for temporal.py
```

### Git Worktrees for True Parallelism

For fully isolated parallel Claude sessions:

```bash
# Create worktrees for parallel work
git worktree add ../voice-time-matching feature/matching
git worktree add ../voice-time-temporal feature/temporal
git worktree add ../voice-time-voice feature/voice

# Launch Claude in each (separate terminals)
cd ../voice-time-matching && claude
cd ../voice-time-temporal && claude
cd ../voice-time-voice && claude

# Each Claude works independently on its feature
# Merge when complete:
git checkout main
git merge feature/matching
git merge feature/temporal
git merge feature/voice
```

### Custom Slash Commands

Create `.claude/commands/` for reusable prompts:

#### `.claude/commands/implement-module.md`
```markdown
---
description: Implement a module following project patterns
argument-hint: <module_name>
---

Implement the module: $ARGUMENTS

Before writing code:
1. Read ARCHITECTURE.md for design context
2. Check similar modules for patterns
3. Review the relevant section in PLAN.md

Requirements:
- Full type hints
- Docstrings (Google style)
- Error handling
- Unit test file in tests/
```

#### `.claude/commands/test-scenario.md`
```markdown
---
description: Run a test scenario through the system
argument-hint: <scenario_description>
---

Test this scenario: $ARGUMENTS

1. Set up the required state
2. Run through the scenario step by step
3. Verify the expected outputs
4. Report any issues found
```

---

## Part 3: Hotkey Activation for Voice Time Tool

The voice time tool should be activated by hotkey, NOT voice detection. Here's the implementation:

### Push-to-Talk Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    HOTKEY LISTENER                          │
│                   (runs in background)                      │
│                                                             │
│   F13 pressed → Start recording → F13 released → Stop      │
│                        OR                                   │
│   Ctrl+Shift+T pressed → Toggle recording mode              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    AUDIO CAPTURE                            │
│              (sounddevice, 16kHz mono)                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  FASTER-WHISPER STT                         │
│              (base.en model, ~1s latency)                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   VOICE TIME CORE                           │
│            (state machine, fast path)                       │
└─────────────────────────────────────────────────────────────┘
```

### Implementation: `voice_time/voice/hotkey.py`

```python
"""Global hotkey listener for push-to-talk activation."""

import threading
from typing import Callable, Optional
from dataclasses import dataclass
from enum import Enum
import sounddevice as sd
import numpy as np
from pynput import keyboard


class RecordingMode(Enum):
    """Recording activation modes."""
    PUSH_TO_TALK = "ptt"      # Hold key to record
    TOGGLE = "toggle"          # Press to start/stop


@dataclass
class HotkeyConfig:
    """Configuration for hotkey activation."""
    # Push-to-talk key (hold to record)
    ptt_key: str = "<f13>"  # F13 is often unbound, good default
    
    # Toggle key (press to start/stop)
    toggle_key: str = "<ctrl>+<shift>+t"
    
    # Alternative: use a specific key combo
    # ptt_key: str = "<ctrl>+<shift>+space"
    
    # Audio settings
    sample_rate: int = 16000
    channels: int = 1


class HotkeyListener:
    """
    Manages global hotkeys for voice recording activation.
    
    Usage:
        listener = HotkeyListener(
            on_recording_start=start_callback,
            on_recording_stop=stop_callback,
            config=HotkeyConfig()
        )
        listener.start()
    """
    
    def __init__(
        self,
        on_recording_start: Callable[[], None],
        on_recording_stop: Callable[[np.ndarray], None],
        config: Optional[HotkeyConfig] = None
    ):
        self.config = config or HotkeyConfig()
        self.on_recording_start = on_recording_start
        self.on_recording_stop = on_recording_stop
        
        self._is_recording = False
        self._audio_buffer: list[np.ndarray] = []
        self._stream: Optional[sd.InputStream] = None
        self._listener: Optional[keyboard.Listener] = None
        self._mode = RecordingMode.PUSH_TO_TALK
        
    def start(self):
        """Start listening for hotkeys."""
        # Parse hotkeys
        ptt_keys = keyboard.HotKey.parse(self.config.ptt_key)
        toggle_keys = keyboard.HotKey.parse(self.config.toggle_key)
        
        # Create hotkey handlers
        self._ptt_hotkey = keyboard.HotKey(ptt_keys, self._on_ptt_activate)
        self._toggle_hotkey = keyboard.HotKey(toggle_keys, self._on_toggle)
        
        # Track key states for PTT release
        self._ptt_keys_pressed = set()
        self._required_ptt_keys = set(ptt_keys)
        
        def on_press(key):
            # Canonicalize the key for consistent comparison
            canonical = self._listener.canonical(key)
            
            # Update PTT hotkey state
            self._ptt_hotkey.press(canonical)
            
            # Track PTT keys for release detection
            if canonical in self._required_ptt_keys:
                self._ptt_keys_pressed.add(canonical)
            
            # Update toggle hotkey state
            self._toggle_hotkey.press(canonical)
        
        def on_release(key):
            canonical = self._listener.canonical(key)
            
            # Update hotkey states
            self._ptt_hotkey.release(canonical)
            self._toggle_hotkey.release(canonical)
            
            # Check if PTT key was released
            if canonical in self._ptt_keys_pressed:
                self._ptt_keys_pressed.discard(canonical)
                if self._is_recording and self._mode == RecordingMode.PUSH_TO_TALK:
                    self._stop_recording()
        
        # Start listener
        self._listener = keyboard.Listener(
            on_press=on_press,
            on_release=on_release
        )
        self._listener.start()
        print(f"Hotkey listener started. PTT: {self.config.ptt_key}, Toggle: {self.config.toggle_key}")
    
    def stop(self):
        """Stop listening for hotkeys."""
        if self._listener:
            self._listener.stop()
            self._listener = None
        if self._is_recording:
            self._stop_recording()
    
    def _on_ptt_activate(self):
        """Called when PTT hotkey is pressed."""
        if not self._is_recording:
            self._mode = RecordingMode.PUSH_TO_TALK
            self._start_recording()
    
    def _on_toggle(self):
        """Called when toggle hotkey is pressed."""
        if self._is_recording:
            self._stop_recording()
        else:
            self._mode = RecordingMode.TOGGLE
            self._start_recording()
    
    def _start_recording(self):
        """Start audio capture."""
        self._is_recording = True
        self._audio_buffer = []
        
        def audio_callback(indata, frames, time, status):
            if status:
                print(f"Audio status: {status}")
            self._audio_buffer.append(indata.copy())
        
        self._stream = sd.InputStream(
            samplerate=self.config.sample_rate,
            channels=self.config.channels,
            dtype=np.float32,
            callback=audio_callback
        )
        self._stream.start()
        
        # Notify callback
        self.on_recording_start()
    
    def _stop_recording(self):
        """Stop audio capture and process."""
        self._is_recording = False
        
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        
        # Combine audio buffer
        if self._audio_buffer:
            audio = np.concatenate(self._audio_buffer, axis=0)
            # Notify callback with audio data
            self.on_recording_stop(audio)
        
        self._audio_buffer = []


# Convenience function for simple usage
def create_push_to_talk(
    on_transcript: Callable[[str], None],
    ptt_key: str = "<f13>",
    toggle_key: str = "<ctrl>+<shift>+t"
) -> HotkeyListener:
    """
    Create a push-to-talk listener that transcribes audio.
    
    Args:
        on_transcript: Called with transcribed text when recording stops
        ptt_key: Key to hold for push-to-talk
        toggle_key: Key to press to toggle recording
    
    Returns:
        HotkeyListener instance (call .start() to begin)
    
    Example:
        def handle_transcript(text):
            print(f"You said: {text}")
            # Process with voice_time core...
        
        ptt = create_push_to_talk(handle_transcript)
        ptt.start()
        
        # Keep running...
        import time
        while True:
            time.sleep(1)
    """
    from .transcribe import Transcriber
    
    transcriber = Transcriber()
    
    def on_start():
        print("🎤 Recording...")
    
    def on_stop(audio: np.ndarray):
        print("⏹️ Processing...")
        text = transcriber.transcribe(audio)
        if text.strip():
            on_transcript(text)
        else:
            print("(No speech detected)")
    
    config = HotkeyConfig(ptt_key=ptt_key, toggle_key=toggle_key)
    return HotkeyListener(on_start, on_stop, config)


if __name__ == "__main__":
    # Test the hotkey listener
    def on_transcript(text: str):
        print(f"\n📝 Transcript: {text}\n")
    
    print("Starting push-to-talk test...")
    print("Hold F13 or press Ctrl+Shift+T to record")
    print("Press Ctrl+C to exit")
    
    listener = create_push_to_talk(on_transcript)
    listener.start()
    
    try:
        import time
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nExiting...")
        listener.stop()
```

### Platform-Specific Notes

#### macOS
```bash
# Grant accessibility permissions
System Preferences → Security & Privacy → Privacy → Accessibility
# Add Terminal.app (or your Python app) to the list

# For packaged apps, whitelist the .app bundle
```

#### Windows
```bash
# Run as Administrator for some hotkeys
# Or use elevated Python process

# F13-F24 keys may require special keyboard or remapping software
```

#### Recommended Hotkeys

| Key | Notes |
|-----|-------|
| F13-F24 | Usually unbound, ideal for custom apps |
| Ctrl+Shift+T | Common, but may conflict with browser |
| Ctrl+Alt+Space | Generally safe |
| Pause/Break | Rarely used, good option |
| Scroll Lock | Rarely used |

### System Tray Integration (Optional)

For a polished experience, add system tray icon:

```python
# voice_time/tray.py
"""System tray integration for voice time recording."""

import pystray
from PIL import Image, ImageDraw
from typing import Callable


def create_tray_icon(
    on_toggle: Callable[[], None],
    on_quit: Callable[[], None]
) -> pystray.Icon:
    """Create system tray icon with menu."""
    
    # Create a simple icon (red circle when recording)
    def create_image(recording: bool = False):
        img = Image.new('RGB', (64, 64), color='white')
        draw = ImageDraw.Draw(img)
        color = 'red' if recording else 'green'
        draw.ellipse([8, 8, 56, 56], fill=color)
        return img
    
    icon = pystray.Icon(
        "voice_time",
        create_image(),
        "Voice Time Recording",
        menu=pystray.Menu(
            pystray.MenuItem("Toggle Recording", on_toggle),
            pystray.MenuItem("Quit", on_quit)
        )
    )
    
    return icon
```

---

## Part 4: Recommended Workflow

### For This Weekend Project

**Use Both Tools Together:**

1. **Cursor** for interactive development
   - Write core modules
   - Debug and iterate
   - Visual diff review
   - Quick tests

2. **Claude Code** for autonomous tasks
   - Generate boilerplate
   - Write comprehensive tests
   - Refactor modules
   - Documentation

### Parallel Development Strategy

```
Terminal 1 (Cursor):
  - Active development
  - state_machine.py
  - Iterating, testing

Terminal 2 (Claude Code - worktree 1):
  & implement matcher.py following PLAN.md
  
Terminal 3 (Claude Code - worktree 2):
  & implement temporal.py following PLAN.md
  
Terminal 4 (Claude Code - worktree 3):
  & create test fixtures and mock Ollama client
```

### Daily Workflow

```bash
# Morning: Review and merge parallel work
git merge feature/matching
git merge feature/temporal
pytest tests/ -v

# During day: Use Cursor for active coding

# Background: Claude Code for:
# - Documentation
# - Test coverage
# - Refactoring

# Evening: Review PRs from background agents
```

---

## Quick Start Commands

### Cursor
```bash
# Open project
cursor /path/to/voice_time

# In Cursor:
Cmd+L → "Read ARCHITECTURE.md and PLAN.md, then implement voice_time/core/matcher.py"
```

### Claude Code
```bash
cd /path/to/voice_time
claude

# In Claude:
/init  # Generate CLAUDE.md from codebase
"Read the planning docs and implement the core state machine"
```

### Both Together
```bash
# Terminal 1: Cursor for main development
cursor .

# Terminal 2: Claude Code for parallel tasks
git worktree add ../voice-time-tests feature/tests
cd ../voice-time-tests
claude
"Create comprehensive tests for all modules in voice_time/core/"
```
