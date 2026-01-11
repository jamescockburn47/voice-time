"""
Analytics and Gap Detection Services.

Provides:
- Time gap detection
- Productivity analytics
- Matter health indicators
- Smart deduplication
- Heatmap data generation
"""
import json
import logging
from datetime import datetime, date, timedelta, time
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from collections import defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from ..database.models import (
    WorkLog, Matter, ActiveTimer, TimeGap, PotentialDuplicate,
    PlannedTask, DayPlan, MemoAction, ActivityType, UserPreferences
)

logger = logging.getLogger(__name__)


@dataclass
class GapInfo:
    """Information about a detected time gap."""
    start: datetime
    end: datetime
    duration_minutes: int
    before_matter: Optional[str] = None
    after_matter: Optional[str] = None
    suggestion: Optional[str] = None


@dataclass
class MatterHealth:
    """Health indicators for a matter."""
    matter_id: str
    matter_name: str
    total_hours: float
    days_since_activity: int
    pending_tasks: int
    pending_memos: int
    upcoming_deadlines: int
    status: str  # "active", "stale", "needs_attention", "on_track"
    warnings: List[str]


@dataclass
class ProductivityStats:
    """Productivity statistics for a time period."""
    total_hours: float
    billable_hours: float
    non_billable_hours: float
    utilization_rate: float  # billable / total
    average_entry_hours: float
    matters_worked: int
    most_productive_day: Optional[str] = None
    most_productive_hour: Optional[int] = None
    comparison_vs_average: Optional[float] = None  # percentage difference


