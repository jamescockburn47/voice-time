"""
Smart Narrative Generation and Memo Action Extraction.

Uses local LLM to:
- Generate professional billing narratives from raw descriptions
- Extract action items from voice memos
- Parse deadlines and dates from natural language
"""
import json
import re
import logging
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from .client import OllamaClient

logger = logging.getLogger(__name__)


@dataclass
class GeneratedNarrative:
    """Result of narrative generation."""
    narrative: str
    confidence: float
    original: str
    expanded_details: List[str]


@dataclass
class ExtractedAction:
    """An action item extracted from a memo."""
    description: str
    due_date: Optional[date] = None
    priority: str = "normal"  # low, normal, high, urgent
    category: str = "task"  # task, deadline, follow_up, research


@dataclass
class MemoParseResult:
    """Result of parsing a voice memo."""
    thoughts: str  # General notes/observations
    actions: List[ExtractedAction]
    deadlines: List[Dict[str, Any]]
    references: List[str]  # Mentioned cases, documents, people


class SmartNarrativeGenerator:
    """
    Generates professional billing narratives from raw descriptions.
    Uses legal writing conventions and matter context.
    """

    NARRATIVE_PROMPT = """You are a legal billing narrative generator. Convert the raw time entry description into a professional billing narrative suitable for a client invoice.

RULES:
1. Use formal legal language
2. Be specific about what was done
3. Include document names or parties when mentioned
4. Use active voice
5. Keep it concise but detailed (1-2 sentences)
6. Don't include time duration in the narrative

MATTER: {matter_name}
ACTIVITY TYPE: {activity_type}
RAW DESCRIPTION: {description}
PREVIOUS NARRATIVES FOR THIS MATTER (for style reference):
{previous_narratives}

Generate a professional billing narrative. Return JSON:
{{"narrative": "...", "confidence": 0.0-1.0}}"""

    def __init__(self, llm_client: OllamaClient):
        self.llm = llm_client

    def generate(
        self,
        description: str,
        matter_name: str = "",
        activity_type: str = "",
        previous_narratives: List[str] = None
    ) -> GeneratedNarrative:
        """Generate a professional billing narrative."""
        if not description:
            return GeneratedNarrative(
                narrative="",
                confidence=0.0,
                original=description,
                expanded_details=[]
            )

        # Build context
        prev_context = ""
        if previous_narratives:
            prev_context = "\n".join(f"- {n}" for n in previous_narratives[:5])
        else:
            prev_context = "None available"

        prompt = self.NARRATIVE_PROMPT.format(
            matter_name=matter_name or "General",
            activity_type=activity_type or "Administration",
            description=description,
            previous_narratives=prev_context
        )

        try:
            result = self.llm.generate(prompt, json_mode=True, temperature=0.3)

            narrative = result.get("narrative", description)
            confidence = result.get("confidence", 0.7)

            return GeneratedNarrative(
                narrative=narrative,
                confidence=confidence,
                original=description,
                expanded_details=[]
            )

        except Exception as e:
            logger.warning(f"Narrative generation failed: {e}")
            # Fallback: basic cleanup
            return GeneratedNarrative(
                narrative=self._basic_cleanup(description, activity_type),
                confidence=0.5,
                original=description,
                expanded_details=[]
            )

    def _basic_cleanup(self, description: str, activity_type: str = "") -> str:
        """Basic narrative cleanup without LLM."""
        # Capitalize first letter
        narrative = description.strip()
        if narrative:
            narrative = narrative[0].upper() + narrative[1:]

        # Add activity prefix if not present
        activity_verbs = {
            "Document Review": "Reviewing",
            "Drafting": "Drafting",
            "Legal Research": "Researching",
            "Telephone": "Telephone attendance with",
            "Meeting/Conference": "Attending conference regarding",
            "Correspondence": "Correspondence regarding",
            "Court/Hearing": "Attending",
        }

        if activity_type in activity_verbs:
            verb = activity_verbs[activity_type]
            if not narrative.lower().startswith(verb.lower()):
                narrative = f"{verb} {narrative.lower()}"

        return narrative


