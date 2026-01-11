"""Helper functions for Flask routes - reduces code duplication."""
import logging
from datetime import date, datetime, timedelta
from typing import List, Dict, Tuple, Optional, Any
from flask import request
from sqlalchemy.orm import Session, joinedload

from ..database.models import (
    Matter, ActivityType, DayPlan, PlannedTask, WorkLog
)

logger = logging.getLogger(__name__)


def parse_date_param(default: Optional[date] = None) -> date:
    """
    Parse date from request query parameter.

    Args:
        default: Default date if not provided or invalid. Defaults to today.

    Returns:
        Parsed date or default.
    """
    if default is None:
        default = date.today()

    date_str = request.args.get('date')
    if date_str:
        try:
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            logger.warning(f"Invalid date format: {date_str}")
    return default


def load_vocabulary_from_db(session: Session) -> Tuple[List[str], List[str]]:
    """
    Load vocabulary from database for Whisper transcription hints.

    Uses eager loading to avoid N+1 queries.

    Args:
        session: Database session

    Returns:
        Tuple of (matter_vocabulary, activity_vocabulary)
    """
    # Load matters with aliases eagerly to avoid N+1
    matters = session.query(Matter).options(
        joinedload(Matter.aliases)
    ).filter(Matter.is_active == True).all()

    matter_vocab = []
    for m in matters:
        if m.display_name:
            matter_vocab.append(m.display_name)
        if m.client:
            matter_vocab.append(m.client)
        # Aliases are already loaded via joinedload
        for alias in (m.aliases or []):
            if alias.alias:
                matter_vocab.append(alias.alias)

    # Load activity types
    activities = session.query(ActivityType).all()
    activity_vocab = [a.label for a in activities if a.label]

    return matter_vocab, activity_vocab


def load_task_vocabulary(session: Session, target_date: Optional[date] = None) -> List[str]:
    """
    Load planned task titles as vocabulary hints.

    Args:
        session: Database session
        target_date: Date to load tasks for (defaults to today)

    Returns:
        List of task-related vocabulary words
    """
    if target_date is None:
        target_date = date.today()

    plan = session.query(DayPlan).filter(DayPlan.date == target_date).first()
    if not plan:
        return []

    tasks = session.query(PlannedTask).filter(
        PlannedTask.day_plan_id == plan.id
    ).all()

    task_vocab = []
    for task in tasks:
        if task.title:
            task_vocab.append(task.title)
            # Also add individual words
            task_vocab.extend(task.title.split())

    return task_vocab


def get_full_vocabulary(session: Session, target_date: Optional[date] = None) -> Tuple[List[str], List[str]]:
    """
    Get complete vocabulary for transcription including matters, activities, and tasks.

    Args:
        session: Database session
        target_date: Date for task vocabulary (defaults to today)

    Returns:
        Tuple of (full_vocabulary, activity_vocabulary)
    """
    matter_vocab, activity_vocab = load_vocabulary_from_db(session)
    task_vocab = load_task_vocabulary(session, target_date)

    full_vocab = matter_vocab + task_vocab
    return full_vocab, activity_vocab


def calculate_work_totals(logs: List[WorkLog]) -> Tuple[Dict[str, float], float]:
    """
    Calculate hours totals by matter from work logs.

    Args:
        logs: List of WorkLog entries

    Returns:
        Tuple of (totals_by_matter, total_hours)
    """
    totals: Dict[str, float] = {}
    total_hours = 0.0

    for log in logs:
        matter_name = log.matter.display_name if log.matter else "General"
        if matter_name not in totals:
            totals[matter_name] = 0.0
        totals[matter_name] += log.duration_hours
        total_hours += log.duration_hours

    return totals, total_hours


def get_logs_for_date(session: Session, target_date: date) -> List[WorkLog]:
    """
    Get work logs for a specific date.

    Args:
        session: Database session
        target_date: Date to query logs for

    Returns:
        List of WorkLog entries ordered by creation time descending
    """
    next_day = target_date + timedelta(days=1)
    return session.query(WorkLog).filter(
        WorkLog.created_at >= target_date,
        WorkLog.created_at < next_day
    ).order_by(WorkLog.created_at.desc()).all()


def get_active_matters(session: Session, order_by_recency: bool = True) -> List[Matter]:
    """
    Get all active matters with eager-loaded aliases.

    Args:
        session: Database session
        order_by_recency: If True, order by last_used_at descending

    Returns:
        List of active Matter objects
    """
    query = session.query(Matter).options(
        joinedload(Matter.aliases)
    ).filter(Matter.is_active == True)

    if order_by_recency:
        query = query.order_by(Matter.last_used_at.desc().nullslast())
    else:
        query = query.order_by(Matter.display_name)

    return query.all()


def get_activity_types(session: Session) -> List[ActivityType]:
    """
    Get all activity types ordered by display order.

    Args:
        session: Database session

    Returns:
        List of ActivityType objects
    """
    return session.query(ActivityType).order_by(ActivityType.display_order).all()


def safe_cleanup(func, *args, **kwargs) -> None:
    """
    Execute a cleanup function, logging any errors instead of raising.

    Args:
        func: Function to call
        *args, **kwargs: Arguments to pass to func
    """
    try:
        func(*args, **kwargs)
    except Exception as e:
        logger.debug(f"Non-critical cleanup error: {e}")
