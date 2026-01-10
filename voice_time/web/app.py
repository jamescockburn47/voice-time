"""Flask application for web UI."""
from flask import Flask, render_template, request, jsonify
from pathlib import Path
from ..config import Config
from ..database.schema import init_db
from ..llm.client import OllamaClient
from ..core.state_machine import DayState


def create_app(config: Config = None) -> Flask:
    """Create and configure Flask app."""
    if config is None:
        config = Config.load()
    
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'dev-secret-key-change-in-production'
    app.config['TEMPLATES_AUTO_RELOAD'] = True  # Auto-reload templates during development
    
    # Initialize database
    db_path = config.data_dir / "voice_time.db"
    session = init_db(db_path)
    
    # Initialize LLM client
    llm_client = OllamaClient(config.ollama)
    
    # Initialize state machine
    day_state = DayState(session, llm_client, config)
    
    # Store in app context
    app.session = session
    app.day_state = day_state
    app.config_obj = config
    app.transcriber = None  # Lazy-loaded on first use
    
    # Register routes
    from . import routes
    routes.register_routes(app)
    
    return app
