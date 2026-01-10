"""Audio capture for voice input."""
import sounddevice as sd
import numpy as np
from typing import Optional


class AudioCapture:
    """
    Simple audio capture for push-to-talk recording.
    
    Records audio until stopped, returns numpy array.
    """
    
    def __init__(self, sample_rate: int = 16000, channels: int = 1):
        self.sample_rate = sample_rate
        self.channels = channels
        self.recording: Optional[list] = None
        self.stream: Optional[sd.InputStream] = None
    
    def start(self):
        """Start recording audio."""
        self.recording = []
        
        def callback(indata, frames, time, status):
            if status:
                print(f"Audio status: {status}")
            self.recording.append(indata.copy())
        
        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype=np.float32,
            callback=callback
        )
        self.stream.start()
        print("🎤 Recording...")
    
    def stop(self) -> np.ndarray:
        """Stop recording and return audio data."""
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        
        print("⏹️ Recording stopped")
        
        if self.recording:
            audio = np.concatenate(self.recording, axis=0)
            self.recording = None
            return audio
        else:
            return np.array([], dtype=np.float32)
    
    def is_recording(self) -> bool:
        """Check if currently recording."""
        return self.stream is not None
