# Weekend Development Checklist

## Pre-Weekend Setup (Do This First)

```bash
# 1. Create project directory
mkdir voice_time && cd voice_time

# 2. Set up Python environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install core dependencies
pip install sqlalchemy pydantic pyyaml ollama httpx rapidfuzz python-dateutil rich flask faster-whisper sounddevice numpy

# 4. Start Ollama (separate terminal)
ollama serve

# 5. Pull the model
ollama pull qwen2.5:7b-instruct

# 6. Test Ollama is working
curl http://localhost:11434/api/tags
```

---

## Friday Evening (2-3 hours)

### Hour 1: Project Structure
- [ ] Create folder structure from cursor_prompt.md
- [ ] Create config.py
- [ ] Create database/models.py
- [ ] Create database/schema.py

### Hour 2: Database & Seed Data
- [ ] Test database initialisation
- [ ] Add seed activity types with vocabulary
- [ ] Create sample matters for testing:
  - "Smith v Jones" (aliases: Smith, SvJ, Smith disclosure)
  - "Brown v Welsh" (aliases: Brown, BvW, Brown skeleton)
  - "Acme Corp" (aliases: Acme, corporate)

### Hour 3: Basic CLI
- [ ] Create simple REPL that:
  - Accepts text input
  - Stores in voice_events table
  - Prints acknowledgment
- [ ] Test: type "hello", see it stored

**Friday Exit Criteria:** Database works, can store/retrieve matters and voice events

---

## Saturday Morning (3-4 hours)

### Focus: Morning Planning Parser

- [ ] Create llm/client.py (Ollama wrapper)
- [ ] Create llm/prompts.py with MORNING_PLAN_PROMPT
- [ ] Create llm/parser.py:
  - Takes transcript string
  - Calls Ollama
  - Returns structured tasks
- [ ] Create core/matcher.py:
  - `find_matter(query, matters)` with recency weighting
  - `find_activity_type(utterance)` from vocabulary

### Test Cases
```
Input: "Today I need to finish Smith disclosure, draft the Brown skeleton"
Expected: 2 PlannedTasks created, correct matters linked

Input: "Working on Smith this morning, call at 3 with counsel on Brown"
Expected: 2 tasks, one with scheduled_time

Input: "Just emails and admin today"  
Expected: 1-2 tasks, no matter (general admin)
```

**Saturday Morning Exit Criteria:** Can speak/type a morning plan, see correctly parsed tasks

---

## Saturday Afternoon (3-4 hours)

### Focus: During-Day Fast Path

- [ ] Create core/intent.py:
  - Intent enum (COMPLETE, START, SWITCH, STATUS, LOG_HISTORICAL, ADD_TASK)
  - `classify_intent(utterance)` using heuristics + keywords

- [ ] Create core/temporal.py:
  - `parse_duration(utterance)` - explicit and natural language
  - `infer_duration(utterance, last_entry_time, now, modifier)`

- [ ] Create core/state_machine.py:
  - State class with: active_matter, active_task, current_work_block, task_stack
  - `process_utterance(text)` → routes to appropriate handler
  - Work block start/stop logic

- [ ] Create core/stack.py:
  - Simple list-based stack for interrupted tasks
  - push(), pop(), peek()

### Test Cases
```
[After morning plan for Smith disclosure]

Input: "Done with the disclosure"
Expected: WorkLog created, Smith, DOCREV, duration inferred from elapsed

Input: "Quick call about Brown"
Expected: Smith pushed to stack, Brown CALL started

Input: "Back to what I was doing"
Expected: Brown CALL closed, Smith popped from stack

Input: "Spent a couple of hours on research for Acme"
Expected: Acme RESEARCH, 2.0 hours (historical log, no timer)
```

**Saturday Exit Criteria:** Full conversational loop works - plan → log → switch → complete

---

## Sunday Morning (3-4 hours)

### Focus: Voice & End-of-Day

