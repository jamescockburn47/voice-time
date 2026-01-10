"""Narrative generation for professional billing descriptions."""
import re
from .client import OllamaClient
from .prompts import get_narrative_prompt


class NarrativeGenerator:
    """
    Generates professional billing narratives from casual descriptions.
    FAITHFUL to what user said - does NOT invent details.
    
    Transforms:
    - "Went through the disclosure" → "Review of disclosure"
    - "Drafting skeleton" → "Drafting skeleton argument"
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
        Generate professional narrative - FAITHFUL to what user said.
        
        Args:
            user_description: What the user said about the work
            matter_name: Name of the matter
            activity_type: Activity code (DOCREV, DRAFT, etc.)
            duration: Hours spent
            
        Returns:
            Professional billing narrative (faithful to input)
        """
        # If description is very short or generic, use simple fallback
        clean_desc = user_description.strip()
        
        # Skip LLM for very short/generic descriptions - just clean up directly
        if len(clean_desc) < 20 or self._is_generic(clean_desc):
            return self._simple_cleanup(activity_type, clean_desc)
        
        # For longer descriptions, use LLM but with strict prompt
        prompt = get_narrative_prompt(
            matter_name=matter_name,
            activity_type=activity_type,
            user_description=clean_desc,
            duration=duration
        )
        
        # Call LLM with low temperature for consistency
        result = self.llm.generate(prompt, json_mode=False, temperature=0.1)
        
        narrative = result.get("text", "").strip()
        
        # Remove quotes if LLM wrapped the response
        narrative = narrative.strip('"\'')
        
        # Fallback if LLM fails or returns too much
        if not narrative or len(narrative) < 5 or len(narrative) > 150:
            narrative = self._simple_cleanup(activity_type, clean_desc)
        
        return narrative
    
    def _is_generic(self, description: str) -> bool:
        """Check if description is too generic to need LLM processing."""
        generic_patterns = [
            r'^working on',
            r'^work on',
            r'^starting',
            r'^beginning',
            r'^done',
            r'^finished',
            r'^general work',
            r'^matter work'
        ]
        lower = description.lower()
        return any(re.match(p, lower) for p in generic_patterns)
    
    def _simple_cleanup(self, activity_type: str, description: str) -> str:
        """Simple cleanup without LLM - just format nicely."""
        # Remove first person
        clean = re.sub(r'\b(I|I\'m|I am|I\'ve|I was)\b', '', description, flags=re.IGNORECASE)
        clean = clean.strip()
        
        # Capitalize first letter
        if clean:
            clean = clean[0].upper() + clean[1:] if len(clean) > 1 else clean.upper()
        
        # Add activity prefix if description is very short
        if len(clean) < 10:
            type_labels = {
                "DOCREV": "Document review",
                "DRAFT": "Drafting",
                "RESEARCH": "Legal research",
                "CALL": "Telephone attendance",
                "CONF": "Meeting",
                "EMAIL": "Correspondence",
                "COURT": "Court attendance",
                "TRAVEL": "Travel",
                "ADMIN": "General work"
            }
            prefix = type_labels.get(activity_type, "Work")
            if clean:
                return f"{prefix}: {clean}"
            return prefix
        
        return clean if clean else "General work"