class GapDetector:
    """
    Detects gaps in time tracking.
    """

    def __init__(self, session: Session):
        self.session = session
        self._working_hours = (9, 18)  # 9 AM to 6 PM
        self._lunch_hours = (12, 13)  # 12 PM to 1 PM
        self._gap_threshold_minutes = 30

    def configure(self, preferences: UserPreferences) -> None:
        """Configure from user preferences."""
        if preferences:
            self._gap_threshold_minutes = preferences.gap_threshold_minutes or 30

    def detect_gaps(self, target_date: date = None) -> List[GapInfo]:
        """
        Detect time gaps for a given date.
        Returns gaps that exceed the threshold during working hours.
        """
        if target_date is None:
            target_date = date.today()

        # Get all work logs for the date
        start_of_day = datetime.combine(target_date, time(0, 0))
        end_of_day = datetime.combine(target_date + timedelta(days=1), time(0, 0))

        logs = self.session.query(WorkLog).filter(
            and_(
                WorkLog.created_at >= start_of_day,
                WorkLog.created_at < end_of_day
            )
        ).order_by(WorkLog.created_at).all()

        # Get active timer
        timer = self.session.query(ActiveTimer).first()

        gaps = []
        work_start = datetime.combine(target_date, time(self._working_hours[0], 0))
        work_end = datetime.combine(target_date, time(self._working_hours[1], 0))
        lunch_start = datetime.combine(target_date, time(self._lunch_hours[0], 0))
        lunch_end = datetime.combine(target_date, time(self._lunch_hours[1], 0))

        if not logs:
            # No logs today - check if we should have some
            now = datetime.now()
            if target_date == date.today() and now > work_start:
                # It's today and past work start - that's a gap
                gap_end = min(now, work_end)
                duration = int((gap_end - work_start).total_seconds() / 60)

                # Exclude lunch
                if work_start < lunch_start and gap_end > lunch_end:
                    duration -= 60  # Subtract lunch hour

                if duration > self._gap_threshold_minutes:
                    gaps.append(GapInfo(
                        start=work_start,
                        end=gap_end,
                        duration_minutes=duration,
                        suggestion="No time logged today. What have you been working on?"
                    ))
            return gaps

        # Check gap from work start to first log
        first_log = logs[0]
        if first_log.created_at > work_start:
            gap_duration = int((first_log.created_at - work_start).total_seconds() / 60)
            if gap_duration > self._gap_threshold_minutes:
                gaps.append(GapInfo(
                    start=work_start,
                    end=first_log.created_at,
                    duration_minutes=gap_duration,
                    after_matter=first_log.matter.display_name if first_log.matter else None,
                    suggestion="Morning gap before first entry"
                ))

        # Check gaps between logs
        for i in range(len(logs) - 1):
            current_log = logs[i]
            next_log = logs[i + 1]

            # Calculate end time of current log
            if current_log.ended_at:
                current_end = current_log.ended_at
            elif current_log.started_at and current_log.duration_hours:
                current_end = current_log.started_at + timedelta(hours=current_log.duration_hours)
            else:
                current_end = current_log.created_at + timedelta(hours=current_log.duration_hours)

            gap_start = current_end
            gap_end = next_log.started_at or next_log.created_at

            # Skip if gap includes lunch
            if gap_start < lunch_end and gap_end > lunch_start:
                # Adjust for lunch overlap
                if gap_start < lunch_start:
                    pre_lunch_gap = int((lunch_start - gap_start).total_seconds() / 60)
                    if pre_lunch_gap > self._gap_threshold_minutes:
                        gaps.append(GapInfo(
                            start=gap_start,
                            end=lunch_start,
                            duration_minutes=pre_lunch_gap,
                            before_matter=current_log.matter.display_name if current_log.matter else None,
                            after_matter=next_log.matter.display_name if next_log.matter else None
                        ))
                if gap_end > lunch_end:
                    post_lunch_gap = int((gap_end - lunch_end).total_seconds() / 60)
                    if post_lunch_gap > self._gap_threshold_minutes:
                        gaps.append(GapInfo(
                            start=lunch_end,
                            end=gap_end,
                            duration_minutes=post_lunch_gap,
                            before_matter=current_log.matter.display_name if current_log.matter else None,
                            after_matter=next_log.matter.display_name if next_log.matter else None
                        ))
                continue

            gap_duration = int((gap_end - gap_start).total_seconds() / 60)
            if gap_duration > self._gap_threshold_minutes:
                gaps.append(GapInfo(
                    start=gap_start,
                    end=gap_end,
                    duration_minutes=gap_duration,
                    before_matter=current_log.matter.display_name if current_log.matter else None,
                    after_matter=next_log.matter.display_name if next_log.matter else None
                ))

        # Check gap from last log to now (if today) or work end
        last_log = logs[-1]
        if last_log.ended_at:
            last_end = last_log.ended_at
        elif last_log.started_at and last_log.duration_hours:
            last_end = last_log.started_at + timedelta(hours=last_log.duration_hours)
        else:
            last_end = last_log.created_at + timedelta(hours=last_log.duration_hours)

        # Only check if no active timer
        if not timer:
            check_end = datetime.now() if target_date == date.today() else work_end
            if check_end > last_end:
                gap_duration = int((check_end - last_end).total_seconds() / 60)
                if gap_duration > self._gap_threshold_minutes:
                    gaps.append(GapInfo(
                        start=last_end,
                        end=check_end,
                        duration_minutes=gap_duration,
                        before_matter=last_log.matter.display_name if last_log.matter else None,
                        suggestion="Gap since last entry" if target_date == date.today() else "End of day gap"
                    ))

        return gaps

    def save_gap(self, gap: GapInfo) -> TimeGap:
        """Save a detected gap to the database."""
        # Check if gap already exists
        existing = self.session.query(TimeGap).filter(
            and_(
                TimeGap.gap_start == gap.start,
                TimeGap.gap_end == gap.end
            )
        ).first()

        if existing:
            return existing

        # Find before/after matters
        before_matter = None
        after_matter = None

        if gap.before_matter:
            before_matter = self.session.query(Matter).filter(
                Matter.display_name == gap.before_matter
            ).first()
        if gap.after_matter:
            after_matter = self.session.query(Matter).filter(
                Matter.display_name == gap.after_matter
            ).first()

        time_gap = TimeGap(
            gap_start=gap.start,
            gap_end=gap.end,
            duration_minutes=gap.duration_minutes,
            before_matter_id=before_matter.id if before_matter else None,
            after_matter_id=after_matter.id if after_matter else None
        )
        self.session.add(time_gap)
        self.session.flush()

        return time_gap


