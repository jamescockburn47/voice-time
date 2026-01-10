"""Realistic sample data for legal time tracking testing."""
from datetime import date, time, datetime, timedelta
from sqlalchemy.orm import Session
from .models import Matter, MatterAlias, DayPlan, PlannedTask, ActivityType


def create_realistic_matters(session: Session) -> list:
    """Create realistic legal matters across different practice areas."""
    
    realistic_matters = [
        # Litigation - Commercial
        {
            "matter_ref": "2024/CL/087",
            "display_name": "Thompson Industries Ltd v Apex Manufacturing",
            "client": "Thompson Industries Ltd",
            "aliases": ["Thompson", "Thompson v Apex", "Apex dispute", "TI matter", "manufacturing case"]
        },
        {
            "matter_ref": "2024/CL/142",
            "display_name": "R (on application of Greenfield) v Planning Authority",
            "client": "Greenfield Developments",
            "aliases": ["Greenfield", "planning JR", "Greenfield judicial review", "planning case"]
        },
        
        # Litigation - Employment
        {
            "matter_ref": "2025/EMP/023",
            "display_name": "Williams v DataTech Solutions Ltd (Unfair Dismissal)",
            "client": "Sarah Williams",
            "aliases": ["Williams", "DataTech dismissal", "Williams employment", "unfair dismissal"]
        },
        
        # Litigation - Personal Injury
        {
            "matter_ref": "2024/PI/156",
            "display_name": "Chen v London Transport Authority",
            "client": "Michael Chen",
            "aliases": ["Chen", "LTA accident", "Chen PI", "transport injury"]
        },
        
        # Family
        {
            "matter_ref": "2024/FAM/091",
            "display_name": "Patel v Patel (Divorce & Financial Remedy)",
            "client": "Anjali Patel",
            "aliases": ["Patel divorce", "Patel", "Anjali matter", "family matter"]
        },
        
        # Corporate/Commercial
        {
            "matter_ref": "2025/CORP/034",
            "display_name": "Acquisition of Digital Innovations Ltd by TechGrowth PLC",
            "client": "TechGrowth PLC",
            "aliases": ["TechGrowth", "Digital Innovations acquisition", "M&A deal", "corporate acquisition"]
        },
        {
            "matter_ref": "2024/COM/208",
            "display_name": "Shareholder Agreement - Riverside Ventures",
            "client": "Riverside Ventures",
            "aliases": ["Riverside", "shareholder agreement", "Riverside SHA", "venture deal"]
        },
        
        # Property/Real Estate
        {
            "matter_ref": "2024/PROP/134",
            "display_name": "Lease Dispute - Harbour Commercial Centre",
            "client": "Harbour Properties Ltd",
            "aliases": ["Harbour", "commercial lease", "HCC dispute", "property matter"]
        },
        
        # Criminal
        {
            "matter_ref": "2025/CRIM/017",
            "display_name": "R v Johnson (Fraud)",
            "client": "Marcus Johnson",
            "aliases": ["Johnson", "R v Johnson", "fraud case", "Johnson fraud"]
        },
        
        # Regulatory
        {
            "matter_ref": "2024/REG/045",
            "display_name": "FCA Investigation - Sterling Financial Services",
            "client": "Sterling Financial Services",
            "aliases": ["Sterling", "FCA matter", "Sterling investigation", "regulatory"]
        },
        
        # Probate/Estate
        {
            "matter_ref": "2024/PROB/078",
            "display_name": "Estate of Elizabeth Montgomery (Deceased)",
            "client": "Montgomery Estate",
            "aliases": ["Montgomery estate", "probate matter", "Elizabeth Montgomery", "estate administration"]
        },
        
        # Immigration
        {
            "matter_ref": "2025/IMM/012",
            "display_name": "Visa Application - Dr. Sharma",
            "client": "Dr. Priya Sharma",
            "aliases": ["Sharma", "visa application", "Sharma immigration", "Tier 2 visa"]
        },
    ]
    
    created = []
    for data in realistic_matters:
        # Check if already exists
        existing = session.query(Matter).filter(
            Matter.matter_ref == data["matter_ref"]
        ).first()
        
        if existing:
            continue
        
        # Create matter
        aliases_data = data.pop("aliases")
        matter = Matter(**data)
        session.add(matter)
        session.flush()
        
        # Create aliases
        for i, alias_text in enumerate(aliases_data):
            alias = MatterAlias(
                matter_id=matter.id,
                alias=alias_text,
                is_primary=(i == 0)
            )
            session.add(alias)
        
        created.append(matter)
    
    session.commit()
    return created


