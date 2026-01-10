"""Common database queries and utilities."""
from sqlalchemy.orm import Session
from .models import Matter, MatterAlias


def create_sample_matters(session: Session):
    """Create sample matters for testing."""
    
    matters_data = [
        {
            "matter_ref": "2024/001",
            "display_name": "Smith v Jones",
            "client": "Smith",
            "aliases": ["Smith", "SvJ", "Smith disclosure", "Smith matter"]
        },
        {
            "matter_ref": "2024/002",
            "display_name": "Brown v Welsh",
            "client": "Brown",
            "aliases": ["Brown", "BvW", "Brown skeleton", "Brown case"]
        },
        {
            "matter_ref": "2024/003",
            "display_name": "Acme Corp Ltd",
            "client": "Acme Corporation",
            "aliases": ["Acme", "Acme Corp", "corporate matter"]
        },
        {
            "matter_ref": "2024/004",
            "display_name": "R v Johnson",
            "client": "Johnson",
            "aliases": ["Johnson", "R v J", "criminal matter"]
        }
    ]
    
    created = []
    for data in matters_data:
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


def get_active_matters(session: Session):
    """Get all active matters."""
    return session.query(Matter).filter(Matter.is_active == True).all()