class ProductivityAnalyzer:
    """
    Analyzes productivity and generates statistics.
    """

    def __init__(self, session: Session):
        self.session = session

    def get_stats(
        self,
        start_date: date,
        end_date: date = None
    ) -> ProductivityStats:
        """Get productivity statistics for a date range."""
        if end_date is None:
            end_date = start_date

        start_dt = datetime.combine(start_date, time(0, 0))
        end_dt = datetime.combine(end_date + timedelta(days=1), time(0, 0))

        logs = self.session.query(WorkLog).filter(
            and_(
                WorkLog.created_at >= start_dt,
                WorkLog.created_at < end_dt
            )
        ).all()

        if not logs:
            return ProductivityStats(
                total_hours=0,
                billable_hours=0,
                non_billable_hours=0,
                utilization_rate=0,
                average_entry_hours=0,
                matters_worked=0
            )

        total_hours = sum(l.duration_hours for l in logs)

        # Calculate billable vs non-billable
        billable = 0
        non_billable = 0
        for log in logs:
            if log.activity_type and log.activity_type.is_billable:
                billable += log.duration_hours
            else:
                non_billable += log.duration_hours

        matters = set(l.matter_id for l in logs if l.matter_id)

        # Find most productive day
        day_hours = defaultdict(float)
        hour_counts = defaultdict(float)

        for log in logs:
            day_name = log.created_at.strftime('%A')
            day_hours[day_name] += log.duration_hours
            hour_counts[log.created_at.hour] += log.duration_hours

        most_productive_day = max(day_hours, key=day_hours.get) if day_hours else None
        most_productive_hour = max(hour_counts, key=hour_counts.get) if hour_counts else None

        # Calculate comparison to average (last 4 weeks)
        comparison = None
        four_weeks_ago = start_date - timedelta(weeks=4)
        historical_logs = self.session.query(WorkLog).filter(
            and_(
                WorkLog.created_at >= datetime.combine(four_weeks_ago, time(0, 0)),
                WorkLog.created_at < start_dt
            )
        ).all()

        if historical_logs:
            historical_days = (start_date - four_weeks_ago).days
            historical_avg_per_day = sum(l.duration_hours for l in historical_logs) / historical_days
            current_days = (end_date - start_date).days + 1
            current_avg_per_day = total_hours / current_days

            if historical_avg_per_day > 0:
                comparison = ((current_avg_per_day - historical_avg_per_day) / historical_avg_per_day) * 100

        return ProductivityStats(
            total_hours=round(total_hours, 1),
            billable_hours=round(billable, 1),
            non_billable_hours=round(non_billable, 1),
            utilization_rate=round(billable / total_hours * 100 if total_hours > 0 else 0, 1),
            average_entry_hours=round(total_hours / len(logs), 2),
            matters_worked=len(matters),
            most_productive_day=most_productive_day,
            most_productive_hour=most_productive_hour,
            comparison_vs_average=round(comparison, 1) if comparison is not None else None
        )

    def get_heatmap_data(self, weeks: int = 4) -> Dict[str, Any]:
        """
        Generate heatmap data for time distribution.
        Returns data suitable for rendering a weekly heatmap.
        """
        end_date = date.today()
        start_date = end_date - timedelta(weeks=weeks)

        logs = self.session.query(WorkLog).filter(
            WorkLog.created_at >= datetime.combine(start_date, time(0, 0))
        ).all()

        # Build heatmap: day of week x hour of day
        heatmap = defaultdict(lambda: defaultdict(float))
        day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

        for log in logs:
            day_idx = log.created_at.weekday()
            hour = log.created_at.hour
            heatmap[day_idx][hour] += log.duration_hours

        # Convert to display format
        data = {
            'days': day_names,
            'hours': list(range(7, 20)),  # 7 AM to 8 PM
            'values': []
        }

        max_value = 0
        for hour in data['hours']:
            row = []
            for day_idx in range(7):
                value = round(heatmap[day_idx][hour], 1)
                row.append(value)
                max_value = max(max_value, value)
            data['values'].append(row)

        data['max_value'] = max_value

        return data


class MatterHealthAnalyzer:
    """
    Analyzes health indicators for matters.
    """

    def __init__(self, session: Session):
        self.session = session

    def get_health(self, matter_id: str) -> MatterHealth:
        """Get health indicators for a specific matter."""
        matter = self.session.query(Matter).get(matter_id)
        if not matter:
            return None

        # Calculate total hours
        total_hours = self.session.query(func.sum(WorkLog.duration_hours)).filter(
            WorkLog.matter_id == matter_id
        ).scalar() or 0

        # Days since last activity
        last_log = self.session.query(WorkLog).filter(
            WorkLog.matter_id == matter_id
        ).order_by(WorkLog.created_at.desc()).first()

        days_since = 0
        if last_log:
            days_since = (date.today() - last_log.created_at.date()).days
        elif matter.last_used_at:
            days_since = (date.today() - matter.last_used_at.date()).days

        # Pending tasks
        pending_tasks = self.session.query(PlannedTask).join(DayPlan).filter(
            PlannedTask.matter_id == matter_id,
            PlannedTask.status.in_(['pending', 'planned', 'in_progress'])
        ).count()

        # Pending memo actions
        pending_memos = self.session.query(MemoAction).filter(
            MemoAction.matter_id == matter_id,
            MemoAction.is_completed == False
        ).count()

        # Upcoming deadlines (tasks with due dates in next 7 days)
        next_week = date.today() + timedelta(days=7)
        upcoming = self.session.query(MemoAction).filter(
            MemoAction.matter_id == matter_id,
            MemoAction.is_completed == False,
            MemoAction.due_date <= next_week,
            MemoAction.due_date >= date.today()
        ).count()

        # Determine status and warnings
        warnings = []
        status = "on_track"

        if days_since > 14:
            status = "stale"
            warnings.append(f"No activity in {days_since} days")
        elif days_since > 7:
            status = "needs_attention"
            warnings.append(f"No activity in {days_since} days")

        if pending_tasks > 5:
            if status == "on_track":
                status = "needs_attention"
            warnings.append(f"{pending_tasks} pending tasks")

        if upcoming > 0:
            warnings.append(f"{upcoming} upcoming deadlines")

        if pending_memos > 3:
            warnings.append(f"{pending_memos} unprocessed memo actions")

        return MatterHealth(
            matter_id=matter_id,
            matter_name=matter.display_name,
            total_hours=round(total_hours, 1),
            days_since_activity=days_since,
            pending_tasks=pending_tasks,
            pending_memos=pending_memos,
            upcoming_deadlines=upcoming,
            status=status,
            warnings=warnings
        )

    def get_all_health(self, active_only: bool = True) -> List[MatterHealth]:
        """Get health indicators for all matters."""
        query = self.session.query(Matter)
        if active_only:
            query = query.filter(Matter.is_active == True)

        matters = query.all()
        return [self.get_health(m.id) for m in matters]


