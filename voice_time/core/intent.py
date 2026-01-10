"""Intent classification for user utterances."""
import re
from enum import Enum
from dataclasses import dataclass
from typing import Optional


class Intent(Enum):
    """Intent types for user utterances."""
    PLAN = "plan"                    # Morning planning
    START = "start"                  # Start working on something
    COMPLETE = "complete"            # Finished a task
    SWITCH = "switch"                # Switch to another task
    PAUSE = "pause"                  # Taking a break
    RESUME = "resume"                # Back from break
    STATUS = "status"                # Query status/what's left
    LOG_HISTORICAL = "log_historical"  # Past tense logging
    ADD_TASK = "add_task"            # Add new task to plan
    CORRECT = "correct"              # Correction to previous entry
    ALLOCATE = "allocate"            # Allocate unallocated time
    UNKNOWN = "unknown"


@dataclass
class IntentResult:
    """Result of intent classification."""
    intent: Intent
    confidence: float  # 0-1
    signals: list  # Matched signals


class IntentClassifier:
    """
    Classifies user utterances into intents using heuristics.
    
    Fast path classification without LLM for sub-second response.
    Uses keyword patterns and linguistic cues.
    """
    
    # Intent signal patterns
    COMPLETION_SIGNALS = [
        "done", "finished", "completed", "wrapped up", "that's it",
        "done with", "finished with", "completed that"
    ]
    
    START_SIGNALS = [
        "starting", "beginning", "working on", "moving to",
        "start", "begin", "going to work on"
    ]
    
    SWITCH_SIGNALS = [
        "back to", "switching to", "returning to", "resume",
        "switch to", "move to", "change to"
    ]
    
    PAUSE_SIGNALS = [
        "taking lunch", "lunch break", "break", "stepping away",
        "going for lunch", "taking a break"
    ]
    
    RESUME_SIGNALS = [
        "back from", "back to work", "returning from",
        "back from lunch", "back from break"
    ]
    
    STATUS_SIGNALS = [
        "what's left", "what's outstanding", "status",
        "what do i have", "what's remaining", "where am i"
    ]
    
    PLAN_SIGNALS = [
        "today i need", "today's plan", "planning to",
        "this morning i", "today i'm", "today i want"
    ]
    
    ADD_TASK_SIGNALS = [
        "also need", "add", "forgot to", "need to add",
        "also have to", "additionally"
    ]
    
    CORRECT_SIGNALS = [
        "actually", "change", "not x but y", "correction",
        "that should be", "make that"
    ]
    
    ALLOCATE_SIGNALS = [
        "that was for", "put that on", "allocate to",
        "charge to", "assign to"
    ]
    
    # Past tense patterns for historical logging
    PAST_TENSE_PATTERNS = [
        r"\bwas\b", r"\bwere\b", r"\bspent\b", r"\bdid\b",
        r"\btook\b", r"\bhad\b", r"\bworked\b"
    ]
    
    # Present continuous patterns for START
    PRESENT_PATTERNS = [
        r"\bam\b", r"\b'm\b", r"\bstarting\b", r"\bbeginning\b",
        r"\bworking\b"
    ]
    
    def classify(self, utterance: str) -> IntentResult:
        """
        Classify user utterance into an intent.
        
        Args:
            utterance: What the user said
            
        Returns:
            IntentResult with intent and confidence
        """
        utterance_lower = utterance.lower().strip()
        
        # Check each intent type in order of specificity
        
        # PLAN (morning planning)
        plan_signals = self._check_signals(utterance_lower, self.PLAN_SIGNALS)
        if plan_signals:
            return IntentResult(Intent.PLAN, 0.9, plan_signals)
        
        # COMPLETE (done with task)
        complete_signals = self._check_signals(utterance_lower, self.COMPLETION_SIGNALS)
        if complete_signals:
            return IntentResult(Intent.COMPLETE, 0.95, complete_signals)
        
        # SWITCH (back to/switching to)
        switch_signals = self._check_signals(utterance_lower, self.SWITCH_SIGNALS)
        if switch_signals:
            return IntentResult(Intent.SWITCH, 0.9, switch_signals)
        
        # RESUME (back from break)
        resume_signals = self._check_signals(utterance_lower, self.RESUME_SIGNALS)
        if resume_signals:
            return IntentResult(Intent.RESUME, 0.9, resume_signals)
        
        # PAUSE (taking break)
        pause_signals = self._check_signals(utterance_lower, self.PAUSE_SIGNALS)
        if pause_signals:
            return IntentResult(Intent.PAUSE, 0.9, pause_signals)
        
        # STATUS (what's left?)
        status_signals = self._check_signals(utterance_lower, self.STATUS_SIGNALS)
        if status_signals:
            return IntentResult(Intent.STATUS, 0.95, status_signals)
        
        # CORRECT (actually/change)
        correct_signals = self._check_signals(utterance_lower, self.CORRECT_SIGNALS)
        if correct_signals:
            return IntentResult(Intent.CORRECT, 0.85, correct_signals)
        
        # ALLOCATE (put that on)
        allocate_signals = self._check_signals(utterance_lower, self.ALLOCATE_SIGNALS)
        if allocate_signals:
            return IntentResult(Intent.ALLOCATE, 0.85, allocate_signals)
        
        # ADD_TASK (also need to)
        add_signals = self._check_signals(utterance_lower, self.ADD_TASK_SIGNALS)
        if add_signals:
            return IntentResult(Intent.ADD_TASK, 0.8, add_signals)
        
        # LOG_HISTORICAL (past tense)
        past_tense = self._check_patterns(utterance_lower, self.PAST_TENSE_PATTERNS)
        if past_tense:
            return IntentResult(Intent.LOG_HISTORICAL, 0.8, past_tense)
        
        # START (present continuous or start signals)
        start_signals = self._check_signals(utterance_lower, self.START_SIGNALS)
        present = self._check_patterns(utterance_lower, self.PRESENT_PATTERNS)
        
        if start_signals or present:
            return IntentResult(
                Intent.START,
                0.85 if start_signals else 0.7,
                start_signals + present
            )
        
        # Default to UNKNOWN with low confidence
        return IntentResult(Intent.UNKNOWN, 0.0, [])
    
    def _check_signals(self, text: str, signals: list) -> list:
        """Check which signals are present in text."""
        matched = []
        for signal in signals:
            if signal in text:
                matched.append(signal)
        return matched
    
    def _check_patterns(self, text: str, patterns: list) -> list:
        """Check which regex patterns match in text."""
        matched = []
        for pattern in patterns:
            if re.search(pattern, text):
                matched.append(pattern)
        return matched
