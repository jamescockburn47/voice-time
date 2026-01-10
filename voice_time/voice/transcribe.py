"""Speech-to-text using faster-whisper."""
import numpy as np
from faster_whisper import WhisperModel
from typing import Optional


class Transcriber:
    """
    Whisper-based transcription for voice input.
    
    Uses faster-whisper (Python bindings for whisper.cpp)
    for efficient CPU inference.
    """
    
    def __init__(self, model_size: str = "base.en", device: str = "cpu"):
        """
        Initialize transcriber.
        
        Args:
            model_size: Whisper model size (tiny.en, base.en, small.en, medium.en)
            device: "cpu" or "cuda"
        """
        self.model_size = model_size
        self.device = device
        self.model: Optional[WhisperModel] = None
    
    def _ensure_loaded(self):
        """Lazy-load the model on first use."""
        if self.model is None:
            print(f"Loading Whisper model: {self.model_size}...")
            self.model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type="int8" if self.device == "cpu" else "float16"
            )
            print("Model loaded!")
    
    def transcribe(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000
    ) -> str:
        """
        Transcribe audio to text.
        
        Args:
            audio: Audio data as numpy array (float32, mono)
            sample_rate: Sample rate of audio (default 16000)
            
        Returns:
            Transcribed text
        """
        self._ensure_loaded()
        
        # Ensure audio is float32
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)
        
        # Ensure mono (if stereo, take mean)
        if len(audio.shape) > 1:
            audio = audio.mean(axis=1)
        
        # Normalize to [-1, 1] range if needed
        max_val = np.abs(audio).max()
        if max_val > 1.0:
            audio = audio / max_val
        
        # Transcribe
        segments, info = self.model.transcribe(
            audio,
            language="en",
            beam_size=5,
            vad_filter=True,  # Voice activity detection
            vad_parameters=dict(
                min_silence_duration_ms=500
            )
        )
        
        # Combine segments
        text = " ".join(segment.text.strip() for segment in segments)
        
        return text.strip()
    
    def transcribe_file(self, audio_path: str) -> str:
        """
        Transcribe audio from file.
        
        Args:
            audio_path: Path to audio file (wav, mp3, etc.)
            
        Returns:
            Transcribed text
        """
        self._ensure_loaded()
        
        segments, info = self.model.transcribe(
            audio_path,
            language="en",
            beam_size=5
        )
        
        text = " ".join(segment.text.strip() for segment in segments)
        return text.strip()