class DuplicateDetector:
    """
    Detects potential duplicate time entries.
    """

    def __init__(self, session: Session):
        self.session = session
        self._similarity_threshold = 0.8
        self._overlap_threshold_minutes = 15

    def detect_duplicates(self, target_date: date = None) -> List[PotentialDuplicate]:
        """
        Detect potential duplicate entries for a given date.
        """
        if target_date is None:
            target_date = date.today()

        start_dt = datetime.combine(target_date, time(0, 0))
        end_dt = datetime.combine(target_date + timedelta(days=1), time(0, 0))

        logs = self.session.query(WorkLog).filter(
            and_(
                WorkLog.created_at >= start_dt,
                WorkLog.created_at < end_dt
            )
        ).order_by(WorkLog.created_at).all()

        duplicates = []

        for i in range(len(logs)):
            for j in range(i + 1, len(logs)):
                log1 = logs[i]
                log2 = logs[j]

                similarity, overlap = self._calculate_similarity(log1, log2)

                if similarity >= self._similarity_threshold or overlap >= self._overlap_threshold_minutes:
                    # Check if already recorded
                    existing = self.session.query(PotentialDuplicate).filter(
                        and_(
                            PotentialDuplicate.entry1_id == log1.id,
                            PotentialDuplicate.entry2_id == log2.id
                        )
                    ).first()

                    if not existing:
                        dup = PotentialDuplicate(
                            entry1_id=log1.id,
                            entry2_id=log2.id,
                            similarity_score=similarity,
                            overlap_minutes=overlap
                        )
                        self.session.add(dup)
                        duplicates.append(dup)

        self.session.flush()
        return duplicates

    def _calculate_similarity(self, log1: WorkLog, log2: WorkLog) -> Tuple[float, int]:
        """
        Calculate similarity score and time overlap between two logs.
        """
        score = 0.0
        factors = 0

        # Same matter
        if log1.matter_id and log1.matter_id == log2.matter_id:
            score += 0.4
        factors += 0.4

        # Same activity type
        if log1.activity_type_id and log1.activity_type_id == log2.activity_type_id:
            score += 0.3
        factors += 0.3

        # Similar narrative
        if log1.narrative and log2.narrative:
            # Simple word overlap
            words1 = set(log1.narrative.lower().split())
            words2 = set(log2.narrative.lower().split())
            if words1 and words2:
                overlap = len(words1 & words2) / len(words1 | words2)
                score += 0.3 * overlap
        factors += 0.3

        similarity = score / factors if factors > 0 else 0

        # Calculate time overlap
        overlap_minutes = 0

        start1 = log1.started_at or log1.created_at
        start2 = log2.started_at or log2.created_at

        end1 = start1 + timedelta(hours=log1.duration_hours)
        end2 = start2 + timedelta(hours=log2.duration_hours)

        overlap_start = max(start1, start2)
        overlap_end = min(end1, end2)

        if overlap_end > overlap_start:
            overlap_minutes = int((overlap_end - overlap_start).total_seconds() / 60)

        return similarity, overlap_minutes

    def merge_duplicates(self, dup_id: str) -> Tuple[bool, str]:
        """Merge two duplicate entries into one."""
        dup = self.session.query(PotentialDuplicate).get(dup_id)
        if not dup:
            return False, "Duplicate record not found"

        log1 = dup.entry1
        log2 = dup.entry2

        # Keep the earlier one, combine durations
        keep = log1 if log1.created_at < log2.created_at else log2
        remove = log2 if keep == log1 else log1

        keep.duration_hours += remove.duration_hours

        # Combine narratives
        if keep.narrative and remove.narrative and keep.narrative != remove.narrative:
            keep.narrative = f"{keep.narrative}; {remove.narrative}"
        elif remove.narrative and not keep.narrative:
            keep.narrative = remove.narrative

        # Delete the duplicate
        self.session.delete(remove)

        dup.status = "merged"
        dup.resolved_at = datetime.now()

        self.session.commit()
        return True, f"Merged entries. Total: {keep.duration_hours}h"
