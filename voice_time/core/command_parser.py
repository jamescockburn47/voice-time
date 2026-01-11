"""
Unified Command Parser - Parses natural language into structured commands.

Handles:
- Time entries: "smith research 2 hours"
- Navigation: "go to review"
- Queries: "how much on smith this week?"
- Commands: "undo", "export last week"
- Corrections: "actually that was for brown"
"""
import re
import logging
from enum import Enum
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta

logger = logging.getLogger(__name__)


class CommandType(str, Enum):
    """Types of commands the parser can recognize."""
    # Time tracking
    LOG_TIME = "log_time"
    START_TIMER = "start_timer"
    STOP_TIMER = "stop_timer"
    PAUSE_TIMER = "pause_timer"
    RESUME_TIMER = "resume_timer"

    # Navigation
    NAVIGATE = "navigate"

    # Queries
    QUERY_HOURS = "query_hours"
    QUERY_STATUS = "query_status"
    QUERY_MATTERS = "query_matters"

    # Corrections
    CORRECT_MATTER = "correct_matter"
    CORRECT_ACTIVITY = "correct_activity"
    CORRECT_DURATION = "correct_duration"
    SPLIT_ENTRY = "split_entry"
    MERGE_ENTRIES = "merge_entries"
    DELETE_ENTRY = "delete_entry"

    # Actions
    UNDO = "undo"
    REDO = "redo"
    EXPORT = "export"
    PLAN = "plan"
    ADD_TASK = "add_task"
    COMPLETE_TASK = "complete_task"

    # Context
    CONTINUE = "continue"  # "continue where I left off"
    SWITCH = "switch"

    # Help
    HELP = "help"

    # Unknown
    UNKNOWN = "unknown"


@dataclass
class ParsedCommand:
    """Result of parsing a command."""
    command_type: CommandType
    confidence: float = 1.0

    # Time tracking params
    matter_query: Optional[str] = None
    activity_query: Optional[str] = None
    duration_hours: Optional[float] = None
    narrative: Optional[str] = None

    # Navigation params
    destination: Optional[str] = None

    # Query params
    time_range: Optional[str] = None  # "today", "this week", "last week"
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    # Correction params
    correction_target: Optional[str] = None  # "last", specific ID
    correction_from: Optional[str] = None
    correction_to: Optional[str] = None
    split_ratio: Optional[Tuple[float, float]] = None

    # Raw data
    original_text: str = ""
    matched_patterns: List[str] = field(default_factory=list)

    # Suggestions if ambiguous
    suggestions: List[str] = field(default_factory=list)
    is_ambiguous: bool = False


