"""Configuration management."""
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
import yaml


@dataclass
class OllamaConfig:
    host: str = "http://localhost:11434"
    model: str = "qwen2.5:1.5b-instruct"
    timeout: int = 30


@dataclass
class WhisperConfig:
    model: str = "base.en"
    device: str = "cpu"


@dataclass
class AudioConfig:
    sample_rate: int = 16000
    channels: int = 1


@dataclass
class MatchingConfig:
    confidence_threshold: float = 0.7
    ambiguity_threshold: float = 0.9


@dataclass
class TemporalConfig:
    working_day_start: str = "09:00"
    working_day_end: str = "18:00"
    lunch_start: str = "12:30"
    lunch_end: str = "13:30"


@dataclass
class Config:
    data_dir: Path = field(default_factory=lambda: Path.home() / ".voice_time")
    ollama: OllamaConfig = field(default_factory=OllamaConfig)
    whisper: WhisperConfig = field(default_factory=WhisperConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    matching: MatchingConfig = field(default_factory=MatchingConfig)
    temporal: TemporalConfig = field(default_factory=TemporalConfig)
    
    @classmethod
    def load(cls, path: Optional[Path] = None) -> "Config":
        """Load config from YAML file, with defaults."""
        config = cls()
        
        if path is None:
            path = Path("config.yaml")
        
        if path.exists():
            with open(path) as f:
                data = yaml.safe_load(f)
                # Merge with defaults
                if data:
                    if "ollama" in data:
                        config.ollama = OllamaConfig(**data["ollama"])
                    if "whisper" in data:
                        config.whisper = WhisperConfig(**data["whisper"])
                    if "audio" in data:
                        config.audio = AudioConfig(**data["audio"])
                    if "matching" in data:
                        config.matching = MatchingConfig(**data["matching"])
                    if "temporal" in data:
                        config.temporal = TemporalConfig(**data["temporal"])
                    if "app" in data and "data_dir" in data["app"]:
                        config.data_dir = Path(data["app"]["data_dir"]).expanduser()
        
        # Ensure data directory exists
        config.data_dir.mkdir(parents=True, exist_ok=True)
        
        return config