class MemoActionExtractor:
    """
    Extracts action items, deadlines, and references from voice memos.
    """

    EXTRACTION_PROMPT = """You are analyzing a voice memo from a lawyer about a legal matter. Extract structured information.

MATTER: {matter_name}
MEMO TRANSCRIPT: {transcript}

Extract:
1. THOUGHTS: General notes and observations (not action items)
2. ACTIONS: Specific things that need to be done
3. DEADLINES: Any dates or timeframes mentioned
4. REFERENCES: Any cases, documents, people, or authorities mentioned

For each action, determine:
- priority: low, normal, high, urgent
- category: task, deadline, follow_up, research

Return JSON:
{{
    "thoughts": "General observations...",
    "actions": [
        {{"description": "...", "due_date": "YYYY-MM-DD or null", "priority": "normal", "category": "task"}}
    ],
    "deadlines": [
        {{"description": "...", "date": "YYYY-MM-DD", "is_hard_deadline": true}}
    ],
    "references": ["case name", "document name", "person name"]
}}"""

    # Patterns for extracting dates
    DATE_PATTERNS = [
        (r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b', 'weekday'),
        (r'\b(today|tomorrow|next week|this week)\b', 'relative'),
        (r'\b(\d{1,2}(?:st|nd|rd|th)?\s+(?:of\s+)?(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*)\b', 'date'),
        (r'\bby\s+(?:end\s+of\s+)?(\w+day)\b', 'deadline_weekday'),
        (r'\b(urgent|asap|immediately)\b', 'urgent'),
    ]

    def __init__(self, llm_client: OllamaClient):
        self.llm = llm_client

    def extract(self, transcript: str, matter_name: str = "") -> MemoParseResult:
        """Extract actions, thoughts, and references from a memo transcript."""
        if not transcript:
            return MemoParseResult(thoughts="", actions=[], deadlines=[], references=[])

        prompt = self.EXTRACTION_PROMPT.format(
            matter_name=matter_name or "Unknown",
            transcript=transcript
        )

        try:
            result = self.llm.generate(prompt, json_mode=True, temperature=0.2)

            thoughts = result.get("thoughts", transcript)
            actions = []
            deadlines = result.get("deadlines", [])
            references = result.get("references", [])

            for action_data in result.get("actions", []):
                due_date = None
                if action_data.get("due_date"):
                    try:
                        due_date = datetime.strptime(action_data["due_date"], "%Y-%m-%d").date()
                    except ValueError:
                        # Try to parse relative dates
                        due_date = self._parse_relative_date(action_data["due_date"])

                actions.append(ExtractedAction(
                    description=action_data.get("description", ""),
                    due_date=due_date,
                    priority=action_data.get("priority", "normal"),
                    category=action_data.get("category", "task")
                ))

            return MemoParseResult(
                thoughts=thoughts,
                actions=actions,
                deadlines=deadlines,
                references=references
            )

        except Exception as e:
            logger.warning(f"Memo extraction failed: {e}")
            # Fallback: basic extraction
            return self._basic_extraction(transcript)

    def _basic_extraction(self, transcript: str) -> MemoParseResult:
        """Basic action extraction without LLM."""
        actions = []
        references = []

        # Split into sentences
        sentences = re.split(r'[.!?]', transcript)

        action_keywords = ['need to', 'should', 'must', 'have to', 'follow up', 'check', 'get', 'send', 'call', 'email']

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # Check for action indicators
            for keyword in action_keywords:
                if keyword in sentence.lower():
                    # Extract the action part
                    idx = sentence.lower().find(keyword)
                    action_text = sentence[idx:].strip()
                    if action_text:
                        due_date = self._extract_date_from_text(sentence)
                        priority = "urgent" if "urgent" in sentence.lower() or "asap" in sentence.lower() else "normal"

                        actions.append(ExtractedAction(
                            description=action_text,
                            due_date=due_date,
                            priority=priority,
                            category="task"
                        ))
                    break

        return MemoParseResult(
            thoughts=transcript,
            actions=actions,
            deadlines=[],
            references=references
        )

    def _extract_date_from_text(self, text: str) -> Optional[date]:
        """Try to extract a date from text."""
        text_lower = text.lower()

        if 'today' in text_lower:
            return date.today()
        elif 'tomorrow' in text_lower:
            return date.today() + timedelta(days=1)
        elif 'next week' in text_lower:
            return date.today() + timedelta(weeks=1)

        # Check for weekday
        weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        for i, day in enumerate(weekdays):
            if day in text_lower:
                today = date.today()
                days_ahead = i - today.weekday()
                if days_ahead <= 0:
                    days_ahead += 7
                return today + timedelta(days=days_ahead)

        return None

    def _parse_relative_date(self, date_str: str) -> Optional[date]:
        """Parse relative date strings."""
        date_str = date_str.lower().strip()

        if date_str in ['today', 'now']:
            return date.today()
        elif date_str == 'tomorrow':
            return date.today() + timedelta(days=1)
        elif date_str == 'next week':
            return date.today() + timedelta(weeks=1)
        elif 'week' in date_str:
            return date.today() + timedelta(weeks=1)

        return None


class ConversationalCorrector:
    """
    Handles natural language corrections to time entries.
    """

    CORRECTION_PROMPT = """You are helping correct a time entry. Parse the user's correction request.

CURRENT ENTRY:
- Matter: {current_matter}
- Activity: {current_activity}
- Duration: {current_duration}h
- Narrative: {current_narrative}

USER SAYS: {correction}

What should be changed? Return JSON:
{{
    "change_type": "matter|activity|duration|narrative|split|delete",
    "new_matter": "matter name or null",
    "new_activity": "activity type or null",
    "new_duration": hours as number or null,
    "new_narrative": "narrative text or null",
    "split_with": "second matter for split or null",
    "split_ratio": [0.5, 0.5] or null,
    "confidence": 0.0-1.0
}}"""

    def __init__(self, llm_client: OllamaClient):
        self.llm = llm_client

    def parse_correction(
        self,
        correction: str,
        current_matter: str = "",
        current_activity: str = "",
        current_duration: float = 0,
        current_narrative: str = ""
    ) -> Dict[str, Any]:
        """Parse a natural language correction request."""

        # Try pattern-based parsing first
        result = self._pattern_parse(correction)
        if result.get("confidence", 0) > 0.8:
            return result

        # Fall back to LLM
        prompt = self.CORRECTION_PROMPT.format(
            current_matter=current_matter or "Unknown",
            current_activity=current_activity or "Unknown",
            current_duration=current_duration,
            current_narrative=current_narrative or "None",
            correction=correction
        )

        try:
            result = self.llm.generate(prompt, json_mode=True, temperature=0.2)
            return result
        except Exception as e:
            logger.warning(f"Correction parsing failed: {e}")
            return {"change_type": "unknown", "confidence": 0.0}

    def _pattern_parse(self, text: str) -> Dict[str, Any]:
        """Pattern-based correction parsing."""
        text_lower = text.lower().strip()

        result = {"confidence": 0.0}

        # "actually that was for X" - matter change
        match = re.search(r'actually\s+(?:that\s+was\s+)?(?:for|on)\s+(.+)', text_lower)
        if match:
            result["change_type"] = "matter"
            result["new_matter"] = match.group(1).strip()
            result["confidence"] = 0.9
            return result

        # "change to X" - matter change
        match = re.search(r'change\s+(?:that\s+)?to\s+(.+)', text_lower)
        if match:
            result["change_type"] = "matter"
            result["new_matter"] = match.group(1).strip()
            result["confidence"] = 0.85
            return result

        # "should be X hours" - duration change
        match = re.search(r'should\s+be\s+(\d+(?:\.\d+)?)\s*(?:hours?|h)', text_lower)
        if match:
            result["change_type"] = "duration"
            result["new_duration"] = float(match.group(1))
            result["confidence"] = 0.9
            return result

        # "split between X and Y" - split
        match = re.search(r'split\s+(?:between|with)\s+(.+?)\s+and\s+(.+)', text_lower)
        if match:
            result["change_type"] = "split"
            result["new_matter"] = match.group(1).strip()
            result["split_with"] = match.group(2).strip()
            result["split_ratio"] = [0.5, 0.5]
            result["confidence"] = 0.85
            return result

        # "delete" - delete
        if re.search(r'\b(delete|remove)\b', text_lower):
            result["change_type"] = "delete"
            result["confidence"] = 0.9
            return result

        return result
