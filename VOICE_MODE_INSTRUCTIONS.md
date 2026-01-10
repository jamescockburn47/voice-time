# Voice Mode Instructions 🎤

## Quick Start

### Option 1: Double-Click
```
🎤 VOICE MODE.bat
```

### Option 2: Via Menu
1. Double-click `START_HERE.bat`
2. Choose option **3** (Start VOICE Mode)

## How It Works

**NO WAKE WORD** - Uses **hotkey activation** instead!

### Recording Options

**Option A: Push-to-Talk (Recommended)**
- Press and **HOLD** `F13` key
- Speak while holding
- **Release** to process

**Option B: Toggle Mode**
- Press `Ctrl+Shift+T` to **start** recording
- Speak
- Press `Ctrl+Shift+T` again to **stop** and process

**Option C: Alternative Push-to-Talk**
- Press and **HOLD** `Ctrl+Shift+Space`
- Speak while holding
- **Release** to process

## What You'll See

```
==========================================
  Voice Time - VOICE MODE
==========================================

🎤 Hotkey listener started!
   Push-to-talk: <f13> (hold to record)
   Toggle: <ctrl>+<shift>+t (press to start/stop)

Active Matters:
  • Smith v Jones - Smith, SvJ
  • Brown v Welsh - Brown, BvW
  ... 

✓ Ready!

🎧 Waiting for hotkey... Press F13 or Ctrl+Shift+T

```

## Usage Examples

### Morning Planning
1. Press and hold `F13`
2. Say: "Today I need to finish Smith disclosure and draft Brown skeleton"
3. Release `F13`
4. Wait for processing...

You'll see:
```
You said: Today I need to finish Smith disclosure and draft Brown skeleton
Processing...
✓ Planned 2 tasks across 2 matters

Ready for next command... (Press hotkey)
```

### During-Day Logging
1. Press and hold `F13`
2. Say: "Working on Smith disclosure"
3. Release

Later:
1. Press and hold `F13`
2. Say: "Done with the disclosure"
3. Release

```
You said: Done with the disclosure
Processing...
✓ Logged 2.5h to Smith v Jones - Document Review

Ready for next command... (Press hotkey)
```

### Interruptions
1. Press `F13`, say: "Quick call about Brown", release
2. ... (handle the call)
3. Press `F13`, say: "Back to what I was doing", release

## Key Differences from Web UI

| Feature | Web UI | Voice Mode |
|---------|--------|------------|
| Input | Type in browser | Speak with hotkey |
| Activation | Click submit | Press F13 |
| Feedback | Visual in browser | Console text |
| Convenience | Mouse/keyboard | Hands-free |

## Tips for Best Results

1. **Speak clearly** - Normal conversational speed
2. **Wait for beep** - System confirms recording started
3. **Brief phrases** - "Done with Smith" works better than long sentences
4. **Use aliases** - "Smith" instead of "Smith v Jones matter number 2024/001"
5. **Check results** - System shows what it understood

## Hotkey Notes

### F13 Key
- Most keyboards don't have F13
- Use software to remap another key to F13:
  - **Windows:** AutoHotkey, SharpKeys
  - **Mac:** Karabiner-Elements

### Alternative: Ctrl+Shift+Space
- Works on all keyboards
- Less convenient (requires 3 keys)
- Good backup option

### Recommended Remapping
Map one of these to F13:
- Caps Lock (rarely used)
- Right Alt
- Right Ctrl
- Pause/Break key

## Troubleshooting

### "No speech detected"
- Speak louder or closer to microphone
- Check microphone is working
- Try toggle mode instead of push-to-talk

### Recording doesn't start
- Check microphone permissions
- Ensure `pynput` is installed: `pip install pynput`
- Try running as administrator (Windows)

### Hotkey not working
- On Windows, may need to run as administrator
- Try alternative hotkey (Ctrl+Shift+T)
- Check no other app is using the same hotkey

### Transcription is wrong
- Speak more clearly
- Reduce background noise
- Use shorter phrases
- Check microphone quality

## Stopping Voice Mode

Press `Ctrl+C` in the console window

## Switching to Web UI

Close voice mode and run:
```
start.bat
```

Or use `START_HERE.bat` menu, option 2

## Advanced: Custom Hotkeys

Edit `run_voice.py` to change hotkeys:

```python
ptt = create_push_to_talk(
    on_transcript=on_transcript,
    ptt_key="<f13>",           # Change this
    toggle_key="<ctrl>+<shift>+t"  # Or this
)
```

Valid keys: `<f13>`, `<f14>`, `<ctrl>+<shift>+<key>`, etc.

## Why Hotkey Instead of Wake Word?

Wake word detection:
- ❌ Requires constant listening (privacy concerns)
- ❌ Higher CPU usage
- ❌ More false positives
- ❌ Background noise issues

Hotkey activation:
- ✅ Only records when you want
- ✅ Better privacy (you control when)
- ✅ Lower CPU usage
- ✅ More reliable
- ✅ Professional setting appropriate

---

**Ready to try it?** Double-click `🎤 VOICE MODE.bat` and press F13!