def create_sample_day_plan(session: Session) -> DayPlan:
    """Create a realistic sample day plan for testing."""
    
    today = date.today()
    
    # Check if plan already exists
    existing = session.query(DayPlan).filter(DayPlan.date == today).first()
    if existing:
        return existing
    
    # Create plan
    plan = DayPlan(date=today, source="demo")
    session.add(plan)
    session.flush()
    
    # Get some matters
    thompson = session.query(Matter).filter(
        Matter.display_name.like("%Thompson%")
    ).first()
    
    greenfield = session.query(Matter).filter(
        Matter.display_name.like("%Greenfield%")
    ).first()
    
    williams = session.query(Matter).filter(
        Matter.display_name.like("%Williams%")
    ).first()
    
    # Get activity types
    docrev = session.query(ActivityType).filter(ActivityType.code == "DOCREV").first()
    draft = session.query(ActivityType).filter(ActivityType.code == "DRAFT").first()
    research = session.query(ActivityType).filter(ActivityType.code == "RESEARCH").first()
    email = session.query(ActivityType).filter(ActivityType.code == "EMAIL").first()
    conf = session.query(ActivityType).filter(ActivityType.code == "CONF").first()
    
    # Create realistic tasks
    tasks = []
    
    if thompson:
        tasks.append(PlannedTask(
            day_plan_id=plan.id,
            matter_id=thompson.id,
            activity_type_id=docrev.id if docrev else None,
            title="Review witness statements from defendant",
            estimated_hours=2.0,
            sort_order=0
        ))
        
        tasks.append(PlannedTask(
            day_plan_id=plan.id,
            matter_id=thompson.id,
            activity_type_id=draft.id if draft else None,
            title="Draft amended particulars of claim",
            estimated_hours=3.0,
            sort_order=1
        ))
    
    if greenfield:
        tasks.append(PlannedTask(
            day_plan_id=plan.id,
            matter_id=greenfield.id,
            activity_type_id=research.id if research else None,
            title="Research planning law - material consideration test",
            estimated_hours=1.5,
            sort_order=2
        ))
        
        tasks.append(PlannedTask(
            day_plan_id=plan.id,
            matter_id=greenfield.id,
            activity_type_id=conf.id if conf else None,
            title="Conference with counsel re grounds of challenge",
            scheduled_time=time(15, 0),
            estimated_hours=1.0,
            sort_order=3
        ))
    
    if williams:
        tasks.append(PlannedTask(
            day_plan_id=plan.id,
            matter_id=williams.id,
            activity_type_id=email.id if email else None,
            title="Correspondence with opponent re disclosure",
            estimated_hours=0.5,
            sort_order=4
        ))
    
    for task in tasks:
        session.add(task)
    
    session.commit()
    return plan


# Tutorial scenarios
TUTORIAL_SCENARIOS = {
    "morning_planning": {
        "title": "Morning Planning",
        "description": "Start your day by planning what you'll work on",
        "examples": [
            "Today I need to review the Thompson witness statements, draft the Greenfield skeleton, and I've got a conference at 3",
            "Working on Thompson and Greenfield today, plus emails",
            "Need to finish the Williams correspondence and research planning law for Greenfield"
        ]
    },
    "starting_work": {
        "title": "Starting Work",
        "description": "Tell the system when you start a task",
        "examples": [
            "Working on Thompson witness statements",
            "Starting the Greenfield research",
            "Beginning Williams emails"
        ]
    },
    "completing_task": {
        "title": "Completing a Task",
        "description": "When done, the system logs the time automatically",
        "examples": [
            "Done with the Thompson witnesses",
            "Finished the research",
            "Completed that",
            "Done - took about 2 hours"
        ]
    },
    "interruptions": {
        "title": "Handling Interruptions",
        "description": "Seamlessly switch between tasks without losing context",
        "examples": [
            "Quick call about Williams",
            "Back to what I was doing",
            "Brief email to Thompson client then back to drafting"
        ]
    },
    "historical_logging": {
        "title": "Historical Logging",
        "description": "Log time for work already completed",
        "examples": [
            "Spent a couple of hours on Thompson this morning",
            "Did about 30 minutes of Williams emails earlier",
            "Was on the Greenfield conference for an hour"
        ]
    },
    "natural_duration": {
        "title": "Natural Duration Language",
        "description": "Use natural phrases for time",
        "examples": [
            "Quick 10 minute call",
            "Couple of hours on drafting",
            "All morning on the disclosure",
            "Since lunch I've been researching",
            "About an hour and a half"
        ]
    }
}
