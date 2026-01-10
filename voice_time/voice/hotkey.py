"""Global hotkey listener for push-to-talk activation."""
import threading
from typing import Callable, Optional
from dataclasses import dataclass
import sounddevice as sd
import numpy as np
from pynput import keyboard


class RecordingMode:
    """Recording activation modes."""
    PUSH_TO_TALK = "ptt"      # Hold key to record
    TOGGLE = "toggle"          # Press to start/stop


@dataclass
class HotkeyConfig:
    """Configuration for hotkey activation."""
    # Push-to-talk key (hold to record)
    ptt_key: str = "<ctrl>+<space>"  # Ctrl+Space - easy to reach!
    
    # Toggle key (press to start/stop)
    toggle_key: str = "<ctrl>+<shift>+t"
    
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
        self._audio_buffer: list = []
        self._stream: Optional[sd.InputStream] = None
        self._listener: Optional[keyboard.Listener] = None
        self._mode = RecordingMode.PUSH_TO_TALK
        self._ptt_active = False
        
    def start(self):
        """Start listening for hotkeys."""
        # Track modifier keys
        current_keys = set()
        
        def on_press(key):
            try:
                # Track all pressed keys
                current_keys.add(key)
                
                # Check for Ctrl+Space (push-to-talk)
                if keyboard.Key.ctrl in current_keys or keyboard.Key.ctrl_l in current_keys or keyboard.Key.ctrl_r in current_keys:
                    if key == keyboard.Key.space:
                        if not self._is_recording:
                            self._mode = RecordingMode.PUSH_TO_TALK
                            self._ptt_active = True
                            self._start_recording()
                
                # Check for Ctrl+Shift+T (toggle)
                if (keyboard.Key.ctrl in current_keys or keyboard.Key.ctrl_l in current_keys or keyboard.Key.ctrl_r in current_keys) and \
                   (keyboard.Key.shift in current_keys or keyboard.Key.shift_l in current_keys or keyboard.Key.shift_r in current_keys):
                    if hasattr(key, 'char') and (key.char == 't' or key.char == 'T'):
                        self.toggle_recording()
                            
            except AttributeError:
                pass
        
        def on_release(key):
            try:
                # Remove from tracked keys
                if key in current_keys:
                    current_keys.remove(key)
                
                # Handle Ctrl+Space release for push-to-talk
                if key == keyboard.Key.space and self._ptt_active:
                    self._ptt_active = False
                    if self._is_recording and self._mode == RecordingMode.PUSH_TO_TALK:
                        self._stop_recording()
                            
            except AttributeError:
                pass
        
        # Create keyboard listener
        self._listener = keyboard.Listener(
            on_press=on_press,
            on_release=on_release
        )
        self._listener.start()
        
        print(f"🎤 Hotkey listener started!")
        print(f"   Push-to-talk: {self.config.ptt_key} (hold to record)")
        print(f"   Toggle: {self.config.toggle_key} (press to start/stop)")
    
    def stop(self):
        """Stop listening for hotkeys."""
        if self._listener:
            self._listener.stop()
            self._listener = None
        if self._is_recording:
            self._stop_recording()
    
    def toggle_recording(self):
        """Toggle recording on/off (for toggle mode)."""
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
        print("⏹️  Processing...")
        text = transcriber.transcribe(audio)
        if text.strip():
            on_transcript(text)
        else:
            print("(No speech detected)")
    
    config = HotkeyConfig(ptt_key=ptt_key, toggle_key=toggle_key)
    return HotkeyListener(on_start, on_stop, config)
