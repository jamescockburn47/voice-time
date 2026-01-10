# Voice Time Recording System - Development Prompt

## Project Overview

Build a voice-activated time recording system for a litigation lawyer. The core insight is that time recording becomes trivial when combined with morning planning - the system knows what you intended to do, so matching "done with that" to the right matter/task is easy.

This is NOT just voice dictation with parsing. It's a stateful day controller that understands legal work, infers duration from context, and generates professional narratives from casual speech.

## Key Differentiators (These Make It Smart)

1. **Morning planning context** - User describes their day; system uses this to resolve ambiguous references later
2. **Temporal awareness** - System knows current time, time since last entry, and can infer duration from natural language ("couple of hours", "all morning", "since lunch")
3. **Legal vocabulary mapping** - "Reviewing disclosure" → Document Review, "drafting skeleton" → Drafting, without explicit codes
4. **Context persistence** - Active matter stays active until explicitly switched; "finished that" resolves from context
5. **Task stack for interruptions** - Handle "quick call about Brown" then "back to what I was doing"
6. **Narrative upgrade** - "Went through witness statements looking for the meeting bit" → "Review and analysis of witness evidence; particular focus on chronology of April meeting"

## Technical Stack

- **Language**: Python 3.11+
- **Database**: SQLite with SQLAlchemy
- **LLM**: Ollama (Qwen2.5-1.5B-Instruct) - Small, fast, excellent at JSON output
- **Speech-to-Text**: faster-whisper (Python bindings for whisper.cpp)
- **UI**: Flask + HTMX for minimal web interface (MVP), upgradeable to Tauri later
- **Audio**: sounddevice for microphone capture

## Project Structure

```
voice_time/
├── README.md
├── ARCHITECTURE.md
├── PLAN.md
├── requirements.txt
├── config.yaml
├── run.py                      # Entry point
├── voice_time/
│   ├── __init__.py
│   ├── config.py               # Configuration management
│   ├── database/
│   │   ├── __init__.py
│   │   ├── models.py           # SQLAlchemy models
│   │   ├── schema.py           # Database setup
│   │   └── queries.py          # Common queries
│   ├── core/
│   │   ├── __init__.py
│   │   ├── state_machine.py    # Day state management
│   │   ├── matcher.py          # Matter/task matching with recency
│   │   ├── temporal.py         # Time inference from natural language
│   │   ├── intent.py           # Intent classification (fast path)
│   │   └── stack.py            # Task stack for interruptions
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── client.py           # Ollama client wrapper
│   │   ├── prompts.py          # All prompts centralised
│   │   ├── parser.py           # Morning plan parser
│   │   └── narrative.py        # Narrative generation
│   ├── voice/
│   │   ├── __init__.py
│   │   ├── transcribe.py       # Whisper integration
│   │   └── capture.py          # Audio capture
│   ├── web/
│   │   ├── __init__.py
│   │   ├── app.py              # Flask app
│   │   ├── routes.py           # API routes
│   │   ├── templates/
│   │   │   ├── base.html
│   │   │   ├── index.html      # Main dashboard
│   │   │   ├── plan.html       # Morning planning
│   │   │   ├── review.html     # End-of-day review
│   │   │   └── components/
│   │   │       ├── task_list.html
│   │   │       ├── work_log.html
│   │   │       └── matter_picker.html
│   │   └── static/
│   │       ├── style.css
│   │       └── app.js
│   └── export/
│       ├── __init__.py
│       └── csv_export.py       # Export to billing system
├── tests/
│   ├── __init__.py
│   ├── test_matcher.py
│   ├── test_temporal.py
│   ├── test_intent.py
│   └── test_parser.py
└── data/
    └── sample_matters.csv      # Sample matter data for testing
```

---

# FILE: ARCHITECTURE.md

Create this file with the following content:

