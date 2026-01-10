"""SQLAlchemy models for TimeBrief."""
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


class ActiveTimer(Base):
    """
    Tracks the currently running timer.
    Only ONE active timer allowed at a time (enforced in app logic).
    """
    __tablename__ = "active_timers"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    matter_id = Column(String, ForeignKey("matters.id"), nullable=False)
    activity_type_id = Column(String, ForeignKey("activity_types.id"))
    started_at = Column(DateTime, nullable=False, default=func.now())
    paused_at = Column(DateTime)  # If paused, when it was paused
    accumulated_seconds = Column(Integer, default=0)  # Time from previous pauses
    narrative_draft = Column(Text)  # Working narrative
    is_active = Column(Boolean, default=True)  # False if paused
    created_at = Column(DateTime, default=func.now())
    
    matter = relationship("Matter")
    activity_type = relationship("ActivityType")
    
    @property
    def elapsed_seconds(self) -> int:
        """Total elapsed time including pauses."""
        if self.paused_at:
            # Timer is paused - return accumulated time
            return self.accumulated_seconds
        else:
            # Timer is running - add time since started
            from datetime import datetime
            running_time = (datetime.now() - self.started_at).total_seconds()
            return self.accumulated_seconds + int(running_time)
    
    @property
    def elapsed_units(self) -> int:
        """Elapsed time in 6-minute billing units (rounded up)."""
        import math
        return math.ceil(self.elapsed_seconds / 360)  # 6 min = 360 sec
    
    @property
    def elapsed_hours(self) -> float:
        """Elapsed time in decimal hours (for billing)."""
        return self.elapsed_units * 0.1  # Each unit = 0.1 hour


class Memo(Base):
    """
    Voice memos/notes for a matter.
    Separates thoughts (notes) from actions (follow-ups).
    """
    __tablename__ = "memos"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    matter_id = Column(String, ForeignKey("matters.id"), nullable=False)
    thoughts = Column(Text, nullable=False)  # General notes/observations
    created_at = Column(DateTime, default=func.now())
    duration_seconds = Column(Integer)  # How long they spoke
    
    matter = relationship("Matter")
    actions = relationship("MemoAction", back_populates="memo", cascade="all, delete-orphan")


class MemoAction(Base):
    """
    Individual action items extracted from voice memos.
    These appear in Planning the next day.
    """
    __tablename__ = "memo_actions"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    memo_id = Column(String, ForeignKey("memos.id"), nullable=False)
    matter_id = Column(String, ForeignKey("matters.id"), nullable=False)
    description = Column(Text, nullable=False)
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime)
    due_date = Column(Date)  # When it should appear in planning
    created_at = Column(DateTime, default=func.now())
    
    memo = relationship("Memo", back_populates="actions")
    matter = relationship("Matter")


# Indexes
Index("idx_matters_active", Matter.is_active)
Index("idx_matters_last_used", Matter.last_used_at.desc())
Index("idx_work_logs_date", WorkLog.started_at)
Index("idx_planned_tasks_date", PlannedTask.day_plan_id)
Index("idx_voice_events_timestamp", VoiceEvent.timestamp)
Index("idx_memos_matter", Memo.matter_id)
Index("idx_memos_created", Memo.created_at.desc())
Index("idx_memo_actions_pending", MemoAction.is_completed, MemoAction.due_date)
Index("idx_memo_actions_matter", MemoAction.matter_id)
