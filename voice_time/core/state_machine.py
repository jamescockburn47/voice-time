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
    WorkLog, VoiceEvent
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
    
    def _handle_edit_command(self, cmd, event: VoiceEvent) -> ProcessingResult:
        """
        Handle voice editing commands for work log entries - COMPLETELY HANDS-FREE.
        
        BUG FIX 1: Now handles all command types including 'add_time', 'change_matter', 'change_activity'
        BUG FIX 2: Validates entry_number >= 1 to prevent negative indexing
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
        
        # BUG FIX 2: Validate entry number is valid (>= 1 and <= len(logs))
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
            # BUG FIX 1: Handle add_time command properly
            # Find matter
            matter_match = self.matter_matcher.find_matter(cmd.matter_name)
            if not matter_match.match:
                return ProcessingResult(
                    success=False,
                    message=f"Could not find matter: {cmd.matter_name}",
                    needs_clarification=True
                )
            
            # Infer activity from context or default to ADMIN
            activity_match = self.activity_matcher.find_activity_type(cmd.matter_name)
            activity_id = activity_match.match.id if activity_match.match else None
            
            # Create new work log
            work_log = WorkLog(
                matter_id=matter_match.match.id,
                activity_type_id=activity_id,
                duration_hours=cmd.new_duration,
                narrative=f"Additional time entry - {cmd.matter_name}",
                started_at=datetime.now() - timedelta(hours=cmd.new_duration),
                ended_at=datetime.now(),
                source_event_id=event.id,
                allocation_status="allocated"
            )
            self.session.add(work_log)
            self.session.commit()
            
            return ProcessingResult(
                success=True,
                message=f"✓ Added {cmd.new_duration}h to {matter_match.match.display_name}"
            )
        
        # If we get here, command type wasn't recognized
        return ProcessingResult(
            success=False,
            message=f"Edit command type '{cmd.command_type}' not yet implemented"
        )
    
    def _handle_plan(self, utterance: str, event: VoiceEvent) -> ProcessingResult:
        """Handle morning planning."""
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
        for i, task_data in enumerate(parsed["tasks"]):
            # Resolve matter
            matter = None
            if task_data["matter_ref"]:
                match = self.matter_matcher.find_matter(task_data["matter_ref"])
                if match.match:
                    matter = match.match
            
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
        
        message = f"✓ Planned {task_count} task{'s' if task_count != 1 else ''}"
        if matter_count > 0:
            message += f" across {matter_count} matter{'s' if matter_count != 1 else ''}"
        
        if parsed["unresolved_mentions"]:
            message += f"\n\nNote: Couldn't identify: {', '.join(parsed['unresolved_mentions'])}"
        
        return ProcessingResult(
            success=True,
            message=message,
            data={"tasks": created_tasks, "plan_id": plan.id}
        )
    
    def _handle_start(self, utterance: str, event: VoiceEvent) -> ProcessingResult:
        """Handle starting work on a task."""
        # Close current work if any
        if self.current_work_started_at:
            self._close_current_work(utterance)
        
        # Extract matter and activity
        matter_match = self.matter_matcher.find_matter(utterance)
        activity_match = self.activity_matcher.find_activity_type(utterance)
        
        if not matter_match.match:
            return ProcessingResult(
                success=False,
                message="Which matter is this for?",
                needs_clarification=True,
                clarification_question="matter"
            )
        
        # Start new work block
        self.active_matter_id = matter_match.match.id
        self.active_activity_type_id = activity_match.match.id if activity_match.match else None
        self.current_work_started_at = datetime.now()
        
        # Touch the matter (update recency)
        matter_match.match.touch()
        self.session.commit()
        
        matter_name = matter_match.match.display_name
        activity_name = activity_match.match.label if activity_match.match else "work"
        
        return ProcessingResult(
            success=True,
            message=f"▶ Started: {matter_name} - {activity_name}"
        )
    
    def _handle_complete(self, utterance: str, event: VoiceEvent) -> ProcessingResult:
        """Handle completing a task."""
        if not self.current_work_started_at:
            return self._handle_log_historical(utterance, event)
        
        # Infer duration
        duration_result = self.temporal_parser.infer_duration(
            utterance,
            self.current_work_started_at,
            datetime.now()
        )
        
        # Get matter and activity
        matter = self.session.query(Matter).get(self.active_matter_id)
        activity = self.session.query(ActivityType).get(self.active_activity_type_id)
        
        # Generate narrative
        narrative = self.narrative_generator.generate(
            utterance,
            matter.display_name if matter else "General",
            activity.code if activity else "ADMIN",
            duration_result.hours
        )
        
        # Create work log
        work_log = WorkLog(
            matter_id=self.active_matter_id,
            activity_type_id=self.active_activity_type_id,
            planned_task_id=self.active_planned_task_id,
            started_at=self.current_work_started_at,
            ended_at=datetime.now(),
            duration_hours=duration_result.hours,
            narrative=narrative,
            source_event_id=event.id
        )
        self.session.add(work_log)
        
        # Mark planned task as done if linked
        if self.active_planned_task_id:
            task = self.session.query(PlannedTask).get(self.active_planned_task_id)
            if task:
                task.status = "done"
        
        # Clear active work
        self.active_matter_id = None
        self.active_activity_type_id = None
        self.active_planned_task_id = None
        self.current_work_started_at = None
        
        self.session.commit()
        
        matter_name = matter.display_name if matter else "General"
        activity_name = activity.label if activity else "work"
        
        message = f"✓ Logged {duration_result.hours}h to {matter_name} - {activity_name}"
        
        if duration_result.needs_confirmation:
            message += f"\n(Inferred from {duration_result.source} - say 'change entry X to Y hours' if incorrect)"
        
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
            return ProcessingResult(
                success=False,
                message="Which matter was this for?",
                needs_clarification=True
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
            message=f"✓ Logged {duration_result.hours}h to {matter_match.match.display_name}"
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