```markdown
# Voice Time Recording System - Architecture

## Design Philosophy

The system is a **stateful day controller** where:
- The **state machine** is the runtime brain (deterministic, fast)
- The **LLM** is a parser and synthesiser (used sparingly, for complex tasks)
- **Voice** is the primary input, but the system works without it

### Model Choice: Qwen2.5-1.5B-Instruct
We use a small (1.5B parameter) model because:
- **Fast**: ~200-400ms inference on CPU, sub-100ms with GPU
- **Excellent JSON output**: Specifically optimised for structured data
- **Good enough**: For intent classification, matter matching, and narrative generation
- **Low resource**: ~2GB RAM, runs on any modern laptop

This means the "slow path" is now fast enough that you could use it for everything if you wanted. The fast path (heuristics) still exists because: (a) it's deterministic, (b) it works offline, and (c) it's still faster. But if a heuristic fails, calling the LLM won't tank UX.

### Non-Negotiables
1. Sub-second response for during-day logging
2. Never silently misallocate time - ask if uncertain
3. Unexpected tasks are first-class, not edge cases
4. Works even when the morning plan is incomplete or wrong
5. All data stays local by default

## Component Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                          │
│                    (Web UI / CLI / Voice)                       │
└─────────────────────────────────┬───────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                      INTERACTION LAYER                          │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │   Voice     │  │    Text     │  │     Hotkey/Button       │ │
│  │   Input     │  │    Input    │  │       Triggers          │ │
│  └──────┬──────┘  └──────┬──────┘  └────────────┬────────────┘ │
│         │                │                      │               │
│         └────────────────┴──────────────────────┘               │
│                          │                                      │
│                          ▼                                      │
│              ┌───────────────────────┐                         │
│              │   Transcription       │                         │
│              │   (faster-whisper)    │                         │
│              └───────────┬───────────┘                         │
└──────────────────────────┼──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     PROCESSING LAYER                            │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                 FAST PATH (No LLM)                       │   │
│  │                                                          │   │
│  │  1. Intent Classification (embeddings + heuristics)      │   │
│  │  2. Entity Extraction (regex + fuzzy match)              │   │
│  │  3. Context Resolution (state machine + recency)         │   │
│  │  4. Confidence Scoring                                   │   │
│  │                                                          │   │
│  │  Handles: ~80% of during-day utterances                  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                      │
│           ┌──────────────┴──────────────┐                      │
│           │                             │                      │
│           ▼                             ▼                      │
│  ┌─────────────────┐          ┌─────────────────┐              │
│  │  High Confidence │          │  Low Confidence  │              │
│  │  → Execute       │          │  → Clarify OR    │              │
│  └────────┬────────┘          │    → LLM Path    │              │
│           │                    └────────┬────────┘              │
│           │                             │                      │
│           │                             ▼                      │
│           │                    ┌─────────────────┐              │
│           │                    │   SLOW PATH     │              │
│           │                    │   (Ollama LLM)  │              │
│           │                    │                 │              │
│           │                    │  • Morning plan │              │
│           │                    │  • Narrative    │              │
│           │                    │  • Ambiguous    │              │
│           │                    └────────┬────────┘              │
│           │                             │                      │
│           └──────────────┬──────────────┘                      │
│                          │                                      │
└──────────────────────────┼──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                      STATE LAYER                                │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   STATE MACHINE                          │   │
│  │                                                          │   │
│  │  • current_day_plan                                      │   │
│  │  • task_stack (for interruptions)                        │   │
│  │  • active_matter_id                                      │   │
│  │  • active_task_id                                        │   │
│  │  • current_work_block                                    │   │
│  │  • last_interaction_time                                 │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PERSISTENCE LAYER                            │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    SQLite Database                       │   │
│  │                                                          │   │
│  │  • matters (with aliases, recency scores)                │   │
│  │  • activity_types (with vocabulary mappings)             │   │
│  │  • day_plans                                             │   │
│  │  • planned_tasks                                         │   │
│  │  • work_logs                                             │   │
│  │  • voice_events (immutable audit trail)                  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow Examples

### Morning Planning
```
User speaks: "Today I need to finish Smith disclosure, draft the 
              Brown skeleton, and I've got a call with counsel at 3"
                                    │
                                    ▼
                          [Transcription]
                                    │
                                    ▼
                    [LLM Parser - SLOW PATH OK]
                                    │
                                    ▼
                    Extract: 3 tasks, 2 matters, 1 time anchor
                                    │
                                    ▼
                    [Matter Resolution]
                    "Smith" → Smith v Jones (95% confidence)
                    "Brown" → Brown v Welsh (92% confidence)
                                    │
                                    ▼
                    [Create PlannedTasks]
                    □ Smith v Jones | DOCREV | "Disclosure review"
                    □ Brown v Welsh | DRAFT  | "Skeleton argument"
                    □ Brown v Welsh | CONF   | "Call with counsel" @15:00
                                    │
                                    ▼
                    [Confirm with user]
                    "3 tasks across 2 matters. Anything else?"
```

### During-Day Logging (Fast Path)
```
User speaks: "Done with the disclosure"
                                    │
                                    ▼
                          [Transcription]
                                    │
                                    ▼
               [Intent Classification - FAST PATH]
               "done" + past tense → COMPLETE intent (98%)
                                    │
                                    ▼
               [Entity Extraction - FAST PATH]
               "disclosure" → matches planned task "Disclosure review"
                                    │
                                    ▼
               [Context Resolution]
               No explicit matter → check active_matter_id
               Active: Smith v Jones → MATCH
                                    │
                                    ▼
               [Duration Inference]
               Last entry: 09:15, Now: 11:45
               Elapsed: 2.5 hours
               Planned task scope: "finish" suggests substantial
               → Infer 2.5 hours (high confidence)
                                    │
                                    ▼
               [Create WorkLog]
               Smith v Jones | DOCREV | 2.5 hrs
               "Review and analysis of disclosure bundle"
                                    │
                                    ▼
               [Update State]
               Mark task complete
               Clear active_task_id
               Response: "Logged 2.5 hours to Smith, disclosure review. Done."
```

### Interruption Handling
```
State: Working on Smith disclosure (on stack)