- [ ] Create voice/transcribe.py:
  - Load faster-whisper model
  - `transcribe(audio_array)` → text

- [ ] Create voice/capture.py:
  - Push-to-talk recording (spacebar or button)
  - Returns audio array

- [ ] Create llm/narrative.py:
  - Takes WorkLog + context
  - Returns professional narrative
  
- [ ] Create end-of-day reconciliation:
  - Sum hours by matter
  - Identify unallocated time
  - List incomplete tasks
  - Offer roll-forward to tomorrow

### Test Cases
```
[After a day of logging]

Input: "What's left?"
Expected: List of incomplete planned tasks

Input: "Review the day"
Expected: 
  - Smith v Jones: 3.5 hrs (DOCREV 3.0, EMAIL 0.5)
  - Brown v Welsh: 2.5 hrs (DRAFT 2.0, CONF 0.5)
  - Unallocated: 0.5 hrs
  
Input: "Put the unallocated on Smith admin"
Expected: Allocated, totals updated
```

**Sunday Morning Exit Criteria:** Voice input works, end-of-day review works

---

## Sunday Afternoon (3-4 hours)

### Focus: Web UI & Export

- [ ] Create web/app.py (Flask setup)
- [ ] Create web/routes.py:
  - GET / → dashboard
  - POST /voice → process voice/text input
  - GET /plan → today's plan
  - GET /review → end-of-day view
  - POST /export → generate CSV

- [ ] Create templates:
  - base.html (layout)
  - index.html (main dashboard with input)
  - plan.html (morning planning view)
  - review.html (end-of-day review)

- [ ] Create export/csv_export.py:
  - Export today's WorkLogs to CSV
  - Format: Date, Matter Ref, Matter Name, Activity, Hours, Narrative

### UI Requirements
- Single-page feel (HTMX for updates)
- Big text input / push-to-talk button
- Today's plan checklist
- Running total by matter
- Clear visual for "needs review" items

**Sunday Exit Criteria:** Complete working system with web UI

---

## Testing Script

Create `test_full_day.py`:

```python
"""Simulate a full day to test the system."""

MORNING_PLAN = """
Today I need to finish the Smith disclosure review, 
draft the Brown skeleton argument, 
and I've got a call with counsel at 3 about Brown.
Also need to chase the Smith expert.
"""

DAY_EVENTS = [
    ("09:15", "Starting on Smith disclosure"),
    ("10:30", "Done with disclosure, took all morning"),
    ("10:35", "Quick email to expert for Smith"),
    ("10:40", "Starting on Brown skeleton"),
    ("12:30", "Taking lunch"),
    ("13:30", "Back to the skeleton"),
    ("14:45", "Quick call - expert got back to me about Smith"),
    ("14:55", "Back to drafting"),
    ("15:00", "Call with counsel starting"),
    ("15:45", "Call's done, ran over a bit"),
    ("15:50", "Back to skeleton, final amendments"),
    ("16:30", "Skeleton's done"),
    ("16:35", "Various emails, mostly Smith"),
    ("17:00", "What's left?"),
    ("17:05", "Move expert chase to tomorrow"),
    ("17:10", "Review the day"),
]

# Run through events, verify state after each
```

---

## Success Criteria

By Sunday evening, you should be able to:

1. ✅ Speak/type a morning plan, see it parsed into tasks
2. ✅ Log time with natural speech ("done with that", "couple of hours on Smith")
3. ✅ Handle interruptions ("quick call", "back to what I was doing")
4. ✅ Get end-of-day summary with totals by matter
5. ✅ Export to CSV for your billing system
6. ✅ All runs locally, no cloud dependencies

---

## What's NOT in Weekend Scope

- Calendar integration
- Desktop app (Tauri)
- Wake word detection  
- Practice management connectors
- Multiple users
- Sync across devices

These are Phase 2+ items documented in ARCHITECTURE.md.