class CommandParser:
    """
    Parses natural language commands into structured ParsedCommand objects.
    """

    # Navigation destinations
    NAV_PATTERNS = {
        r'\b(go\s+to\s+|show\s+|open\s+)?review\b': 'review',
        r'\b(go\s+to\s+|show\s+|open\s+)?planning\b': 'planning',
        r'\b(go\s+to\s+|show\s+|open\s+)?dashboard\b': 'index',
        r'\b(go\s+to\s+|show\s+|open\s+)?home\b': 'index',
        r'\b(go\s+to\s+|show\s+|open\s+)?matters?\b': 'matters',
        r'\b(go\s+to\s+|show\s+|open\s+)?memos?\b': 'memos',
        r'\b(go\s+to\s+|show\s+|open\s+)?chat\b': 'chat',
        r'\b(go\s+to\s+|show\s+|open\s+)?settings?\b': 'settings',
        r'\b(go\s+to\s+|show\s+|open\s+)?calendar\b': 'calendar',
        r'\b(go\s+to\s+|show\s+|open\s+)?analytics\b': 'analytics',
    }

    # Time patterns
    DURATION_PATTERNS = [
        (r'(\d+(?:\.\d+)?)\s*(?:hours?|hrs?|h)\b', lambda m: float(m.group(1))),
        (r'(\d+)\s*(?:minutes?|mins?|m)\b', lambda m: float(m.group(1)) / 60),
        (r'(\d+)\s*(?:units?|u)\b', lambda m: float(m.group(1)) * 0.1),
        (r'half\s*(?:an?\s*)?hour', lambda m: 0.5),
        (r'quarter\s*(?:of\s*an?\s*)?hour', lambda m: 0.25),
        (r'couple\s*(?:of\s*)?hours?', lambda m: 2.0),
        (r'few\s*hours?', lambda m: 3.0),
    ]

    # Time range patterns
    TIME_RANGE_PATTERNS = {
        r'\btoday\b': 'today',
        r'\byesterday\b': 'yesterday',
        r'\bthis\s+week\b': 'this_week',
        r'\blast\s+week\b': 'last_week',
        r'\bthis\s+month\b': 'this_month',
        r'\blast\s+month\b': 'last_month',
    }

    # Query patterns
    QUERY_PATTERNS = [
        (r'how\s+(?:much|many)\s+(?:time\s+)?(?:on|for)\s+(.+?)(?:\s+(?:today|this|last))?$', 'query_hours'),
        (r'what.+(?:working|worked)\s+on', 'query_status'),
        (r'(?:show|list|what)\s+(?:are\s+)?(?:my\s+)?matters?', 'query_matters'),
        (r'status', 'query_status'),
        (r"what's\s+left", 'query_status'),
    ]

    # Correction patterns
    CORRECTION_PATTERNS = [
        (r'actually\s+(?:that\s+was\s+)?(?:for|on)\s+(.+)', 'correct_matter'),
        (r'(?:change|move)\s+(?:that|last|it)\s+(?:to|from)\s+(.+?)\s+to\s+(.+)', 'correct_matter'),
        (r'(?:that\s+)?should\s+(?:be|have\s+been)\s+(.+)', 'correct'),
        (r'split\s+(?:that|it|last)\s+(?:between|with)\s+(.+)', 'split_entry'),
        (r'(?:delete|remove)\s+(?:that|last|the\s+last)', 'delete_entry'),
        (r'merge\s+(?:the\s+)?(?:last\s+)?(?:two|2)', 'merge_entries'),
    ]

    # Action patterns
    ACTION_PATTERNS = [
        (r'\bundo\b', 'undo'),
        (r'\bredo\b', 'redo'),
        (r'export\s+(.+)', 'export'),
        (r'continue\s+(?:where\s+I\s+left\s+off|with\s+(.+))', 'continue'),
        (r'(?:switch|back)\s+to\s+(.+)', 'switch'),
        (r'(?:start|begin)\s+(?:timer\s+)?(?:on|for)\s+(.+)', 'start_timer'),
        (r'(?:stop|end|finish)\s+(?:the\s+)?timer', 'stop_timer'),
        (r'pause\s+(?:the\s+)?timer', 'pause_timer'),
        (r'resume\s+(?:the\s+)?timer', 'resume_timer'),
        (r'(?:done|finished|completed?)\s+(?:with\s+)?(.+)?', 'complete'),
        (r'add\s+(?:task|todo)\s*[:\s]*(.+)', 'add_task'),
        (r'plan\s*[:\s]*(.+)', 'plan'),
    ]

    # Help patterns
    HELP_PATTERNS = [
        r'\bhelp\b',
        r'\bcommands?\b',
        r'what\s+can\s+(?:you|I)\s+(?:do|say)',
        r'how\s+do\s+I',
    ]

    def parse(self, text: str) -> ParsedCommand:
        """Parse natural language text into a command."""
        original_text = text
        text = text.lower().strip()

        # Check for help
        for pattern in self.HELP_PATTERNS:
            if re.search(pattern, text):
                return ParsedCommand(
                    command_type=CommandType.HELP,
                    original_text=original_text
                )

        # Check for undo/redo first (simple commands)
        if re.search(r'\bundo\b', text):
            return ParsedCommand(
                command_type=CommandType.UNDO,
                original_text=original_text,
                confidence=1.0
            )
        if re.search(r'\bredo\b', text):
            return ParsedCommand(
                command_type=CommandType.REDO,
                original_text=original_text,
                confidence=1.0
            )

        # Check for navigation
        for pattern, destination in self.NAV_PATTERNS.items():
            if re.search(pattern, text):
                return ParsedCommand(
                    command_type=CommandType.NAVIGATE,
                    destination=destination,
                    original_text=original_text,
                    matched_patterns=[pattern]
                )

        # Check for queries
        for pattern, query_type in self.QUERY_PATTERNS:
            match = re.search(pattern, text)
            if match:
                cmd = ParsedCommand(
                    command_type=CommandType.QUERY_HOURS if query_type == 'query_hours' else CommandType.QUERY_STATUS,
                    original_text=original_text,
                    matched_patterns=[pattern]
                )
                if match.groups():
                    cmd.matter_query = match.group(1).strip()

                # Extract time range
                cmd.time_range = self._extract_time_range(text)
                cmd.start_date, cmd.end_date = self._resolve_time_range(cmd.time_range)

                return cmd

        # Check for corrections
        for pattern, correction_type in self.CORRECTION_PATTERNS:
            match = re.search(pattern, text)
            if match:
                cmd = ParsedCommand(
                    original_text=original_text,
                    matched_patterns=[pattern]
                )

                if correction_type == 'correct_matter':
                    cmd.command_type = CommandType.CORRECT_MATTER
                    if len(match.groups()) >= 2:
                        cmd.correction_from = match.group(1).strip()
                        cmd.correction_to = match.group(2).strip()
                    elif match.groups():
                        cmd.correction_to = match.group(1).strip()
                elif correction_type == 'split_entry':
                    cmd.command_type = CommandType.SPLIT_ENTRY
                    if match.groups():
                        cmd.correction_to = match.group(1).strip()
                elif correction_type == 'delete_entry':
                    cmd.command_type = CommandType.DELETE_ENTRY
                elif correction_type == 'merge_entries':
                    cmd.command_type = CommandType.MERGE_ENTRIES
                else:
                    cmd.command_type = CommandType.CORRECT_MATTER
                    if match.groups():
                        cmd.correction_to = match.group(1).strip()

                return cmd

        # Check for actions
        for pattern, action_type in self.ACTION_PATTERNS:
            match = re.search(pattern, text)
            if match:
                cmd = ParsedCommand(
                    original_text=original_text,
                    matched_patterns=[pattern]
                )

                if action_type == 'start_timer':
                    cmd.command_type = CommandType.START_TIMER
                    if match.groups():
                        target = match.group(1).strip()
                        cmd.matter_query, cmd.activity_query = self._split_matter_activity(target)
                elif action_type == 'stop_timer':
                    cmd.command_type = CommandType.STOP_TIMER
                elif action_type == 'pause_timer':
                    cmd.command_type = CommandType.PAUSE_TIMER
                elif action_type == 'resume_timer':
                    cmd.command_type = CommandType.RESUME_TIMER
                elif action_type == 'continue':
                    cmd.command_type = CommandType.CONTINUE
                    if match.lastindex and match.group(match.lastindex):
                        cmd.matter_query = match.group(match.lastindex).strip()
                elif action_type == 'switch':
                    cmd.command_type = CommandType.SWITCH
                    if match.groups():
                        target = match.group(1).strip()
                        cmd.matter_query, cmd.activity_query = self._split_matter_activity(target)
                elif action_type == 'complete':
                    cmd.command_type = CommandType.COMPLETE_TASK
                    if match.groups() and match.group(1):
                        cmd.matter_query = match.group(1).strip()
                elif action_type == 'add_task':
                    cmd.command_type = CommandType.ADD_TASK
                    if match.groups():
                        cmd.narrative = match.group(1).strip()
                elif action_type == 'plan':
                    cmd.command_type = CommandType.PLAN
                    if match.groups():
                        cmd.narrative = match.group(1).strip()
                elif action_type == 'export':
                    cmd.command_type = CommandType.EXPORT
                    if match.groups():
                        cmd.time_range = self._extract_time_range(match.group(1))

                return cmd

        # Default: try to parse as time entry
        return self._parse_time_entry(text, original_text)

    def _parse_time_entry(self, text: str, original_text: str) -> ParsedCommand:
        """Parse text as a time entry command."""
        cmd = ParsedCommand(
            command_type=CommandType.LOG_TIME,
            original_text=original_text
        )

        # Extract duration
        remaining_text = text
        for pattern, extractor in self.DURATION_PATTERNS:
            match = re.search(pattern, text)
            if match:
                cmd.duration_hours = extractor(match)
                remaining_text = re.sub(pattern, '', remaining_text).strip()
                cmd.matched_patterns.append(pattern)
                break

        # Extract time range (for context)
        cmd.time_range = self._extract_time_range(text)
        if cmd.time_range:
            for pattern in self.TIME_RANGE_PATTERNS:
                remaining_text = re.sub(pattern, '', remaining_text).strip()

        # Clean up common words
        remaining_text = re.sub(r'\b(working|worked|on|for|with|doing|did|spent)\b', '', remaining_text)
        remaining_text = re.sub(r'\s+', ' ', remaining_text).strip()

        # Split remaining into matter and activity
        if remaining_text:
            cmd.matter_query, cmd.activity_query = self._split_matter_activity(remaining_text)

        # Determine confidence
        if cmd.matter_query and cmd.duration_hours:
            cmd.confidence = 0.9
        elif cmd.matter_query:
            cmd.confidence = 0.7
        elif cmd.duration_hours:
            cmd.confidence = 0.5
        else:
            cmd.command_type = CommandType.UNKNOWN
            cmd.confidence = 0.0

        return cmd

    def _split_matter_activity(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """Split text into matter and activity components."""
        # Common activity keywords that help split
        activity_keywords = [
            'research', 'researching', 'drafting', 'draft', 'review', 'reviewing',
            'call', 'calling', 'meeting', 'conference', 'email', 'emailing',
            'correspondence', 'letter', 'attending', 'attendance', 'court',
            'hearing', 'trial', 'document', 'preparation', 'prep'
        ]

        text = text.strip()
        words = text.split()

        if not words:
            return None, None

        # Look for activity keyword
        for i, word in enumerate(words):
            if word.lower() in activity_keywords:
                matter = ' '.join(words[:i]).strip() if i > 0 else None
                activity = ' '.join(words[i:]).strip()
                return matter or None, activity

        # No clear activity - assume all is matter
        return text, None

    def _extract_time_range(self, text: str) -> Optional[str]:
        """Extract time range from text."""
        for pattern, range_name in self.TIME_RANGE_PATTERNS.items():
            if re.search(pattern, text):
                return range_name
        return None

    def _resolve_time_range(self, range_name: Optional[str]) -> Tuple[Optional[date], Optional[date]]:
        """Convert time range name to actual dates."""
        if not range_name:
            return None, None

        today = date.today()

        if range_name == 'today':
            return today, today
        elif range_name == 'yesterday':
            yesterday = today - timedelta(days=1)
            return yesterday, yesterday
        elif range_name == 'this_week':
            week_start = today - timedelta(days=today.weekday())
            return week_start, today
        elif range_name == 'last_week':
            week_start = today - timedelta(days=today.weekday() + 7)
            week_end = week_start + timedelta(days=6)
            return week_start, week_end
        elif range_name == 'this_month':
            month_start = today.replace(day=1)
            return month_start, today
        elif range_name == 'last_month':
            month_start = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
            month_end = today.replace(day=1) - timedelta(days=1)
            return month_start, month_end

        return None, None

    def get_help_text(self) -> str:
        """Get help text showing available commands."""
        return """
Available Commands:

TIME TRACKING
  "smith research 2 hours" - Log time
  "start timer on thompson" - Start timer
  "stop timer" / "pause" / "resume"
  "done with research" - Complete current work

NAVIGATION
  "go to review" / "show planning" / "open matters"

QUERIES
  "how much on smith this week?"
  "what am I working on?" / "status"

CORRECTIONS
  "actually that was for brown"
  "change last to thompson"
  "split that between smith and brown"
  "delete last entry"
  "undo" / "redo"

TASKS
  "add task: review disclosure"
  "plan: call client, draft letter"

KEYBOARD SHORTCUTS
  Press ? for shortcut overlay
"""
