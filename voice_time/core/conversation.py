"""
Conversation Manager - Handles chat-style interactions with full context.

Provides:
- Persistent conversation history
- Transcription display
- Error tracking with suggestions
- Undo/redo support
- Matter context memory
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from sqlalchemy.orm import Session

from ..database.models import (
    Conversation, ChatMessage, UndoAction, MatterContext,
    Matter, WorkLog, ActiveTimer, PlannedTask,
    MessageRole, MessageType
)

logger = logging.getLogger(__name__)


@dataclass
class ConversationResponse:
    """Response from processing a user message."""
    success: bool
    message: str
    transcript: Optional[str] = None

    # Parsing details
    parsed_intent: Optional[str] = None
    parsed_matter: Optional[str] = None
    parsed_activity: Optional[str] = None
    parsed_duration: Optional[float] = None
    confidence: Optional[float] = None

    # Error handling
    error_type: Optional[str] = None
    error_message: Optional[str] = None

    # Suggestions for user
    suggestions: List[str] = field(default_factory=list)

    # Action taken
    action_taken: Optional[str] = None
    action_reference_id: Optional[str] = None
    can_undo: bool = False

    # Conversation context
    conversation_id: Optional[str] = None
    message_id: Optional[str] = None

    # For clarifications
    needs_clarification: bool = False
    clarification_question: Optional[str] = None
    clarification_options: List[str] = field(default_factory=list)


class ConversationManager:
    """
    Manages conversation sessions and message history.
    """

    def __init__(self, session: Session):
        self.session = session
        self._current_conversation: Optional[Conversation] = None
        self._undo_stack: List[str] = []  # Stack of UndoAction IDs
        self._max_undo_stack = 50

    def get_or_create_conversation(self, matter_id: Optional[str] = None) -> Conversation:
        """
        Get active conversation or create a new one.
        Conversations older than 4 hours are considered stale.
        """
        cutoff = datetime.now() - timedelta(hours=4)

        # Try to find recent active conversation
        conv = self.session.query(Conversation).filter(
            Conversation.is_active == True,
            Conversation.started_at > cutoff
        ).order_by(Conversation.started_at.desc()).first()

        if conv:
            self._current_conversation = conv
            return conv

        # Create new conversation
        conv = Conversation(
            matter_id=matter_id,
            is_active=True
        )
        self.session.add(conv)
        self.session.flush()

        self._current_conversation = conv
        return conv

    def add_user_message(
        self,
        content: str,
        transcript: Optional[str] = None,
        message_type: str = MessageType.TEXT.value,
        audio_path: Optional[str] = None
    ) -> ChatMessage:
        """Add a user message to the current conversation."""
        conv = self.get_or_create_conversation()

        msg = ChatMessage(
            conversation_id=conv.id,
            role=MessageRole.USER.value,
            message_type=message_type,
            content=content,
            transcript=transcript or content,
            audio_path=audio_path
        )
        self.session.add(msg)
        self.session.flush()

        return msg

    def add_assistant_response(
        self,
        response: ConversationResponse,
        user_message_id: Optional[str] = None
    ) -> ChatMessage:
        """Add an assistant response to the current conversation."""
        conv = self.get_or_create_conversation()

        # Determine message type
        if response.error_type:
            msg_type = MessageType.ERROR.value
        elif response.needs_clarification:
            msg_type = MessageType.CLARIFICATION.value
        elif response.success:
            msg_type = MessageType.SUCCESS.value
        else:
            msg_type = MessageType.TEXT.value

        msg = ChatMessage(
            conversation_id=conv.id,
            role=MessageRole.ASSISTANT.value,
            message_type=msg_type,
            content=response.message,
            parsed_intent=response.parsed_intent,
            parsed_matter=response.parsed_matter,
            parsed_activity=response.parsed_activity,
            parsed_duration=response.parsed_duration,
            confidence=response.confidence,
            error_type=response.error_type,
            error_message=response.error_message,
            suggestions=json.dumps(response.suggestions) if response.suggestions else None,
            action_taken=response.action_taken,
            action_reference_id=response.action_reference_id,
            action_reversible=response.can_undo
        )
        self.session.add(msg)
        self.session.flush()

        response.message_id = msg.id
        response.conversation_id = conv.id

        return msg

    def get_conversation_history(
        self,
        conversation_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get conversation history formatted for display."""
        if conversation_id:
            conv = self.session.query(Conversation).get(conversation_id)
        else:
            conv = self._current_conversation or self.get_or_create_conversation()

        if not conv:
            return []

        messages = self.session.query(ChatMessage).filter(
            ChatMessage.conversation_id == conv.id
        ).order_by(ChatMessage.created_at.desc()).limit(limit).all()

        # Reverse to get chronological order
        messages = list(reversed(messages))

        history = []
        for msg in messages:
            entry = {
                'id': msg.id,
                'role': msg.role,
                'type': msg.message_type,
                'content': msg.content,
                'timestamp': msg.created_at.isoformat(),
                'time_display': msg.created_at.strftime('%H:%M')
            }

            # Add transcript for voice messages
            if msg.transcript and msg.transcript != msg.content:
                entry['transcript'] = msg.transcript

            # Add parsing details
            if msg.parsed_intent:
                entry['parsed'] = {
                    'intent': msg.parsed_intent,
                    'matter': msg.parsed_matter,
                    'activity': msg.parsed_activity,
                    'duration': msg.parsed_duration,
                    'confidence': msg.confidence
                }

            # Add error info
            if msg.error_type:
                entry['error'] = {
                    'type': msg.error_type,
                    'message': msg.error_message
                }

            # Add suggestions
            if msg.suggestions:
                try:
                    entry['suggestions'] = json.loads(msg.suggestions)
                except json.JSONDecodeError:
                    pass

            # Add action info
            if msg.action_taken:
                entry['action'] = {
                    'type': msg.action_taken,
                    'reference_id': msg.action_reference_id,
                    'can_undo': msg.action_reversible
                }

            history.append(entry)

        return history

    def get_recent_conversations(self, days: int = 7, limit: int = 20) -> List[Dict[str, Any]]:
        """Get list of recent conversations with summaries."""
        cutoff = datetime.now() - timedelta(days=days)

        conversations = self.session.query(Conversation).filter(
            Conversation.started_at > cutoff
        ).order_by(Conversation.started_at.desc()).limit(limit).all()

        result = []
        for conv in conversations:
            # Get message count
            msg_count = self.session.query(ChatMessage).filter(
                ChatMessage.conversation_id == conv.id
            ).count()

            # Get first user message as preview
            first_msg = self.session.query(ChatMessage).filter(
                ChatMessage.conversation_id == conv.id,
                ChatMessage.role == MessageRole.USER.value
            ).order_by(ChatMessage.created_at).first()

            result.append({
                'id': conv.id,
                'started_at': conv.started_at.isoformat(),
                'date_display': conv.started_at.strftime('%b %d, %H:%M'),
                'matter_id': conv.matter_id,
                'matter_name': conv.matter.display_name if conv.matter else None,
                'message_count': msg_count,
                'preview': first_msg.content[:100] if first_msg else None,
                'is_active': conv.is_active
            })

        return result

    # ==================== Undo System ====================

    def record_action(
        self,
        action_type: str,
        entity_type: str,
        entity_id: str,
        previous_state: Optional[Dict] = None,
        new_state: Optional[Dict] = None,
        description: str = ""
    ) -> UndoAction:
        """Record an action for potential undo."""
        action = UndoAction(
            action_type=action_type,
            entity_type=entity_type,
            entity_id=entity_id,
            previous_state=json.dumps(previous_state) if previous_state else None,
            new_state=json.dumps(new_state) if new_state else None,
            description=description
        )
        self.session.add(action)
        self.session.flush()

        # Add to undo stack
        self._undo_stack.append(action.id)
        if len(self._undo_stack) > self._max_undo_stack:
            self._undo_stack.pop(0)

        return action

    def undo_last_action(self) -> Tuple[bool, str]:
        """
        Undo the last action.
        Returns (success, message).
        """
        if not self._undo_stack:
            # Try to load from database
            recent_action = self.session.query(UndoAction).filter(
                UndoAction.is_undone == False
            ).order_by(UndoAction.created_at.desc()).first()

            if not recent_action:
                return False, "Nothing to undo"

            action_id = recent_action.id
        else:
            action_id = self._undo_stack.pop()

        action = self.session.query(UndoAction).get(action_id)
        if not action or action.is_undone:
            return False, "Action already undone"

        try:
            success, message = self._execute_undo(action)
            if success:
                action.is_undone = True
                action.undone_at = datetime.now()
                self.session.commit()
            return success, message
        except Exception as e:
            logger.exception("Undo failed")
            self.session.rollback()
            return False, f"Undo failed: {str(e)}"

    def _execute_undo(self, action: UndoAction) -> Tuple[bool, str]:
        """Execute the actual undo operation."""
        if action.action_type == "create":
            # Delete the created entity
            return self._undo_create(action)
        elif action.action_type == "update":
            # Restore previous state
            return self._undo_update(action)
        elif action.action_type == "delete":
            # Recreate the entity
            return self._undo_delete(action)
        else:
            return False, f"Unknown action type: {action.action_type}"

    def _undo_create(self, action: UndoAction) -> Tuple[bool, str]:
        """Undo a create action by deleting the entity."""
        if action.entity_type == "work_log":
            entity = self.session.query(WorkLog).get(action.entity_id)
            if entity:
                self.session.delete(entity)
                return True, f"Deleted time entry: {action.description}"
        elif action.entity_type == "timer":
            entity = self.session.query(ActiveTimer).get(action.entity_id)
            if entity:
                self.session.delete(entity)
                return True, f"Stopped timer: {action.description}"
        elif action.entity_type == "planned_task":
            entity = self.session.query(PlannedTask).get(action.entity_id)
            if entity:
                self.session.delete(entity)
                return True, f"Removed task: {action.description}"

        return False, "Entity not found"

    def _undo_update(self, action: UndoAction) -> Tuple[bool, str]:
        """Undo an update by restoring previous state."""
        if not action.previous_state:
            return False, "No previous state to restore"

        previous = json.loads(action.previous_state)

        if action.entity_type == "work_log":
            entity = self.session.query(WorkLog).get(action.entity_id)
            if entity:
                for key, value in previous.items():
                    if hasattr(entity, key):
                        setattr(entity, key, value)
                return True, f"Restored: {action.description}"

        return False, "Entity not found"

    def _undo_delete(self, action: UndoAction) -> Tuple[bool, str]:
        """Undo a delete by recreating the entity."""
        if not action.previous_state:
            return False, "No state to restore"

        previous = json.loads(action.previous_state)

        if action.entity_type == "work_log":
            # Recreate work log
            entity = WorkLog(**previous)
            self.session.add(entity)
            return True, f"Restored: {action.description}"

        return False, "Cannot restore this entity type"

    def get_undo_preview(self) -> Optional[str]:
        """Get description of what will be undone."""
        if self._undo_stack:
            action = self.session.query(UndoAction).get(self._undo_stack[-1])
            if action and not action.is_undone:
                return action.description

        # Check database
        recent = self.session.query(UndoAction).filter(
            UndoAction.is_undone == False
        ).order_by(UndoAction.created_at.desc()).first()

        if recent:
            return recent.description

        return None


