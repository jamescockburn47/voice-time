"""Morning plan parser using LLM."""
import json
from typing import List, Dict, Any, Optional
from datetime import time
from .client import OllamaClient
from .prompts import get_morning_plan_prompt


class PlanParser:
    """
    Parses morning planning transcripts into structured tasks.
    
    Uses LLM to extract:
    - Matter references
    - Activity types
    - Task titles
    - Scheduled times
    - Estimated durations
    """
    
    def __init__(self, llm_client: OllamaClient):
        self.llm = llm_client
    
    def parse(
        self,
        transcript: str,
        active_matters: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Parse morning plan transcript into structured tasks.
        
        Args:
            transcript: User's spoken/typed morning plan
            active_matters: List of active matters for context
            
        Returns:
            Dictionary with:
                - tasks: List of extracted tasks
                - unresolved_mentions: Matter names that couldn't be matched
        """
        # Format matters for prompt
        matters_json = self._format_matters(active_matters)
        
        # Generate prompt
        prompt = get_morning_plan_prompt(matters_json, transcript)
        
        # Call LLM with error handling
        try:
            result = self.llm.generate(prompt, json_mode=True, temperature=0.2)
        except Exception as e:
            # Return helpful error with context
            error_msg = str(e)
            if 'connection' in error_msg.lower() or 'refused' in error_msg.lower():
                raise ValueError("Ollama is not running. Please start Ollama: ollama serve")
            elif 'model' in error_msg.lower():
                raise ValueError(f"Model not found. Please run: ollama pull {self.llm.config.model}")
            else:
                raise ValueError(f"AI error: {error_msg}")
        
        # Parse and validate tasks
        tasks = result.get("tasks", [])
        validated_tasks = []
        
        for task in tasks:
            validated_task = self._validate_task(task)
            if validated_task:
                validated_tasks.append(validated_task)
        
        # If no tasks were extracted, provide helpful feedback
        if not validated_tasks:
            # Check if LLM returned anything useful
            parsing_notes = result.get("parsing_notes", "")
            raise ValueError(
                f"Could not extract any tasks from your plan. "
                f"Try being more specific, e.g., 'Today I need to work on Thompson disclosure'. "
                f"{('AI note: ' + parsing_notes) if parsing_notes else ''}"
            )
        
        return {
            "tasks": validated_tasks,
            "unresolved_mentions": result.get("unresolved_mentions", []),
            "parsing_notes": result.get("parsing_notes", "")
        }
    
    def _format_matters(self, matters: List[Dict[str, Any]]) -> str:
        """Format matters list for prompt."""
        if not matters:
            return "No active matters"
        
        lines = []
        for matter in matters:
            ref = matter.get("matter_ref", "")
            name = matter.get("display_name", "")
            aliases = matter.get("aliases", [])
            
            line = f"- {name}"
            if ref:
                line += f" ({ref})"
            if aliases:
                line += f" [also: {', '.join(aliases)}]"
            
            lines.append(line)
        
        return "\n".join(lines)
    
    def _validate_task(self, task: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Validate and normalize a task."""
        try:
            # Required fields
            if not task.get("title"):
                return None
            
            validated = {
                "matter_ref": task.get("matter_ref"),
                "activity_type": task.get("activity_type", "ADMIN"),
                "title": task["title"],
                "scheduled_time": None,
                "estimated_hours": None
            }
            
            # Parse scheduled time
            if task.get("scheduled_time"):
                validated["scheduled_time"] = self._parse_time(task["scheduled_time"])
            
            # Parse estimated hours
            if task.get("estimated_hours"):
                try:
                    validated["estimated_hours"] = float(task["estimated_hours"])
                except (ValueError, TypeError):
                    pass
            
            return validated
            
        except Exception as e:
            print(f"Error validating task: {e}")
            return None
    
    def _parse_time(self, time_str: str) -> Optional[time]:
        """Parse time string to time object."""
        try:
            # Handle HH:MM format
            parts = time_str.split(":")
            if len(parts) == 2:
                hour, minute = int(parts[0]), int(parts[1])
                if 0 <= hour < 24 and 0 <= minute < 60:
                    return time(hour, minute)
        except:
            pass
        return None
