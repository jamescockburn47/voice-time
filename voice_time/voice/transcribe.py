"""Speech-to-text using faster-whisper."""
import numpy as np
from faster_whisper import WhisperModel
from typing import Optional


class Transcriber:
    """
    Whisper-based transcription for voice input.
    
    Uses faster-whisper (Python bindings for whisper.cpp)
    for efficient CPU inference with hardware optimization.
    """
    
    def __init__(self, model_size: str = "base.en", device: str = "cpu", compute_type: str = None):
        """
        Initialize transcriber.
        
        Args:
            model_size: Whisper model size (tiny.en, base.en, small.en, medium.en)
            device: "cpu" or "cuda" (user config respected)
            compute_type: "int8", "float16", "float32" (auto-detected if None)
        """
        self.model_size = model_size
        
        # BUG FIX #2: Respect user-configured device, only auto-detect if default
        # Auto-detect optimal settings only if user hasn't configured
        if compute_type is None and device == "cpu":
            # User hasn't explicitly configured - use auto-detection
            from .hardware import get_optimal_whisper_config
            config = get_optimal_whisper_config()
            self.device = config['device']
            self.compute_type = config['compute_type']
        else:
            # User has configured device or compute_type - respect their choice
            self.device = device
            if compute_type is None:
                # Auto-detect compute type for user's chosen device
                self.compute_type = "float16" if device == "cuda" else "int8"
            else:
                self.compute_type = compute_type
        
        self.model: Optional[WhisperModel] = None
    
    def _ensure_loaded(self):
        """Lazy-load the model on first use."""
        if self.model is None:
            print(f"Loading Whisper model: {self.model_size} on {self.device} ({self.compute_type})...")
            
            # Import hardware detection for info
            try:
                from .hardware import detect_hardware
                hw = detect_hardware()
                if hw['notes']:
                    print(f"Hardware: {', '.join(hw['notes'][:2])}")
            except:
                pass
            
            self.model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type
            )
            print(f"Model loaded! Device: {self.device}, Compute: {self.compute_type}")
    
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