class MatterContextManager:
    """
    Manages contextual memory for each matter.
    Remembers work patterns, last activities, common narratives.
    """

    def __init__(self, session: Session):
        self.session = session

    def get_context(self, matter_id: str) -> Optional[MatterContext]:
        """Get or create context for a matter."""
        context = self.session.query(MatterContext).filter(
            MatterContext.matter_id == matter_id
        ).first()

        if not context:
            context = MatterContext(matter_id=matter_id)
            self.session.add(context)
            self.session.flush()

        return context

    def update_from_work_log(self, work_log: WorkLog) -> None:
        """Update matter context after a work log is created."""
        if not work_log.matter_id:
            return

        context = self.get_context(work_log.matter_id)

        # Update last activity
        context.last_activity_type_id = work_log.activity_type_id
        context.last_narrative = work_log.narrative
        context.last_worked_at = datetime.now()

        # Update common activities
        activities = json.loads(context.common_activities or '{}')
        activity_id = work_log.activity_type_id or 'none'
        activities[activity_id] = activities.get(activity_id, 0) + 1
        context.common_activities = json.dumps(activities)

        # Update common narratives
        if work_log.narrative:
            narratives = json.loads(context.common_narratives or '[]')
            # Keep unique, limit to 20
            if work_log.narrative not in narratives:
                narratives.insert(0, work_log.narrative)
                narratives = narratives[:20]
            context.common_narratives = json.dumps(narratives)

        # Update average session hours
        logs = self.session.query(WorkLog).filter(
            WorkLog.matter_id == work_log.matter_id
        ).order_by(WorkLog.created_at.desc()).limit(20).all()

        if logs:
            avg_hours = sum(l.duration_hours for l in logs) / len(logs)
            context.average_session_hours = round(avg_hours, 2)

        self.session.flush()

    def get_suggestions(self, matter_id: str) -> Dict[str, Any]:
        """Get suggestions based on matter context."""
        context = self.get_context(matter_id)
        matter = self.session.query(Matter).get(matter_id)

        suggestions = {
            'matter_name': matter.display_name if matter else None,
            'last_activity': None,
            'last_narrative': context.last_narrative,
            'common_activities': [],
            'suggested_duration': context.average_session_hours,
            'ai_notes': context.ai_context_notes
        }

        # Get last activity name
        if context.last_activity:
            suggestions['last_activity'] = context.last_activity.label

        # Get top common activities
        if context.common_activities:
            activities = json.loads(context.common_activities)
            from ..database.models import ActivityType

            sorted_activities = sorted(activities.items(), key=lambda x: x[1], reverse=True)[:3]
            for activity_id, count in sorted_activities:
                if activity_id != 'none':
                    activity = self.session.query(ActivityType).get(activity_id)
                    if activity:
                        suggestions['common_activities'].append({
                            'id': activity.id,
                            'label': activity.label,
                            'count': count
                        })

        return suggestions

    def get_resume_context(self, matter_id: str) -> Optional[str]:
        """Get context for 'continue where I left off' command."""
        context = self.get_context(matter_id)

        if not context.last_worked_at:
            return None

        parts = []

        if context.last_activity:
            parts.append(f"Last activity: {context.last_activity.label}")

        if context.last_narrative:
            parts.append(f"Working on: {context.last_narrative}")

        if context.last_worked_at:
            time_ago = datetime.now() - context.last_worked_at
            if time_ago.days > 0:
                parts.append(f"({time_ago.days} days ago)")
            elif time_ago.seconds > 3600:
                parts.append(f"({time_ago.seconds // 3600} hours ago)")
            else:
                parts.append(f"({time_ago.seconds // 60} minutes ago)")

        return " | ".join(parts) if parts else None
