"""Narrative generation for professional billing descriptions."""
from .client import OllamaClient
from .prompts import get_narrative_prompt


class NarrativeGenerator:
    """
    Generates professional billing narratives from casual descriptions.
    
    Transforms:
    - "Went through the disclosure looking for emails" 
    → "Review and analysis of disclosure bundle; focus on email correspondence"
    """
    
    def __init__(self, llm_client: OllamaClient):
        self.llm = llm_client
    
    def generate(
        self,
        user_description: str,
        matter_name: str,
        activity_type: str,
        duration: float
    ) -> str:
        """
        Generate professional narrative from user's casual description.
        
        Args:
            user_description: What the user said about the work
            matter_name: Name of the matter
            activity_type: Activity code (DOCREV, DRAFT, etc.)
            duration: Hours spent
            
        Returns:
            Professional billing narrative
        """
        prompt = get_narrative_prompt(
            matter_name=matter_name,
            activity_type=activity_type,
            user_description=user_description,
            duration=duration
        )
        
        # Call LLM (no JSON mode for narrative)
        result = self.llm.generate(prompt, json_mode=False, temperature=0.3)
        
        narrative = result.get("text", "").strip()
        
        # Fallback if LLM fails
        if not narrative or len(narrative) < 5:
            narrative = self._fallback_narrative(activity_type, user_description)
        
        return narrative
    
    def _fallback_narrative(self, activity_type: str, description: str) -> str:
        """Simple fallback narrative if LLM fails."""
        type_labels = {
            "DOCREV": "Review of",
            "DRAFT": "Drafting",
            "RESEARCH": "Research regarding",
            "CALL": "Telephone attendance with",
            "CONF": "Meeting regarding",
            "EMAIL": "Correspondence regarding",
            "COURT": "Court attendance",
            "TRAVEL": "Travel",
            "ADMIN": "Administration"
        }
        
        label = type_labels.get(activity_type, "Work on")
        return f"{label} {description[:100]}"
