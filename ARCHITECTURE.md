# Voice Time Recording System - Architecture

## Design Philosophy

The system is a **stateful day controller** where:
- The **state machine** is the runtime brain (deterministic, fast)
- The **LLM** is a parser and synthesiser (used sparingly, for complex tasks)
- **Voice** is the primary input, but the system works without it

### Model Choice: Qwen2.5-7B-Instruct

We use a small (7B parameter) model because:
- **Fast**: ~200-400ms inference on CPU, sub-100ms with GPU
- **Excellent JSON output**: Specifically optimised for structured data
- **Good enough**: For intent classification, matter matching, and narrative generation
- **Low resource**: ~4GB RAM, runs on any modern laptop

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
│  │  1. Intent Classification (heuristics)                   │   │
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
