"""Temporal inference - duration and time parsing from natural language."""
import re
from typing import Optional, Tuple
from datetime import datetime, time, timedelta
from dataclasses import dataclass


@dataclass
class DurationResult:
    """Result of duration inference."""
    hours: float
    confidence: float  # 0-1
    source: str  # 'explicit', 'natural', 'anchor', 'elapsed', 'modifier'
    needs_confirmation: bool = False


class TemporalParser:
    """
    Parses duration and time expressions from natural language.
    
    Handles:
    - Explicit: "2 hours", "30 minutes", "1.5 hrs"
    - Natural: "couple of hours", "all morning", "ages"
    - Time anchors: "since lunch", "since 3pm"
    - Modifiers: "quick", "brief", "long"
    """
    
    # Explicit duration patterns
    DURATION_PATTERNS = {
        r"(\d+\.?\d*)\s*hours?": lambda m: float(m.group(1)),
        r"(\d+\.?\d*)\s*hrs?": lambda m: float(m.group(1)),
        r"(\d+)\s*mins?(?:utes?)?": lambda m: float(m.group(1)) / 60,
        r"(\d+)\s*h(?:our)?s?\s+(\d+)\s*m(?:in)?(?:utes?)?": lambda m: float(m.group(1)) + float(m.group(2)) / 60,
    }
    
    # Natural language durations (hours)
    NATURAL_DURATIONS = {
        "quick": 0.1,
        "brief": 0.2,
        "short": 0.25,
        "few minutes": 0.15,
        "about an hour": 1.0,
        "hour or so": 1.0,
        "an hour": 1.0,
        "one hour": 1.0,
        "couple of hours": 2.0,
        "few hours": 3.0,
        "several hours": 3.5,
        "most of the morning": 3.5,
        "all morning": 4.0,
        "most of the afternoon": 3.5,
        "all afternoon": 4.0,
        "half day": 3.75,
        "all day": 7.5,
        "ages": None,  # Will use elapsed time
    }
    
    # Time anchors (relative times)
    TIME_ANCHORS = {
        "since this morning": "09:00",
        "since morning": "09:00",
        "since lunch": "13:00",
        "since after lunch": "13:30",
        "since noon": "12:00",
        "this morning": ("09:00", "12:00"),
        "this afternoon": ("13:00", "now"),
        "before lunch": ("09:00", "12:30"),
        "after lunch": ("13:00", "18:00"),
    }
    
    def __init__(self, config=None):
        self.config = config
    
    def infer_duration(
        self,
        utterance: str,
        last_entry_time: Optional[datetime] = None,
        current_time: Optional[datetime] = None
    ) -> DurationResult:
        """
        Infer duration from utterance and context.
        
        Args:
            utterance: What the user said
            last_entry_time: When the last work log was created
            current_time: Current time (defaults to now)
            
        Returns:
            DurationResult with inferred hours and confidence
        """
        if current_time is None:
            current_time = datetime.now()
        
        utterance_lower = utterance.lower()
        
        # 1. Check for explicit duration
        explicit = self._parse_explicit_duration(utterance_lower)
        if explicit is not None:
            return DurationResult(
                hours=explicit,
                confidence=0.95,
                source="explicit"
            )
        
        # 2. Check for natural language duration
        natural = self._parse_natural_duration(utterance_lower)
        if natural is not None:
            return DurationResult(
                hours=natural,
                confidence=0.85,
                source="natural"
            )
        
        # 3. Check for time anchors
        anchor_time = self._parse_time_anchor(utterance_lower, current_time)
        if anchor_time:
            hours = (current_time - anchor_time).total_seconds() / 3600
            return DurationResult(
                hours=round(hours, 1),
                confidence=0.8,
                source="anchor"
            )
        
        # 4. Use elapsed time since last entry
        if last_entry_time:
            elapsed = (current_time - last_entry_time).total_seconds() / 3600
            
            # Check for modifier hints
            modifier = self._extract_modifier(utterance_lower)
            
            if modifier == "quick":
                inferred = min(elapsed, 0.25)
                confidence = 0.7
            elif modifier == "brief":
                inferred = min(elapsed, 0.5)
                confidence = 0.7
            elif modifier == "long":
                inferred = elapsed
                confidence = 0.6
            elif elapsed < 0.5:
                # Short elapsed time, probably accurate
                inferred = elapsed
                confidence = 0.7
            elif elapsed < 4.0:
                # Medium elapsed time
                inferred = elapsed
                confidence = 0.6
            else:
                # Long elapsed time, less confident
                inferred = elapsed
                confidence = 0.5
            
            return DurationResult(
                hours=round(inferred, 1),
                confidence=confidence,
                source="elapsed",
                needs_confirmation=confidence < 0.7
            )
        
        # 5. Default to 0.5 hours with low confidence
        return DurationResult(
            hours=0.5,
            confidence=0.3,
            source="default",
            needs_confirmation=True
        )
    
    def _parse_explicit_duration(self, text: str) -> Optional[float]:
        """Parse explicit duration expressions."""
        for pattern, extractor in self.DURATION_PATTERNS.items():
            match = re.search(pattern, text)
            if match:
                return extractor(match)
        return None
    
    def _parse_natural_duration(self, text: str) -> Optional[float]:
        """Parse natural language duration expressions."""
        for phrase, hours in self.NATURAL_DURATIONS.items():
            if phrase in text:
                return hours
        return None
    
    def _parse_time_anchor(
        self,
        text: str,
        current_time: datetime
    ) -> Optional[datetime]:
        """Parse time anchor expressions to datetime."""
        for phrase, anchor in self.TIME_ANCHORS.items():
            if phrase in text:
                if isinstance(anchor, str):
                    if anchor == "now":
                        return current_time
                    # Parse time string (HH:MM)
                    anchor_time = self._parse_time_string(anchor)
                    if anchor_time:
                        return datetime.combine(current_time.date(), anchor_time)
                elif isinstance(anchor, tuple):
                    # Range - use start time
                    start_str = anchor[0]
                    if start_str != "now":
                        start_time = self._parse_time_string(start_str)
                        if start_time:
                            return datetime.combine(current_time.date(), start_time)
        
        # Check for "since HH:MM" pattern
        match = re.search(r"since\s+(\d{1,2}):?(\d{2})?", text)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2)) if match.group(2) else 0
            if 0 <= hour < 24 and 0 <= minute < 60:
                return datetime.combine(current_time.date(), time(hour, minute))
        
        return None
    
    def _parse_time_string(self, time_str: str) -> Optional[time]:
        """Parse HH:MM string to time object."""
        try:
            parts = time_str.split(":")
            if len(parts) == 2:
                hour, minute = int(parts[0]), int(parts[1])
                if 0 <= hour < 24 and 0 <= minute < 60:
                    return time(hour, minute)
        except:
            pass
        return None
    
    def _extract_modifier(self, text: str) -> Optional[str]:
        """Extract duration modifier hints."""
        if any(word in text for word in ["quick", "quickly"]):
            return "quick"
        if any(word in text for word in ["brief", "briefly"]):
            return "brief"
        if any(word in text for word in ["long", "lengthy", "ages", "forever"]):
            return "long"
        return None