User: "Quick call about Brown"
                                    │
                                    ▼
               [Intent: START new task]
               [Entity: "Brown" → Brown v Welsh]
               [Activity: "call" → CALL]
               [Modifier: "quick" → expect short duration]
                                    │
                                    ▼
               [Stack Operation: PUSH]
               Push current (Smith/disclosure) to stack
               Set active: Brown/ad-hoc call
               Start new work block
                                    │
                                    ▼
User: "Done, back to what I was doing"
                                    │
                                    ▼
               [Intent: COMPLETE + RETURN]
               [Stack Operation: POP]
               Close Brown call block (infer ~5-10 mins from "quick")
               Restore Smith/disclosure from stack
               Resume work block
```

## Intent Classification

### Intent Types
| Intent | Trigger Patterns | Examples |
|--------|-----------------|----------|
| PLAN | morning, today, planning | "Today I need to..." |
| START | starting, beginning, working on | "Working on Smith now" |
| COMPLETE | done, finished, completed | "Done with that" |
| SWITCH | switching, moving to, back to | "Back to drafting" |
| PAUSE | break, lunch, stepping away | "Taking lunch" |
| STATUS | what's left, where am I, status | "What's outstanding?" |
| LOG_HISTORICAL | spent, did, was | "Spent an hour on emails" |
| ADD_TASK | also need, add, forgot | "Also need to chase expert" |
| CORRECT | actually, change, not X but Y | "Actually that was 2 hours" |
| ALLOCATE | that was for, put that on | "Put that on Smith" |

### Fast Path Classification
```python
# Heuristic signals (checked first, fast)
COMPLETION_SIGNALS = ["done", "finished", "completed", "wrapped up", "that's it"]
START_SIGNALS = ["starting", "beginning", "working on", "moving to"]
SWITCH_SIGNALS = ["back to", "switching to", "returning to"]
QUERY_SIGNALS = ["what's", "how much", "status", "outstanding"]

# Tense detection
PAST_TENSE_PATTERNS = [r"\bwas\b", r"\bspent\b", r"\bdid\b", r"\btook\b"]
PRESENT_PATTERNS = [r"\bam\b", r"\b'm\b", r"\bstarting\b", r"\bbeginning\b"]

# Duration language
DURATION_QUICK = ["quick", "brief", "short", "5 minutes", "few minutes"]
DURATION_MEDIUM = ["about an hour", "hour or so", "a while"]
DURATION_LONG = ["all morning", "most of the day", "hours", "ages"]
```

## Activity Type Inference

### Legal Vocabulary Mapping
```python
ACTIVITY_VOCABULARY = {
    "DOCREV": [
        "reviewing", "reading", "going through", "analysing", "analysis",
        "disclosure", "bundle", "documents", "exhibits", "evidence",
        "witness statement", "pleading", "skeleton"
    ],
    "DRAFT": [
        "drafting", "writing", "preparing", "amending", "revising",
        "skeleton", "witness statement", "letter", "application",
        "particulars", "defence", "reply"
    ],
    "RESEARCH": [
        "researching", "looking into", "checking", "authorities",
        "case law", "legislation", "limitation", "law on"
    ],
    "CALL": [
        "call", "phone", "telephone", "spoke to", "speaking with",
        "conference call", "teams call", "zoom"
    ],
    "CONF": [
        "meeting", "conference", "attendance", "with counsel",
        "con", "chambers"
    ],
    "EMAIL": [
        "email", "emailing", "correspondence", "letter",
        "responding to", "reply to"
    ],
    "COURT": [
        "court", "hearing", "trial", "CMC", "PTR", "application",
        "before the judge", "master"
    ],
    "TRAVEL": [
        "travelling", "travel", "train", "heading to", "journey"
    ],
    "ADMIN": [
        "admin", "internal", "billing", "file review", "housekeeping"
    ]
}
```

## Temporal Inference

### Duration Language Parser
```python
DURATION_MAPPINGS = {
    # Explicit
    r"(\d+)\s*hours?": lambda m: float(m.group(1)),
    r"(\d+)\s*mins?": lambda m: float(m.group(1)) / 60,
    r"(\d+\.?\d*)\s*hrs?": lambda m: float(m.group(1)),
    
    # Natural language
    "quick": 0.1,  # 6 minutes
    "brief": 0.2,
    "short": 0.25,
    "few minutes": 0.1,
    "about an hour": 1.0,
    "hour or so": 1.0,
    "couple of hours": 2.0,
    "few hours": 3.0,
    "most of the morning": 3.5,
    "all morning": 4.0,
    "most of the afternoon": 3.5,
    "all afternoon": 4.0,
    "all day": 7.5,
    "ages": None,  # Infer from elapsed time
}

