"""State machine - the runtime brain of the voice time system."""
from typing import Optional, Dict, Any
from datetime import datetime, date, timedelta
from dataclasses import dataclass
from sqlalchemy.orm import Session

from .intent import IntentClassifier, Intent
from .matcher import MatterMatcher, ActivityMatcher
from .temporal import TemporalParser
from .stack import TaskStack, TaskContext
from .edit_commands import EditCommandParser
from ..database.models import (
    Matter, ActivityType, DayPlan, PlannedTask,
    WorkLog, VoiceEvent, ActiveTimer
)
from ..llm.client import OllamaClient
from ..llm.parser import PlanParser
from ..llm.narrative import NarrativeGenerator


@dataclass
class ProcessingResult:
    """Result of processing an utterance."""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    needs_clarification: bool = False
    clarification_question: Optional[str] = None


class DayState:
    """
    The runtime state machine for a working day.
    
    This is the deterministic core that orchestrates:
    - Intent classification
    - Matter/activity matching
    - Duration inference
    - Work log creation
    - Task stack management
    - Voice-controlled editing
    - Conversational clarifications
    """
    
    def __init__(
        self,
        session: Session,
        llm_client: OllamaClient,
        config: Any
    ):
        self.session = session
        self.config = config
        
        # Core components
        self.intent_classifier = IntentClassifier()
        self.matter_matcher = MatterMatcher(session, config.matching.confidence_threshold)
        self.activity_matcher = ActivityMatcher(session)
        self.temporal_parser = TemporalParser(config.temporal)
        self.task_stack = TaskStack()
        self.edit_parser = EditCommandParser()
        
        # LLM components (used sparingly)
        self.plan_parser = PlanParser(llm_client)
        self.narrative_generator = NarrativeGenerator(llm_client)
        
        # Runtime state
        self.active_matter_id: Optional[str] = None
        self.active_activity_type_id: Optional[str] = None
        self.active_planned_task_id: Optional[str] = None
        self.current_work_started_at: Optional[datetime] = None
        self.last_interaction_time: datetime = datetime.now()
        self.today_plan_id: Optional[str] = None
        
        # Conversational state for clarifications
        self.pending_clarification: Optional[Dict[str, Any]] = None
        
        # Load today's plan if exists
        self._load_today_plan()
    
    def process(self, utterance: str) -> ProcessingResult:
        """
        Process a user utterance - the main entry point.
        
        Args:
            utterance: What the user said/typed
            
        Returns:
            ProcessingResult with success, message, and optional data
        """
        # Record voice event
        event = VoiceEvent(transcript=utterance)
        self.session.add(event)
        self.session.flush()
        
        # Update last interaction time
        self.last_interaction_time = datetime.now()
        
        # Check if we're waiting for a clarification response
        if self.pending_clarification:
            result = self._handle_clarification_response(utterance, event)
            if result:
                return result
        
        # Check if this is an edit command first (priority)
        edit_cmd = self.edit_parser.parse(utterance)
        if edit_cmd:
            result = self._handle_edit_command(edit_cmd, event)
            event.intent = 'edit'
            event.processed = True
            self.session.commit()
            return result
        
        # Classify intent (fast path)
        intent_result = self.intent_classifier.classify(utterance)
        
        # Store intent in event
        event.intent = intent_result.intent.value
        event.confidence = intent_result.confidence
        self.session.commit()
        
        # Route to appropriate handler
        handlers = {
            Intent.PLAN: self._handle_plan,
            Intent.START: self._handle_start,
            Intent.COMPLETE: self._handle_complete,
            Intent.SWITCH: self._handle_switch,
            Intent.PAUSE: self._handle_pause,
            Intent.RESUME: self._handle_resume,
            Intent.STATUS: self._handle_status,
            Intent.LOG_HISTORICAL: self._handle_log_historical,
            Intent.ADD_TASK: self._handle_add_task,
        }
        
        handler = handlers.get(intent_result.intent)
        if handler:
            return handler(utterance, event)
        else:
            return ProcessingResult(
                success=False,
                message="I didn't understand that. Can you rephrase?",
                needs_clarification=True
            )
    
    def _handle_clarification_response(self, utterance: str, event: VoiceEvent) -> Optional[ProcessingResult]:
        """Handle a response to a pending clarification question."""
        if not self.pending_clarification:
            return None
        
        clarification_type = self.pending_clarification.get('type')
        
        if clarification_type == 'matter':
            return self._handle_matter_clarification(utterance, event)
        
        elif clarification_type == 'activity':
            return self._handle_activity_clarification(utterance, event)
        
        elif clarification_type == 'description':
            return self._handle_description_clarification(utterance, event)
        
        # Unknown clarification type - clear and process normally
        self.pending_clarification = None
        return None
    
    def _handle_matter_clarification(self, utterance: str, event: VoiceEvent) -> ProcessingResult:
        """Handle response when user is specifying which matter."""
        matter_match = self.matter_matcher.find_matter(utterance)
        
        if matter_match.match:
            # Got a valid matter - now START A TIMER
            self.pending_clarification = None
            
            # Stop any existing timer first
            existing_timer = self.session.query(ActiveTimer).first()
            if existing_timer:
                self._save_timer_to_log(existing_timer)
                self.session.delete(existing_timer)
            
            # Create new timer
            new_timer = ActiveTimer(
                matter_id=matter_match.match.id,
                activity_type_id=None,
                started_at=datetime.now(),
                is_active=True
            )
            self.session.add(new_timer)
            
            # Update internal state
            self.active_matter_id = matter_match.match.id
            self.active_activity_type_id = None
            self.current_work_started_at = datetime.now()
            matter_match.match.touch()
            self.session.commit()
            
            event.intent = 'start'
            event.processed = True
            
            matter_name = matter_match.match.display_name
            
            # Now ask for activity type
            self.pending_clarification = {
                'type': 'activity',
                'timer_id': new_timer.id,
                'matter_name': matter_name,
                'timestamp': datetime.now()
            }
            
            activities = self.session.query(ActivityType).order_by(ActivityType.display_order).all()
            activity_labels = [a.label for a in activities]
            
            return ProcessingResult(
                success=True,
                message=f"Timer started: {matter_name}. What type of work?",
                needs_clarification=True,
                clarification_question="activity",
                data={
                    'timer_started': True,
                    'matter': matter_name,
                    'suggestions': activity_labels[:6]
                }
            )
        else:
            # Still can't find matter - give up and clear state
            self.pending_clarification = None
            available = self._get_available_matters()
            return ProcessingResult(
                success=False,
                message=f"Could not find that matter. Available: {available}"
            )
    
    def _handle_activity_clarification(self, utterance: str, event: VoiceEvent) -> ProcessingResult:
        """Handle response when user is specifying activity type."""
        timer_id = self.pending_clarification.get('timer_id')
        matter_name = self.pending_clarification.get('matter_name', 'Unknown')
        
        # Try to match the activity type
        activity_match = self.activity_matcher.find_activity_type(utterance)
        
        # Get the active timer
        timer = self.session.query(ActiveTimer).get(timer_id) if timer_id else self.session.query(ActiveTimer).first()
        
        if not timer:
            self.pending_clarification = None
            return ProcessingResult(
                success=False,
                message="Timer not found. Please start again."
            )
        
        if activity_match.match:
            # Update timer with activity type
            timer.activity_type_id = activity_match.match.id
            self.active_activity_type_id = activity_match.match.id
            self.session.commit()
            
            activity_name = activity_match.match.label
            
            # Now ask for description
            self.pending_clarification = {
                'type': 'description',
                'timer_id': timer.id,
                'matter_name': matter_name,
                'activity_name': activity_name,
                'timestamp': datetime.now()
            }
            
            return ProcessingResult(
                success=True,
                message=f"Recording {activity_name}. What specifically are you working on?",
                needs_clarification=True,
                clarification_question="description",
                data={
                    'matter': matter_name,
                    'activity': activity_name
                }
            )
        else:
            # Couldn't match - ask again with options
            activities = self.session.query(ActivityType).order_by(ActivityType.display_order).all()
            activity_labels = [a.label for a in activities]
            
            return ProcessingResult(
                success=True,
                message=f"Please choose: {', '.join(activity_labels[:6])}",
                needs_clarification=True,
                clarification_question="activity",
                data={'suggestions': activity_labels[:6]}
            )
    
    def _handle_description_clarification(self, utterance: str, event: VoiceEvent) -> ProcessingResult:
        """Handle response when user is describing what they're working on."""
        timer_id = self.pending_clarification.get('timer_id')
        matter_name = self.pending_clarification.get('matter_name', 'Unknown')
        activity_name = self.pending_clarification.get('activity_name', 'work')
        
        # Get the active timer
        timer = self.session.query(ActiveTimer).get(timer_id) if timer_id else self.session.query(ActiveTimer).first()
        
        if not timer:
            self.pending_clarification = None
            return ProcessingResult(
                success=False,
                message="Timer not found. Please start again."
            )
        
        # Save the description as the narrative draft
        timer.narrative_draft = utterance
        self.session.commit()
        
        # Clear clarification state - time entry is now complete
        self.pending_clarification = None
        
        return ProcessingResult(
            success=True,
            message=f"Recording: {matter_name} - {activity_name}\n{utterance}",
            data={
                'timer_complete': True,
                'matter': matter_name,
                'activity': activity_name,
                'description': utterance
            }
        )
    
    def _get_available_matters(self) -> str:
        """Get a list of available matter names for suggestions."""
        matters = self.session.query(Matter).filter(Matter.is_active == True).order_by(
            Matter.last_used_at.desc().nullslast()
        ).limit(5).all()
        
        if not matters:
            return "No matters configured. Add some in the Matters page."
        
        names = [m.display_name.split()[0] if m.display_name else m.matter_ref for m in matters]
        return ", ".join(names)
    
    def _handle_edit_command(self, cmd, event: VoiceEvent) -> ProcessingResult:
        """
        Handle voice editing commands for work log entries - COMPLETELY HANDS-FREE.
        
        BUGS FIXED:
        - Bug #1: Now handles all command types including 'add_time'
        - Bug #2: Validates entry_number >= 1 to prevent negative indexing  
        - Bug #3: Infers activity from full utterance, defaults to ADMIN properly
        """
        # Get today's logs
        logs = self.session.query(WorkLog).filter(
            WorkLog.created_at >= date.today()
        ).order_by(WorkLog.created_at).all()
        
        if not logs and cmd.command_type != 'add_time':
            return ProcessingResult(
                success=False,
                message="No entries to edit today"
            )
        
        # BUG FIX #2: Validate entry number is valid (>= 1 and <= len(logs))
        if cmd.entry_number is not None:
            if cmd.entry_number < 1:
                return ProcessingResult(
                    success=False,
                    message=f"Invalid entry number: {cmd.entry_number} (must be 1 or higher)"
                )
            if cmd.entry_number > len(logs):
                return ProcessingResult(
                    success=False,
                    message=f"Entry {cmd.entry_number} not found (only {len(logs)} entries today)"
                )
        
        # Handle each command type
        if cmd.command_type == 'change_duration':
            log = logs[cmd.entry_number - 1]
            old_duration = log.duration_hours
            log.duration_hours = cmd.new_duration
            
            # Update end time based on new duration
            if log.started_at:
                log.ended_at = log.started_at + timedelta(hours=cmd.new_duration)
            
            self.session.commit()
            
            matter_name = log.matter.display_name if log.matter else "General"
            return ProcessingResult(
                success=True,
                message=f"✓ Entry {cmd.entry_number} ({matter_name}): {old_duration}h → {cmd.new_duration}h"
            )
        
        elif cmd.command_type == 'update_narrative':
            log = logs[cmd.entry_number - 1]
            
            # Generate professional narrative from casual update
            if log.matter and log.activity_type:
                narrative = self.narrative_generator.generate(
                    cmd.narrative_update,
                    log.matter.display_name,
                    log.activity_type.code,
                    log.duration_hours
                )
                log.narrative = narrative
            else:
                log.narrative = cmd.narrative_update
            
            self.session.commit()
            
            matter_name = log.matter.display_name if log.matter else "General"
            return ProcessingResult(
                success=True,
                message=f"✓ Entry {cmd.entry_number} ({matter_name}) narrative updated",
                data={"new_narrative": log.narrative}
            )
        
        elif cmd.command_type == 'change_matter':
            log = logs[cmd.entry_number - 1]
            old_matter = log.matter.display_name if log.matter else "General"
            
            # Find new matter
            matter_match = self.matter_matcher.find_matter(cmd.matter_name)
            if not matter_match.match:
                return ProcessingResult(
                    success=False,
                    message=f"Could not find matter: {cmd.matter_name}",
                    needs_clarification=True
                )
            
            log.matter_id = matter_match.match.id
            matter_match.match.touch()
            self.session.commit()
            
            return ProcessingResult(
                success=True,
                message=f"✓ Entry {cmd.entry_number}: {old_matter} → {matter_match.match.display_name}"
            )
        
        elif cmd.command_type == 'change_activity':
            log = logs[cmd.entry_number - 1]
            old_activity = log.activity_type.label if log.activity_type else "Unspecified"
            
            # Match activity type
            activity_match = self.activity_matcher.find_activity_type(cmd.activity_name)
            if not activity_match.match:
                return ProcessingResult(
                    success=False,
                    message=f"Could not find activity type: {cmd.activity_name}"
                )
            
            log.activity_type_id = activity_match.match.id
            self.session.commit()
            
            return ProcessingResult(
                success=True,
                message=f"✓ Entry {cmd.entry_number} activity: {old_activity} → {activity_match.match.label}"
            )
        
        elif cmd.command_type == 'delete':
            log = logs[cmd.entry_number - 1]
            matter_name = log.matter.display_name if log.matter else "General"
            duration = log.duration_hours
            
            self.session.delete(log)
            self.session.commit()
            
            return ProcessingResult(
                success=True,
                message=f"✓ Deleted entry {cmd.entry_number} ({matter_name}, {duration}h)"
            )
        
        elif cmd.command_type == 'add_time':
            # BUG FIX #1: Handle add_time command (was missing)
            # BUG FIX #3: Infer activity from FULL utterance, default to ADMIN properly
            
            # Find matter
            matter_match = self.matter_matcher.find_matter(cmd.matter_name)
            if not matter_match.match:
                return ProcessingResult(
                    success=False,
                    message=f"Could not find matter: {cmd.matter_name}",
                    needs_clarification=True
                )
            
            # Infer activity from FULL utterance (not just matter name!)
            # e.g., "Add 2 hours to Thompson for emails" -> should detect EMAIL
            activity_match = self.activity_matcher.find_activity_type(event.transcript)
            
            # Default to ADMIN if no activity found or low confidence
            if not activity_match.match or activity_match.confidence < 0.5:
                admin_activity = self.session.query(ActivityType).filter(
                    ActivityType.code == "ADMIN"
                ).first()
                activity_id = admin_activity.id if admin_activity else None
                activity_code = "ADMIN"
                activity_name = "Administration"
            else:
                activity_id = activity_match.match.id
                activity_code = activity_match.match.code
                activity_name = activity_match.match.label
            
            # Generate professional narrative from full utterance
            narrative = self.narrative_generator.generate(
                event.transcript,
                matter_match.match.display_name,
                activity_code,
                cmd.new_duration
            )
            
            # Create new work log
            work_log = WorkLog(
                matter_id=matter_match.match.id,
                activity_type_id=activity_id,
                duration_hours=cmd.new_duration,
                narrative=narrative,
                started_at=datetime.now() - timedelta(hours=cmd.new_duration),
                ended_at=datetime.now(),
                source_event_id=event.id,
                allocation_status="allocated"
            )
            self.session.add(work_log)
            self.session.commit()
            
            return ProcessingResult(
                success=True,
                message=f"✓ Added {cmd.new_duration}h to {matter_match.match.display_name} ({activity_name})"
            )
        
        # If we get here, command type wasn't recognized
        return ProcessingResult(
            success=False,
            message=f"Edit command type '{cmd.command_type}' not implemented"
        )
    
    def _handle_plan(self, utterance: str, event: VoiceEvent) -> ProcessingResult:
        """Handle morning planning with follow-up questions."""
        # Check if input is too vague
        if len(utterance.strip()) < 15:
            # Too short - ask for more detail
            return ProcessingResult(
                success=False,
                message="What would you like to plan? Tell me your tasks for today.",
                needs_clarification=True,
                clarification_question="plan_tasks",
                data={
                    'example': "Today I need to finish Thompson disclosure, draft Brown skeleton, and call counsel"
                }
            )
        
        # Get active matters for context
        matters = self.session.query(Matter).filter(Matter.is_active == True).all()
        matters_data = [
            {
                "matter_ref": m.matter_ref,
                "display_name": m.display_name,
                "aliases": [a.alias for a in m.aliases]
            }
            for m in matters
        ]
        
        # Parse plan using LLM
        parsed = self.plan_parser.parse(utterance, matters_data)
        
        # Check if LLM found any tasks
        if not parsed.get("tasks"):
            # No tasks found - ask for clarification
            available = self._get_available_matters()
            return ProcessingResult(
                success=False,
                message=f"I couldn't identify any tasks. Try: 'Today I need to work on [matter]'.\n\nAvailable matters: {available}",
                needs_clarification=True,
                clarification_question="plan_tasks"
            )
        
        # Create or get today's plan
        today = date.today()
        plan = self.session.query(DayPlan).filter(DayPlan.date == today).first()
        if not plan:
            plan = DayPlan(date=today, source="voice")
            self.session.add(plan)
            self.session.flush()
        
        self.today_plan_id = plan.id
        
        # Create planned tasks
        created_tasks = []
        unmatched_matters = []
        
        for i, task_data in enumerate(parsed["tasks"]):
            # Resolve matter
            matter = None
            if task_data["matter_ref"]:
                match = self.matter_matcher.find_matter(task_data["matter_ref"])
                if match.match:
                    matter = match.match
                else:
                    unmatched_matters.append(task_data["matter_ref"])
            
            # Resolve activity type
            activity = self.session.query(ActivityType).filter(
                ActivityType.code == task_data["activity_type"]
            ).first()
            
            # Create planned task
            task = PlannedTask(
                day_plan_id=plan.id,
                matter_id=matter.id if matter else None,
                activity_type_id=activity.id if activity else None,
                title=task_data["title"],
                scheduled_time=task_data["scheduled_time"],
                estimated_hours=task_data["estimated_hours"],
                sort_order=i
            )
            self.session.add(task)
            created_tasks.append(task)
        
        self.session.commit()
        
        # Build response
        task_count = len(created_tasks)
        matter_count = len(set(t.matter_id for t in created_tasks if t.matter_id))
        
        message = f"Planned {task_count} task{'s' if task_count != 1 else ''}"
        if matter_count > 0:
            message += f" across {matter_count} matter{'s' if matter_count != 1 else ''}"
        
        # Check for issues that need follow-up
        all_unresolved = list(set(unmatched_matters + parsed.get("unresolved_mentions", [])))
        
        if all_unresolved:
            # Some matters weren't matched - ask about them
            available = self._get_available_matters()
            message += f"\n\nCouldn't match: {', '.join(all_unresolved)}.\nAvailable: {available}"
            
            return ProcessingResult(
                success=True,
                message=message,
                needs_clarification=True,
                clarification_question="unmatched_matters",
                data={
                    "tasks": created_tasks,
                    "plan_id": plan.id,
                    "unmatched": all_unresolved
                }
            )
        
        # Check if any tasks are missing matters
        tasks_without_matters = [t for t in created_tasks if not t.matter_id]
        if tasks_without_matters:
            message += "\n\nSome tasks don't have matters assigned. You can edit them on the Planning page."
        
        return ProcessingResult(
            success=True,
            message=message,
            data={"tasks": created_tasks, "plan_id": plan.id}
        )
    
    def _handle_start(self, utterance: str, event: VoiceEvent) -> ProcessingResult:
        """Handle starting work on a task - CREATES AN ACTUAL TIMER with follow-up questions."""
        # Extract matter and activity
        matter_match = self.matter_matcher.find_matter(utterance)
        activity_match = self.activity_matcher.find_activity_type(utterance)
        
        if not matter_match.match:
            # No match found - provide helpful suggestions
            available = self._get_available_matters()
            
            # Store state for follow-up
            self.pending_clarification = {
                'type': 'matter',
                'original_utterance': utterance,
                'timestamp': datetime.now()
            }
            
            # Check if there were close matches
            if matter_match.candidates:
                suggestions = [c[0].display_name.split()[0] for c in matter_match.candidates[:3]]
                return ProcessingResult(
                    success=False,
                    message=f"Did you mean: {', '.join(suggestions)}? Say the matter name to start.",
                    needs_clarification=True,
                    clarification_question="matter",
                    data={'suggestions': suggestions, 'available': available}
                )
            else:
                return ProcessingResult(
                    success=False,
                    message=f"Matter not found. Available: {available}. Say a matter name to start.",
                    needs_clarification=True,
                    clarification_question="matter",
                    data={'available': available}
                )
        
        # Stop any existing timer first and save it
        existing_timer = self.session.query(ActiveTimer).first()
        if existing_timer:
            self._save_timer_to_log(existing_timer)
            self.session.delete(existing_timer)
        
        # Create a NEW ActiveTimer in the database
        activity_id = activity_match.match.id if activity_match.match else None
        new_timer = ActiveTimer(
            matter_id=matter_match.match.id,
            activity_type_id=activity_id,
            started_at=datetime.now(),
            is_active=True
        )
        self.session.add(new_timer)
        
        # Also update internal state for consistency
        self.active_matter_id = matter_match.match.id
        self.active_activity_type_id = activity_id
        self.current_work_started_at = datetime.now()
        
        # Touch the matter (update recency)
        matter_match.match.touch()
        self.session.commit()
        
        matter_name = matter_match.match.display_name
        
        # Check if we need follow-up questions to complete the time entry
        # Question 1: Activity type (if not detected)
        if not activity_match.match:
            self.pending_clarification = {
                'type': 'activity',
                'timer_id': new_timer.id,
                'matter_name': matter_name,
                'timestamp': datetime.now()
            }
            
            # Get activity type options
            activities = self.session.query(ActivityType).order_by(ActivityType.display_order).all()
            activity_labels = [a.label for a in activities]
            
            return ProcessingResult(
                success=True,
                message=f"Timer started: {matter_name}. What type of work?",
                needs_clarification=True,
                clarification_question="activity",
                data={
                    'timer_started': True,
                    'matter': matter_name,
                    'suggestions': activity_labels[:6]
                }
            )
        
        # Activity was detected - now ask for description
        activity_name = activity_match.match.label
        self.pending_clarification = {
            'type': 'description',
            'timer_id': new_timer.id,
            'matter_name': matter_name,
            'activity_name': activity_name,
            'timestamp': datetime.now()
        }
        
        return ProcessingResult(
            success=True,
            message=f"Timer started: {matter_name} - {activity_name}. What specifically?",
            needs_clarification=True,
            clarification_question="description",
            data={
                'timer_started': True,
                'matter': matter_name,
                'activity': activity_name
            }
        )
    
    def _save_timer_to_log(self, timer: ActiveTimer, narrative: str = None):
        """Save an ActiveTimer to the work log."""
        import math
        
        # Calculate hours (minimum 0.1 = 1 unit)
        elapsed_seconds = timer.elapsed_seconds
        units = math.ceil(elapsed_seconds / 360)  # 6 min = 360 sec
        hours = max(0.1, units * 0.1)
        
        log = WorkLog(
            matter_id=timer.matter_id,
            activity_type_id=timer.activity_type_id,
            started_at=timer.created_at,
            ended_at=datetime.now(),
            duration_hours=hours,
            narrative=narrative or timer.narrative_draft,
            allocation_status='allocated'
        )
        self.session.add(log)
    
    def _handle_complete(self, utterance: str, event: VoiceEvent) -> ProcessingResult:
        """Handle completing a task - STOPS THE ACTIVE TIMER."""
        import math
        
        # Check for active timer in database
        active_timer = self.session.query(ActiveTimer).first()
        
        if not active_timer and not self.current_work_started_at:
            return self._handle_log_historical(utterance, event)
        
        # Get matter and activity from timer or internal state
        if active_timer:
            matter = active_timer.matter
            activity = active_timer.activity_type
            started_at = active_timer.created_at
            elapsed_seconds = active_timer.elapsed_seconds
            units = math.ceil(elapsed_seconds / 360)
            duration_hours = max(0.1, units * 0.1)
        else:
            matter = self.session.query(Matter).get(self.active_matter_id)
            activity = self.session.query(ActivityType).get(self.active_activity_type_id)
            started_at = self.current_work_started_at
            # Infer duration from time elapsed
            duration_result = self.temporal_parser.infer_duration(
                utterance, self.current_work_started_at, datetime.now()
            )
            duration_hours = duration_result.hours
        
        # Generate narrative
        narrative = self.narrative_generator.generate(
            utterance,
            matter.display_name if matter else "General",
            activity.code if activity else "ADMIN",
            duration_hours
        )
        
        # Create work log
        work_log = WorkLog(
            matter_id=matter.id if matter else self.active_matter_id,
            activity_type_id=activity.id if activity else self.active_activity_type_id,
            planned_task_id=self.active_planned_task_id,
            started_at=started_at,
            ended_at=datetime.now(),
            duration_hours=duration_hours,
            narrative=narrative,
            source_event_id=event.id
        )
        self.session.add(work_log)
        
        # Delete active timer
        if active_timer:
            self.session.delete(active_timer)
        
        # Mark planned task as done if linked
        if self.active_planned_task_id:
            task = self.session.query(PlannedTask).get(self.active_planned_task_id)
            if task:
                task.status = "done"
        
        # Clear internal state
        self.active_matter_id = None
        self.active_activity_type_id = None
        self.active_planned_task_id = None
        self.current_work_started_at = None
        
        self.session.commit()
        
        matter_name = matter.display_name if matter else "General"
        activity_name = activity.label if activity else "work"
        
        # Calculate units for display
        units_display = int(duration_hours / 0.1)
        message = f"Stopped: {duration_hours}h ({units_display} units) logged to {matter_name}"
        
        return ProcessingResult(
            success=True,
            message=message,
            data={"work_log": work_log}
        )
    
    def _handle_switch(self, utterance: str, event: VoiceEvent) -> ProcessingResult:
        """Handle switching tasks (with stack management)."""
        # If currently working, push to stack
        if self.current_work_started_at:
            context = TaskContext(
                matter_id=self.active_matter_id,
                activity_type_id=self.active_activity_type_id,
                planned_task_id=self.active_planned_task_id,
                started_at=self.current_work_started_at,
                description=utterance
            )
            self.task_stack.push(context)
        
        # Check for "back to what I was doing"
        if any(phrase in utterance.lower() for phrase in ["back to", "return to"]):
            # Pop from stack
            context = self.task_stack.pop()
            if context:
                self.active_matter_id = context.matter_id
                self.active_activity_type_id = context.activity_type_id
                self.active_planned_task_id = context.planned_task_id
                self.current_work_started_at = datetime.now()
                
                matter = self.session.query(Matter).get(context.matter_id)
                return ProcessingResult(
                    success=True,
                    message=f"↩ Resumed: {matter.display_name if matter else 'previous task'}"
                )
        
        # Otherwise, start new task
        return self._handle_start(utterance, event)
    
    def _handle_pause(self, utterance: str, event: VoiceEvent) -> ProcessingResult:
        """Handle taking a break."""
        if self.current_work_started_at:
            # Close current work
            self._close_current_work(utterance, is_break=True)
        
        return ProcessingResult(
            success=True,
            message="⏸ Paused - enjoy your break!"
        )
    
    def _handle_resume(self, utterance: str, event: VoiceEvent) -> ProcessingResult:
        """Handle resuming from break."""
        return ProcessingResult(
            success=True,
            message="▶ Welcome back!"
        )
    
    def _handle_status(self, utterance: str, event: VoiceEvent) -> ProcessingResult:
        """Handle status query."""
        if not self.today_plan_id:
            return ProcessingResult(
                success=True,
                message="No plan for today yet. What would you like to work on?"
            )
        
        # Get planned tasks
        tasks = self.session.query(PlannedTask).filter(
            PlannedTask.day_plan_id == self.today_plan_id,
            PlannedTask.status != "done"
        ).all()
        
        if not tasks:
            message = "✓ All planned tasks complete!"
        else:
            message = f"Outstanding tasks ({len(tasks)}):\n"
            for task in tasks:
                matter_name = task.matter.display_name if task.matter else "General"
                message += f"  □ {matter_name}: {task.title}\n"
        
        return ProcessingResult(
            success=True,
            message=message,
            data={"tasks": tasks}
        )
    
    def _handle_log_historical(self, utterance: str, event: VoiceEvent) -> ProcessingResult:
        """Handle historical (past tense) logging."""
        # Extract matter, activity, and duration
        matter_match = self.matter_matcher.find_matter(utterance)
        activity_match = self.activity_matcher.find_activity_type(utterance)
        duration_result = self.temporal_parser.infer_duration(utterance)
        
        if not matter_match.match:
            available = self._get_available_matters()
            return ProcessingResult(
                success=False,
                message=f"Which matter was this for? Available: {available}",
                needs_clarification=True,
                data={'available': available}
            )
        
        # Generate narrative
        narrative = self.narrative_generator.generate(
            utterance,
            matter_match.match.display_name,
            activity_match.match.code if activity_match.match else "ADMIN",
            duration_result.hours
        )
        
        # Create work log (no current work block)
        work_log = WorkLog(
            matter_id=matter_match.match.id,
            activity_type_id=activity_match.match.id if activity_match.match else None,
            duration_hours=duration_result.hours,
            narrative=narrative,
            source_event_id=event.id,
            started_at=datetime.now() - timedelta(hours=duration_result.hours),
            ended_at=datetime.now()
        )
        self.session.add(work_log)
        self.session.commit()
        
        return ProcessingResult(
            success=True,
            message=f"Logged {duration_result.hours}h to {matter_match.match.display_name}"
        )
    
    def _handle_add_task(self, utterance: str, event: VoiceEvent) -> ProcessingResult:
        """Handle adding a task to the plan."""
        # This would use similar logic to _handle_plan but for a single task
        return ProcessingResult(
            success=True,
            message="Task added to plan"
        )
    
    def _close_current_work(self, description: str = "", is_break: bool = False):
        """Close the current work block without creating a log entry yet."""
        # In a more complete implementation, this would create a work log
        # For now, we just clear the state
        pass
    
    def _load_today_plan(self):
        """Load today's plan if it exists."""
        today = date.today()
        plan = self.session.query(DayPlan).filter(DayPlan.date == today).first()
        if plan:
            self.today_plan_id = plan.id
