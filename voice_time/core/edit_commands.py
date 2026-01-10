"""Voice commands for editing work log entries."""
import re
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class EditCommand:
    """Parsed edit command."""
    command_type: str  # 'change_duration', 'update_narrative', 'change_matter', 'change_activity', 'delete', 'add_time'
    entry_number: Optional[int] = None
    entry_id: Optional[str] = None
    new_duration: Optional[float] = None
    narrative_update: Optional[str] = None
    matter_name: Optional[str] = None
    activity_name: Optional[str] = None


class EditCommandParser:
    """
    Parses voice commands for editing work log entries.
    
    Handles commands like:
    - "Change entry 3 duration to 2.5 hours"
    - "Update entry 1 narrative to mention expert report"
    - "Change entry 2 matter to Thompson"
    - "Update entry 5 activity to research"
    - "Delete entry 4"
    - "Add 30 minutes to Thompson for emails"
    """
    
    # Duration change patterns (more specific)
    CHANGE_DURATION_PATTERNS = [
        r"change entry (\d+) duration to ([\d.]+)\s*h(?:ours?)?",
        r"update entry (\d+) duration to ([\d.]+)\s*h(?:ours?)?",
        r"change entry (\d+) to ([\d.]+)\s*h(?:ours?)?",
        r"update entry (\d+) to ([\d.]+)\s*h(?:ours?)?",
        r"make entry (\d+) ([\d.]+)\s*h(?:ours?)?",
        r"entry (\d+) should be ([\d.]+)\s*h(?:ours?)?",
        r"entry (\d+) duration ([\d.]+)\s*h(?:ours?)?",
    ]
    
    # Narrative update patterns
    NARRATIVE_PATTERNS = [
        r"(?:change|update) entry (\d+) narrative to (.+)",
        r"(?:change|update) entry (\d+) description to (.+)",
        r"entry (\d+) narrative (.+)",
        r"edit entry (\d+) (?:narrative )?to say (.+)",
        r"entry (\d+) should say (.+)",
    ]
    
    # Matter change patterns
    MATTER_PATTERNS = [
        r"change entry (\d+) matter to (.+)",
        r"update entry (\d+) matter to (.+)",
        r"move entry (\d+) to (.+)",
        r"entry (\d+) should be (?:on|for) (.+)",
    ]
    
    # Activity change patterns
    ACTIVITY_PATTERNS = [
        r"change entry (\d+) activity to (.+)",
        r"update entry (\d+) activity to (.+)",
        r"make entry (\d+) (.+?) activity",
        r"entry (\d+) (?:should be|is) (.+?) (?:activity|work)",
    ]
    
    # Delete patterns
    DELETE_PATTERNS = [
        r"delete entry (\d+)",
        r"remove entry (\d+)",
        r"cancel entry (\d+)",
        r"get rid of entry (\d+)",
    ]
    
    # Add time patterns
    ADD_TIME_PATTERNS = [
        r"add ([\d.]+)\s*h(?:ours?)? to (.+)",
        r"forgot ([\d.]+)\s*h(?:ours?)? (?:on|for) (.+)",
        r"also (?:add|log) ([\d.]+)\s*h(?:ours?)? (?:on|for|to) (.+)",
    ]
    
    def parse(self, utterance: str) -> Optional[EditCommand]:
        """
        Parse an editing voice command.
        
        Args:
            utterance: What the user said
            
        Returns:
            EditCommand if valid edit command, None otherwise
        """
        utterance_lower = utterance.lower().strip()
        
        # Check for duration changes
        for pattern in self.CHANGE_DURATION_PATTERNS:
            match = re.search(pattern, utterance_lower)
            if match:
                entry_num = int(match.group(1))
                hours = float(match.group(2))
                return EditCommand(
                    command_type='change_duration',
                    entry_number=entry_num,
                    new_duration=hours
                )
        
        # Check for narrative updates
        for pattern in self.NARRATIVE_PATTERNS:
            match = re.search(pattern, utterance_lower)
            if match:
                entry_num = int(match.group(1))
                narrative = match.group(2).strip()
                return EditCommand(
                    command_type='update_narrative',
                    entry_number=entry_num,
                    narrative_update=narrative
                )
        
        # Check for matter changes
        for pattern in self.MATTER_PATTERNS:
            match = re.search(pattern, utterance_lower)
            if match:
                entry_num = int(match.group(1))
                matter = match.group(2).strip()
                return EditCommand(
                    command_type='change_matter',
                    entry_number=entry_num,
                    matter_name=matter
                )
        
        # Check for activity changes
        for pattern in self.ACTIVITY_PATTERNS:
            match = re.search(pattern, utterance_lower)
            if match:
                entry_num = int(match.group(1))
                activity = match.group(2).strip()
                return EditCommand(
                    command_type='change_activity',
                    entry_number=entry_num,
                    activity_name=activity
                )
        
        # Check for deletions
        for pattern in self.DELETE_PATTERNS:
            match = re.search(pattern, utterance_lower)
            if match:
                entry_num = int(match.group(1))
                return EditCommand(
                    command_type='delete',
                    entry_number=entry_num
                )
        
        # Check for adding time
        for pattern in self.ADD_TIME_PATTERNS:
            match = re.search(pattern, utterance_lower)
            if match:
                hours = float(match.group(1))
                matter = match.group(2).strip()
                return EditCommand(
                    command_type='add_time',
                    new_duration=hours,
                    matter_name=matter
                )
        
        return None
