# Voice Time Recording System - Development Plan

## Vision

A voice-first time recording system that understands how lawyers actually work. You describe your day in the morning, log time with natural speech throughout the day, and review/export at end of day. The system infers what it can and asks only when genuinely uncertain.

## MVP Scope

### In Scope
- ✅ Morning planning via voice/text
- ✅ Matter management with aliases
- ✅ During-day logging with context awareness
- ✅ Natural duration language ("couple of hours")
- ✅ Task stack for interruptions
- ✅ End-of-day review
- ✅ Narrative generation
- ✅ CSV export
- ✅ Simple web UI

### Out of Scope (Future)
- [ ] Calendar integration
- [ ] Desktop app (Tauri)
- [ ] Wake word detection
- [ ] Practice management system connectors
- [ ] Multi-device sync
- [ ] Team features

## Implementation Status

### ✅ Phase 1: Foundation
- [x] Project setup (virtualenv, requirements)
- [x] SQLite database schema
- [x] SQLAlchemy models
- [x] Basic matter CRUD
- [x] Activity type seed data
- [x] Configuration management

### ✅ Phase 2: Core Intelligence
- [x] Ollama client wrapper
- [x] Morning planning prompt
- [x] Plan parser (LLM-based)
- [x] Matter alias matching with recency weighting
- [x] PlannedTask creation
- [x] Intent classifier (heuristic)
- [x] Activity type inference from vocabulary
- [x] Temporal inference (duration language)
- [x] State machine (current task, active matter)
- [x] Task stack for interruptions
- [x] Work block creation/closure

### ✅ Phase 3: Voice & Polish
- [x] faster-whisper integration
- [x] Audio capture (push-to-talk)
- [x] End-of-day reconciliation logic
- [x] Narrative generation prompt
- [x] Flask web UI
- [x] Dashboard (today's plan, logged time)
- [x] Review interface
- [x] CSV export

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

## Next Steps

1. **Testing**: Run through all test scenarios
2. **Bug Fixes**: Address any issues found
3. **Documentation**: Complete user guide
4. **Demo**: Prepare demo for real-world testing
5. **Feedback**: Collect user feedback

## Future Enhancements (Post-MVP)

### Phase 4: Calendar Integration
- EventKit (macOS) or Microsoft Graph API
- Auto-import meetings as planned tasks
- Auto-pause when calendar events start

### Phase 5: Desktop App
- Tauri-based native app
- System tray icon
- Global hotkey (Cmd+Shift+T)
- Native notifications

### Phase 6: Advanced Features
- Wake word detection
- Voice feedback
- Multi-day planning
- Task rollover
- Analytics dashboard
- Practice management integration

### Phase 7: Team Features
- Multi-user support
- Matter sharing
- Team billing
- Admin dashboard