TIME_ANCHORS = {
    "since lunch": "13:00",
    "since this morning": "09:00",
    "after the call": None,  # Resolve from calendar/last entry
    "before lunch": ("09:00", "12:30"),
    "this afternoon": ("13:00", "now"),
}
```

## Future Architecture (Post-MVP)

### Phase 2: Enhanced Voice
- Wake word detection ("Hey Timekeeper")
- Continuous listening mode
- Voice confirmation/feedback

### Phase 3: Calendar Integration
- macOS: EventKit
- Windows: Microsoft Graph API
- Auto-create tasks from calendar events
- Auto-close work blocks when meetings start

### Phase 4: Desktop App
- Tauri-based cross-platform app
- System tray presence
- Global hotkey activation
- Native notifications

### Phase 5: Practice Management Integration
- Clio API connector
- ActionStep integration
- LEDES export format
- Direct billing system push
```

---

# FILE: PLAN.md

Create this file with the following content:

```markdown
# Voice Time Recording System - Development Plan

## Vision

A voice-first time recording system that understands how lawyers actually work. You describe your day in the morning, log time with natural speech throughout the day, and review/export at end of day. The system infers what it can and asks only when genuinely uncertain.

## MVP Scope (Weekend Build)

### In Scope
- [x] Morning planning via voice/text
- [x] Matter management with aliases
- [x] During-day logging with context awareness
- [x] Natural duration language ("couple of hours")
- [x] Task stack for interruptions
- [x] End-of-day review
- [x] Narrative generation
- [x] CSV export
- [x] Simple web UI

### Out of Scope (Future)
- [ ] Calendar integration
- [ ] Desktop app (Tauri)
- [ ] Wake word detection
- [ ] Practice management system connectors
- [ ] Multi-device sync
- [ ] Team features

## Development Phases

### Phase 1: Foundation (Friday Evening)
**Goal**: Working database and basic CLI

- [ ] Project setup (virtualenv, requirements)
- [ ] SQLite database schema
- [ ] SQLAlchemy models
- [ ] Basic matter CRUD
- [ ] Activity type seed data
- [ ] Simple CLI REPL for testing

**Test**: Can create matters, list them, basic queries work

### Phase 2: Core Intelligence (Saturday)
**Goal**: The smart matching and inference engine

#### Morning (3-4 hours)
- [ ] Ollama client wrapper
- [ ] Morning planning prompt
- [ ] Plan parser (LLM-based)
- [ ] Matter alias matching with recency weighting
- [ ] PlannedTask creation

**Test**: Speak a morning plan, see correctly parsed tasks

#### Afternoon (3-4 hours)
- [ ] Intent classifier (heuristic + embedding)
- [ ] Activity type inference from vocabulary
- [ ] Temporal inference (duration language)
- [ ] State machine (current task, active matter)
- [ ] Task stack for interruptions
- [ ] Work block creation/closure

**Test**: Log several entries conversationally, verify correct allocation

### Phase 3: Polish & Voice (Sunday)

#### Morning (3-4 hours)
- [ ] faster-whisper integration
- [ ] Audio capture (push-to-talk)
- [ ] End-of-day reconciliation logic
- [ ] Unallocated time detection
- [ ] Narrative generation prompt

**Test**: Full voice workflow - plan, log, review

#### Afternoon (3-4 hours)
- [ ] Flask web UI
- [ ] Dashboard (today's plan, logged time)
- [ ] Review interface (edit, allocate, approve)
- [ ] CSV export
- [ ] Error handling and edge cases

**Test**: Complete day simulation with real matters

## Database Schema

```sql
-- Matters (your cases/files)
CREATE TABLE matters (
    id TEXT PRIMARY KEY,
    matter_ref TEXT,              -- Billing system reference
    display_name TEXT NOT NULL,
    client TEXT,
    is_active BOOLEAN DEFAULT 1,
    last_used_at TIMESTAMP,
    use_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Matter aliases for fuzzy matching
CREATE TABLE matter_aliases (
    id TEXT PRIMARY KEY,
    matter_id TEXT REFERENCES matters(id),
    alias TEXT NOT NULL,
    is_primary BOOLEAN DEFAULT 0,
    UNIQUE(matter_id, alias)
);

-- Activity types (your billing codes)
CREATE TABLE activity_types (
    id TEXT PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,    -- e.g., "DOCREV", "DRAFT"
    label TEXT NOT NULL,          -- e.g., "Document Review"
    is_billable BOOLEAN DEFAULT 1,
    display_order INTEGER
);

-- Vocabulary mappings for activity inference
CREATE TABLE activity_vocabulary (
    id TEXT PRIMARY KEY,
    activity_type_id TEXT REFERENCES activity_types(id),
    phrase TEXT NOT NULL,
    weight REAL DEFAULT 1.0
);

-- Day plans
CREATE TABLE day_plans (
    id TEXT PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source TEXT DEFAULT 'voice'   -- voice, typed, rolled_over
);

-- Planned tasks
CREATE TABLE planned_tasks (
    id TEXT PRIMARY KEY,
    day_plan_id TEXT REFERENCES day_plans(id),
    matter_id TEXT REFERENCES matters(id),  -- NULL for general admin
    activity_type_id TEXT REFERENCES activity_types(id),
    title TEXT NOT NULL,
    scheduled_time TIME,          -- From calendar or explicit mention
    estimated_hours REAL,
    status TEXT DEFAULT 'planned', -- planned, in_progress, done, deferred
    sort_order INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Voice events (immutable audit trail)
CREATE TABLE voice_events (
    id TEXT PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    transcript TEXT NOT NULL,
    audio_path TEXT,              -- Optional path to audio file
    intent TEXT,
    confidence REAL,
    processed BOOLEAN DEFAULT 0
);

-- Work logs (the actual time entries)
CREATE TABLE work_logs (
    id TEXT PRIMARY KEY,
    matter_id TEXT REFERENCES matters(id),
    activity_type_id TEXT REFERENCES activity_types(id),
    planned_task_id TEXT REFERENCES planned_tasks(id),  -- NULL for ad-hoc
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    duration_hours REAL NOT NULL,
    narrative TEXT,
    source_event_id TEXT REFERENCES voice_events(id),
    allocation_status TEXT DEFAULT 'allocated',  -- allocated, needs_review
    is_exported BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Session state (runtime, but persisted for recovery)
CREATE TABLE session_state (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_matters_active ON matters(is_active);
CREATE INDEX idx_matters_last_used ON matters(last_used_at DESC);
CREATE INDEX idx_work_logs_date ON work_logs(started_at);
CREATE INDEX idx_planned_tasks_date ON planned_tasks(day_plan_id);
CREATE INDEX idx_voice_events_timestamp ON voice_events(timestamp);
```

## Key Algorithms

### Matter Matching with Recency

```python
def find_matter(query: str, matters: List[Matter]) -> MatchResult:
    """
    Match a query string to a matter using:
    1. Exact alias match
    2. Fuzzy alias match (weighted by recency)
    3. Substring match on display_name
    
    Recency weight: matters used today get 2x, this week 1.5x, older 1x
    """
    candidates = []
    
    for matter in matters:
        # Check all aliases
        for alias in matter.aliases:
            score = fuzzy_ratio(query.lower(), alias.lower())
            
            # Apply recency weight
            recency_weight = calculate_recency_weight(matter.last_used_at)
            weighted_score = score * recency_weight
            
            if weighted_score > 60:  # Threshold
                candidates.append((matter, weighted_score, alias))
    
    # Sort by weighted score
    candidates.sort(key=lambda x: x[1], reverse=True)
    
    if not candidates:
        return MatchResult(match=None, confidence=0)
    
    best = candidates[0]
    
    # Check if ambiguous (top 2 are close)
    if len(candidates) > 1:
        if candidates[1][1] > best[1] * 0.9:
            return MatchResult(
                match=None,
                confidence=0,
                ambiguous=True,
                candidates=candidates[:3]
            )
    
    return MatchResult(
        match=best[0],
        confidence=best[1] / 100,
        matched_alias=best[2]
    )
```

### Duration Inference

```python
def infer_duration(
    utterance: str,
    last_entry_time: datetime,
    current_time: datetime,
    modifier: str = None  # "quick", "long", etc.
) -> DurationResult:
    """
    Infer duration from:
    1. Explicit mention ("2 hours")
    2. Natural language ("couple of hours")
    3. Time anchor ("since lunch")
    4. Elapsed time since last entry
    5. Modifier hints ("quick" = short)
    """
    
    # 1. Check for explicit duration
    explicit = extract_explicit_duration(utterance)
    if explicit:
        return DurationResult(hours=explicit, confidence=0.95, source="explicit")
    
    # 2. Check for natural language duration
    natural = extract_natural_duration(utterance)
    if natural:
        return DurationResult(hours=natural, confidence=0.85, source="natural")
    
    # 3. Check for time anchors
    anchor = extract_time_anchor(utterance, current_time)
    if anchor:
        hours = (current_time - anchor).total_seconds() / 3600
        return DurationResult(hours=round(hours, 1), confidence=0.8, source="anchor")
    
    # 4. Calculate elapsed time
    elapsed = (current_time - last_entry_time).total_seconds() / 3600
    
    # 5. Apply modifier adjustments
    if modifier == "quick":
        inferred = min(elapsed, 0.25)
        confidence = 0.7
    elif modifier == "brief":
        inferred = min(elapsed, 0.5)
        confidence = 0.7
    elif elapsed < 0.5:
        inferred = elapsed
        confidence = 0.6
    else:
        # For longer periods, less confident about elapsed = actual
        inferred = elapsed
        confidence = 0.5
    
    return DurationResult(
        hours=round(inferred, 1),
        confidence=confidence,
        source="elapsed",
        needs_confirmation=confidence < 0.7
    )
```

## LLM Prompts

### Morning Planning Parser

```python
MORNING_PLAN_PROMPT = '''You are parsing a lawyer's morning plan into structured tasks.

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
{
  "tasks": [
    {
      "matter_ref": "Smith" or null,
      "activity_type": "DOCREV",
      "title": "Disclosure review",
      "scheduled_time": null,
      "estimated_hours": null
    }
  ],
  "unresolved_mentions": ["any matter names you couldn't confidently identify"]
}'''
```

### Narrative Generation

```python
NARRATIVE_PROMPT = '''Generate a professional legal billing narrative from this description.

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
```

## Configuration

```yaml
# config.yaml
app:
  name: "Voice Time"
  data_dir: "~/.voice_time"
  
ollama:
  host: "http://localhost:11434"
  model: "qwen2.5:1.5b-instruct"  # Small, fast, excellent JSON output
  timeout: 30
  
whisper:
  model: "base.en"  # Options: tiny.en, base.en, small.en
  device: "cpu"  # or "cuda" if available
  
audio:
  sample_rate: 16000
  channels: 1
  
matching:
  confidence_threshold: 0.7
  ambiguity_threshold: 0.9  # Top 2 within 90% = ambiguous
  
temporal:
  working_day_start: "09:00"
  working_day_end: "18:00"
  lunch_start: "12:30"
  lunch_end: "13:30"
  
export:
  format: "csv"
  date_format: "%Y-%m-%d"
  time_format: "%H:%M"
```

## Testing Scenarios

### Scenario 1: Complete Day
```
Morning: "Today I need to finish the Smith disclosure review, draft 
          the Brown skeleton argument, and I've got a call with 
          counsel at 3"

10:30:   "Done with Smith disclosure, took all morning"
12:15:   "Quick email to the expert for Smith"
12:30:   "Taking lunch"
13:30:   "Back, starting on Brown skeleton"
14:45:   "Quick call about Smith - the expert got back to me"
14:50:   "Back to the skeleton"
15:45:   "Call's done" [counsel call]
16:30:   "Finished the skeleton"
17:00:   "What's left?"
17:15:   "Actually add another 30 mins to the skeleton, forgot to log 
          the amendments"
```

Expected output:
- Smith v Jones: 4.1 hrs (DOCREV 3.5, EMAIL 0.1, CALL 0.5)
- Brown v Welsh: 4.25 hrs (DRAFT 3.5, CONF 0.75)

### Scenario 2: Unexpected Tasks
```
Morning: "Working on Smith today"

10:00:   "Got a call from the Brown client about costs"
10:15:   "Back to Smith"
11:30:   "Need to quickly review the Jones CMC bundle - wasn't planning that"
12:00:   "Done with Jones, back to Smith"
```

Expected: System handles ad-hoc Brown call and Jones review without losing Smith context.

### Scenario 3: Minimal Planning
```
Morning: [No plan given]

10:00:   "Spent the morning on Smith disclosure"
14:00:   "Couple of hours drafting the Brown skeleton"
16:00:   "Various emails, split between Smith and Brown"
```

Expected: System works in reactive mode, asks for allocation on ambiguous "various emails".
```

---

# FILE: requirements.txt

```
# Core
sqlalchemy>=2.0.0
pydantic>=2.0.0
pyyaml>=6.0

# LLM
ollama>=0.1.0
httpx>=0.24.0

# Speech
faster-whisper>=0.9.0
sounddevice>=0.4.6
numpy>=1.24.0

# Web UI
flask>=3.0.0
flask-cors>=4.0.0

# Utilities
rapidfuzz>=3.0.0
python-dateutil>=2.8.0
rich>=13.0.0  # For nice CLI output

# Development
pytest>=7.0.0
pytest-asyncio>=0.21.0
black>=23.0.0
```

---

# Now build the implementation

Start with these files in order:

## 1. voice_time/config.py

```python
"""Configuration management."""
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
import yaml


@dataclass
class OllamaConfig:
    host: str = "http://localhost:11434"
    model: str = "qwen2.5:7b-instruct"
    timeout: int = 30


@dataclass
class WhisperConfig:
    model: str = "base.en"
    device: str = "cpu"


@dataclass
class AudioConfig:
    sample_rate: int = 16000
    channels: int = 1


@dataclass
class MatchingConfig:
    confidence_threshold: float = 0.7
    ambiguity_threshold: float = 0.9


@dataclass
class TemporalConfig:
    working_day_start: str = "09:00"
    working_day_end: str = "18:00"
    lunch_start: str = "12:30"
    lunch_end: str = "13:30"


@dataclass
class Config:
    data_dir: Path = field(default_factory=lambda: Path.home() / ".voice_time")
    ollama: OllamaConfig = field(default_factory=OllamaConfig)
    whisper: WhisperConfig = field(default_factory=WhisperConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    matching: MatchingConfig = field(default_factory=MatchingConfig)
    temporal: TemporalConfig = field(default_factory=TemporalConfig)
    
    @classmethod
    def load(cls, path: Optional[Path] = None) -> "Config":
        """Load config from YAML file, with defaults."""
        config = cls()
        
        if path is None:
            path = Path("config.yaml")
        
        if path.exists():
            with open(path) as f:
                data = yaml.safe_load(f)
                # Merge with defaults
                if data:
                    if "ollama" in data:
                        config.ollama = OllamaConfig(**data["ollama"])
                    if "whisper" in data:
                        config.whisper = WhisperConfig(**data["whisper"])
                    if "audio" in data:
                        config.audio = AudioConfig(**data["audio"])
                    if "matching" in data:
                        config.matching = MatchingConfig(**data["matching"])
                    if "temporal" in data:
                        config.temporal = TemporalConfig(**data["temporal"])
                    if "app" in data and "data_dir" in data["app"]:
                        config.data_dir = Path(data["app"]["data_dir"]).expanduser()
        
        # Ensure data directory exists
        config.data_dir.mkdir(parents=True, exist_ok=True)
        
        return config
```

## 2. voice_time/database/models.py

```python
"""SQLAlchemy models for the voice time system."""
import uuid
from datetime import datetime, date, time
from typing import Optional, List
from sqlalchemy import (
    create_engine, Column, String, Boolean, Integer, Float, 
    DateTime, Date, Time, ForeignKey, Text, Index
)
from sqlalchemy.orm import declarative_base, relationship, Session
from sqlalchemy.sql import func

Base = declarative_base()


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Matter(Base):
    __tablename__ = "matters"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    matter_ref = Column(String)  # Billing system reference
    display_name = Column(String, nullable=False)
    client = Column(String)
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime)
    use_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())
    
    aliases = relationship("MatterAlias", back_populates="matter", cascade="all, delete-orphan")
    planned_tasks = relationship("PlannedTask", back_populates="matter")
    work_logs = relationship("WorkLog", back_populates="matter")
    
    def touch(self):
        """Update last_used_at and increment use_count."""
        self.last_used_at = datetime.now()
        self.use_count += 1


class MatterAlias(Base):
    __tablename__ = "matter_aliases"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    matter_id = Column(String, ForeignKey("matters.id"), nullable=False)
    alias = Column(String, nullable=False)
    is_primary = Column(Boolean, default=False)
    
    matter = relationship("Matter", back_populates="aliases")


class ActivityType(Base):
    __tablename__ = "activity_types"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    code = Column(String, unique=True, nullable=False)
    label = Column(String, nullable=False)
    is_billable = Column(Boolean, default=True)
    display_order = Column(Integer)
    
    vocabulary = relationship("ActivityVocabulary", back_populates="activity_type")


class ActivityVocabulary(Base):
    __tablename__ = "activity_vocabulary"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    activity_type_id = Column(String, ForeignKey("activity_types.id"), nullable=False)
    phrase = Column(String, nullable=False)
    weight = Column(Float, default=1.0)
    
    activity_type = relationship("ActivityType", back_populates="vocabulary")


class DayPlan(Base):
    __tablename__ = "day_plans"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    date = Column(Date, nullable=False, unique=True)
    created_at = Column(DateTime, default=func.now())
    source = Column(String, default="voice")
    
    tasks = relationship("PlannedTask", back_populates="day_plan", cascade="all, delete-orphan")


class PlannedTask(Base):
    __tablename__ = "planned_tasks"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    day_plan_id = Column(String, ForeignKey("day_plans.id"), nullable=False)
    matter_id = Column(String, ForeignKey("matters.id"))  # NULL for general admin
    activity_type_id = Column(String, ForeignKey("activity_types.id"))
    title = Column(String, nullable=False)
    scheduled_time = Column(Time)
    estimated_hours = Column(Float)
    status = Column(String, default="planned")  # planned, in_progress, done, deferred
    sort_order = Column(Integer)
    created_at = Column(DateTime, default=func.now())
    
    day_plan = relationship("DayPlan", back_populates="tasks")
    matter = relationship("Matter", back_populates="planned_tasks")
    activity_type = relationship("ActivityType")
    work_logs = relationship("WorkLog", back_populates="planned_task")


class VoiceEvent(Base):
    __tablename__ = "voice_events"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    timestamp = Column(DateTime, default=func.now())
    transcript = Column(Text, nullable=False)
    audio_path = Column(String)
    intent = Column(String)
    confidence = Column(Float)
    processed = Column(Boolean, default=False)


class WorkLog(Base):
    __tablename__ = "work_logs"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    matter_id = Column(String, ForeignKey("matters.id"))
    activity_type_id = Column(String, ForeignKey("activity_types.id"))
    planned_task_id = Column(String, ForeignKey("planned_tasks.id"))
    started_at = Column(DateTime)
    ended_at = Column(DateTime)
    duration_hours = Column(Float, nullable=False)
    narrative = Column(Text)
    source_event_id = Column(String, ForeignKey("voice_events.id"))
    allocation_status = Column(String, default="allocated")  # allocated, needs_review
    is_exported = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    
    matter = relationship("Matter", back_populates="work_logs")
    activity_type = relationship("ActivityType")
    planned_task = relationship("PlannedTask", back_populates="work_logs")
    voice_event = relationship("VoiceEvent")


class SessionState(Base):
    __tablename__ = "session_state"
    
    key = Column(String, primary_key=True)
    value = Column(Text)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


# Indexes
Index("idx_matters_active", Matter.is_active)
Index("idx_matters_last_used", Matter.last_used_at.desc())
Index("idx_work_logs_date", WorkLog.started_at)
Index("idx_planned_tasks_date", PlannedTask.day_plan_id)
Index("idx_voice_events_timestamp", VoiceEvent.timestamp)
```

## 3. voice_time/database/schema.py

```python
"""Database setup and seed data."""
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from .models import Base, ActivityType, ActivityVocabulary


def init_db(db_path: Path) -> Session:
    """Initialize database and return session."""
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    # Seed activity types if empty
    if session.query(ActivityType).count() == 0:
        seed_activity_types(session)
    
    return session


def seed_activity_types(session: Session):
    """Seed default activity types and vocabulary."""
    
    activities = [
        {
            "code": "DOCREV",
            "label": "Document Review",
            "is_billable": True,
            "display_order": 1,
            "vocabulary": [
                "reviewing", "reading", "going through", "analysing", "analysis",
                "disclosure", "bundle", "documents", "exhibits", "evidence",
                "witness statement", "pleading", "perusing", "considering"
            ]
        },
        {
            "code": "DRAFT",
            "label": "Drafting",
            "is_billable": True,
            "display_order": 2,
            "vocabulary": [
                "drafting", "writing", "preparing", "amending", "revising",
                "skeleton", "statement", "letter", "application", "particulars",
                "defence", "reply", "submissions", "redrafting"
            ]
        },
        {
            "code": "RESEARCH",
            "label": "Legal Research",
            "is_billable": True,
            "display_order": 3,
            "vocabulary": [
                "researching", "looking into", "checking", "authorities",
                "case law", "legislation", "limitation", "law on", "investigating"
            ]
        },
        {
            "code": "CALL",
            "label": "Telephone",
            "is_billable": True,
            "display_order": 4,
            "vocabulary": [
                "call", "phone", "telephone", "spoke to", "speaking with",
                "rang", "called"
            ]
        },
        {
            "code": "CONF",
            "label": "Meeting/Conference",
            "is_billable": True,
            "display_order": 5,
            "vocabulary": [
                "meeting", "conference", "attendance", "with counsel",
                "con", "chambers", "teams", "zoom", "video call"
            ]
        },
        {
            "code": "EMAIL",
            "label": "Correspondence",
            "is_billable": True,
            "display_order": 6,
            "vocabulary": [
                "email", "emailing", "correspondence", "letter",
                "responding to", "reply to", "chasing", "writing to"
            ]
        },
        {
            "code": "COURT",
            "label": "Court/Hearing",
            "is_billable": True,
            "display_order": 7,
            "vocabulary": [
                "court", "hearing", "trial", "CMC", "PTR", "application",
                "before the judge", "master", "tribunal"
            ]
        },
        {
            "code": "TRAVEL",
            "label": "Travel",
            "is_billable": True,
            "display_order": 8,
            "vocabulary": [
                "travelling", "travel", "train", "heading to", "journey",
                "commuting"
            ]
        },
        {
            "code": "ADMIN",
            "label": "Administration",
            "is_billable": False,
            "display_order": 9,
            "vocabulary": [
                "admin", "internal", "billing", "file review", "housekeeping",
                "filing", "organising"
            ]
        },
    ]
    
    for activity_data in activities:
        vocab_phrases = activity_data.pop("vocabulary")
        activity = ActivityType(**activity_data)
        session.add(activity)
        session.flush()  # Get the ID
        
        for phrase in vocab_phrases:
            vocab = ActivityVocabulary(
                activity_type_id=activity.id,
                phrase=phrase
            )
            session.add(vocab)
    
    session.commit()
```

## Continue with the remaining files...

The core intelligence files (matcher.py, temporal.py, intent.py, state_machine.py) are the heart of the system. Build these carefully following the ARCHITECTURE.md specifications.

The LLM prompts in llm/prompts.py should exactly match what's documented.

The web UI can be minimal - Flask with HTMX for dynamic updates without JavaScript complexity.

## Key Implementation Notes

1. **Start with CLI**: Before building the web UI, get the core loop working in a simple REPL. This lets you iterate on the intelligence without UI friction.

2. **Test with real scenarios**: Use the test scenarios from PLAN.md. If those work, the system works.

3. **Prompt iteration**: The LLM prompts will need tuning. Start with the documented versions but expect to adjust based on actual outputs.

4. **Confidence thresholds**: Start conservative (higher thresholds = more clarification questions). You can lower them once you trust the matching.

5. **Voice can wait**: Get everything working with typed input first. Voice is just a different input method for the same logic.

---

**Run these commands to initialise:**

```bash
mkdir voice_time
cd voice_time
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install sqlalchemy pydantic pyyaml ollama httpx rapidfuzz python-dateutil rich flask

# Start Ollama in another terminal
ollama serve
ollama pull qwen2.5:1.5b-instruct
```

Then begin building file by file, testing as you go.
