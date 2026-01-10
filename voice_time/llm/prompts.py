"""All LLM prompts centralised."""


def get_morning_plan_prompt(matters_json: str, transcript: str) -> str:
    """Generate morning planning prompt."""
    return f'''You are parsing a lawyer's morning plan into structured tasks.

ACTIVE MATTERS:
{matters_json}

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

USER'S PLAN:
"{transcript}"

Extract tasks from the plan. For each task, provide:
- matter_ref: The matter reference or name mentioned (or null for general admin)
- activity_type: One of the codes above
- title: Brief description of the task
- scheduled_time: If a specific time is mentioned (HH:MM format, or null)
- estimated_hours: If duration is mentioned or implied (or null)

Respond with valid JSON only:
{{
  "tasks": [
    {{
      "matter_ref": "Smith" or null,
      "activity_type": "DOCREV",
      "title": "Disclosure review",
      "scheduled_time": null,
      "estimated_hours": null
    }}
  ],
  "unresolved_mentions": ["any matter names you couldn't confidently identify"]
}}'''


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
