"""Database setup and seed data."""
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from .models import Base, ActivityType, ActivityVocabulary


def init_db(db_path: Path) -> Session:
    """Initialize database and return session."""
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    # Seed activity types if empty
    if session.query(ActivityType).count() == 0:
        seed_activity_types(session)
    
    return session


def seed_activity_types(session: Session):
    """Seed default activity types and vocabulary."""
    
    activities = [
        {
            "code": "DOCREV",
            "label": "Document Review",
            "is_billable": True,
            "display_order": 1,
            "vocabulary": [
                "reviewing", "reading", "going through", "analysing", "analysis",
                "disclosure", "bundle", "documents", "exhibits", "evidence",
                "witness statement", "pleading", "perusing", "considering"
            ]
        },
        {
            "code": "DRAFT",
            "label": "Drafting",
            "is_billable": True,
            "display_order": 2,
            "vocabulary": [
                "drafting", "writing", "preparing", "amending", "revising",
                "skeleton", "statement", "letter", "application", "particulars",
                "defence", "reply", "submissions", "redrafting"
            ]
        },
        {
            "code": "RESEARCH",
            "label": "Legal Research",
            "is_billable": True,
            "display_order": 3,
            "vocabulary": [
                "researching", "looking into", "checking", "authorities",
                "case law", "legislation", "limitation", "law on", "investigating"
            ]
        },
        {
            "code": "CALL",
            "label": "Telephone",
            "is_billable": True,
            "display_order": 4,
            "vocabulary": [
                "call", "phone", "telephone", "spoke to", "speaking with",
                "rang", "called"
            ]
        },
        {
            "code": "CONF",
            "label": "Meeting/Conference",
            "is_billable": True,
            "display_order": 5,
            "vocabulary": [
                "meeting", "conference", "attendance", "with counsel",
                "con", "chambers", "teams", "zoom", "video call"
            ]
        },
        {
            "code": "EMAIL",
            "label": "Correspondence",
            "is_billable": True,
            "display_order": 6,
            "vocabulary": [
                "email", "emailing", "correspondence", "letter",
                "responding to", "reply to", "chasing", "writing to"
            ]
        },
        {
            "code": "COURT",
            "label": "Court/Hearing",
            "is_billable": True,
            "display_order": 7,
            "vocabulary": [
                "court", "hearing", "trial", "CMC", "PTR", "application",
                "before the judge", "master", "tribunal"
            ]
        },
        {
            "code": "TRAVEL",
            "label": "Travel",
            "is_billable": True,
            "display_order": 8,
            "vocabulary": [
                "travelling", "travel", "train", "heading to", "journey",
                "commuting"
            ]
        },
        {
            "code": "ADMIN",
            "label": "Administration",
            "is_billable": False,
            "display_order": 9,
            "vocabulary": [
                "admin", "internal", "billing", "file review", "housekeeping",
                "filing", "organising"
            ]
        },
    ]
    
    for activity_data in activities:
        vocab_phrases = activity_data.pop("vocabulary")
        activity = ActivityType(**activity_data)
        session.add(activity)
        session.flush()  # Get the ID
        
        for phrase in vocab_phrases:
            vocab = ActivityVocabulary(
                activity_type_id=activity.id,
                phrase=phrase
            )
            session.add(vocab)
    
    session.commit()
