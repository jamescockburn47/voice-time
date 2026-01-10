"""All LLM prompts centralised."""


def get_morning_plan_prompt(matters_json: str, transcript: str) -> str:
    """Generate morning planning prompt - FLEXIBLE and forgiving."""
    return f'''Parse a lawyer's daily plan into tasks. Be flexible and extract what you can.

ACTIVE MATTERS (user might mention these):
{matters_json}

ACTIVITY TYPES (guess the best match):
- DOCREV: Document review, reading, analysis
- DRAFT: Drafting, writing, preparing
- RESEARCH: Legal research, case law
- CALL: Phone calls, telephone
- CONF: Meetings, conferences
- EMAIL: Correspondence, emails
- COURT: Court hearings
- TRAVEL: Travel time
- ADMIN: Administrative, general work

WHAT THE USER SAID:
"{transcript}"

INSTRUCTIONS:
- Extract ANY tasks you can identify (even vague ones)
- If unsure about matter, set matter_ref to null (it's okay!)
- If unsure about activity, use ADMIN (it's okay!)
- Be LENIENT - extract something rather than nothing
- Even "working on stuff" should create a task
- If you see ANY work intention, create a task for it

Respond with JSON:
{{
  "tasks": [
    {{
      "matter_ref": "partial name" or null,
      "activity_type": "best guess or ADMIN",
      "title": "what they said or best guess",
      "scheduled_time": "HH:MM" or null,
      "estimated_hours": number or null
    }}
  ],
  "unresolved_mentions": [],
  "parsing_notes": "brief note about what you extracted"
}}

IMPORTANT: Always return valid JSON even if you're unsure. Create at least one task if ANY work is mentioned.'''


def get_narrative_prompt(
    matter_name: str,
    activity_type: str,
    user_description: str,
    duration: float
) -> str:
    """Generate narrative generation prompt."""
    return f'''Generate a professional legal billing narrative from this description.

MATTER: {matter_name}
ACTIVITY TYPE: {activity_type}
USER DESCRIPTION: "{user_description}"
DURATION: {duration} hours

Requirements:
- Professional, neutral tone suitable for client billing
- Concise but specific
- No first person ("I reviewed" → "Review of...")
- Include key details mentioned
- Typical length: 10-30 words

Respond with the narrative only, no explanation.'''


def get_matter_resolution_prompt(
    query: str,
    candidates: list,
    context: str = ""
) -> str:
    """Generate prompt for resolving ambiguous matter references."""
    candidates_json = "\n".join(
        f"- {i+1}. {c['display_name']} ({c['matter_ref']})" 
        for i, c in enumerate(candidates)
    )
    
    context_str = f"\nCONTEXT: {context}" if context else ""
    
    return f'''You are helping resolve an ambiguous reference to a legal matter.

USER SAID: "{query}"{context_str}

POSSIBLE MATCHES:
{candidates_json}

Which matter is most likely? Consider:
- Phonetic similarity
- Recent usage patterns
- Context clues

Respond with JSON:
{{
  "choice": 1,
  "confidence": 0.85,
  "reason": "Brief explanation"
}}'''


def get_activity_inference_prompt(
    utterance: str,
    context: str = ""
) -> str:
    """Generate prompt for inferring activity type from utterance."""
    context_str = f"\nCONTEXT: {context}" if context else ""
    
    return f'''Classify this legal work activity.

UTTERANCE: "{utterance}"{context_str}

ACTIVITY TYPES:
- DOCREV: Document review, reading, analysis
- DRAFT: Drafting, writing, preparing documents
- RESEARCH: Legal research, checking authorities
- CALL: Phone calls, telephone attendances
- CONF: Meetings, conferences, attendances
- EMAIL: Correspondence, emails, letters
- COURT: Court hearings, applications
- TRAVEL: Travel time
- ADMIN: Administrative, internal matters

Respond with JSON:
{{
  "activity_type": "DOCREV",
  "confidence": 0.9,
  "keywords_matched": ["reviewing", "disclosure"]
}}'''
