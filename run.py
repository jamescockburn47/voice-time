#!/usr/bin/env python3
"""
TimeBrief - Entry Point

Usage:
    python run.py                 # Run web UI
    python run.py --cli           # Run CLI REPL
    python run.py --init          # Initialize database with sample data
"""
import sys
import argparse
from pathlib import Path

# Add voice_time to path
sys.path.insert(0, str(Path(__file__).parent))

from voice_time.config import Config
from voice_time.database.schema import init_db
from voice_time.database.queries import create_sample_matters, get_active_matters
from voice_time.llm.client import OllamaClient
from voice_time.core.state_machine import DayState
from voice_time.web.app import create_app


def init_database(config: Config):
    """Initialize database with sample data."""
    print("Initializing database...")
    
    db_path = config.data_dir / "voice_time.db"
    session = init_db(db_path)
    
    print(f"[OK] Database created at: {db_path}")
    
    # Create realistic sample matters
    print("\nCreating realistic sample matters...")
    from voice_time.database.sample_data import create_realistic_matters
    matters = create_realistic_matters(session)
    
    if matters:
        print(f"[OK] Created {len(matters)} sample matters:")
        for matter in matters:
            print(f"  - {matter.display_name} ({matter.matter_ref})")
    else:
        print("[OK] Sample matters already exist")
    
    print("\nDatabase initialization complete!")
    print("\nYou can now run:")
    print("  python run.py        # Start web UI")
    print("  python run.py --cli  # Start CLI")


def run_cli(config: Config):
    """Run CLI REPL for testing."""
    from rich.console import Console
    from rich.panel import Panel
    from rich import print as rprint
    
    console = Console()
    
    # Initialize database
    db_path = config.data_dir / "voice_time.db"
    session = init_db(db_path)
    
    # Initialize LLM client
    llm_client = OllamaClient(config.ollama)
    
    # Check Ollama is available
    if not llm_client.health_check():
        console.print("[red]Error: Ollama is not running or model not available[/red]")
        console.print(f"\nPlease ensure Ollama is running and model '{config.ollama.model}' is installed:")
        console.print(f"  ollama serve")
        console.print(f"  ollama pull {config.ollama.model}")
        sys.exit(1)
    
    # Initialize state machine
    day_state = DayState(session, llm_client, config)
    
    # Show welcome
    console.print(Panel.fit(
        "[bold blue]TimeBrief - CLI Mode[/bold blue]\n\n"
        "Try saying:\n"
        "  • Today I need to finish Smith disclosure and draft Brown skeleton\n"
        "  • Working on Smith disclosure\n"
        "  • Done with that\n"
        "  • What's left?\n\n"
        "Type 'quit' or 'exit' to exit",
        border_style="blue"
    ))
    
    # Show active matters
    matters = get_active_matters(session)
    if matters:
        console.print("\n[bold]Active Matters:[/bold]")
        for matter in matters:
            aliases = [a.alias for a in matter.aliases]
            console.print(f"  • {matter.display_name} - {', '.join(aliases[:2])}")
        console.print()
    
    # REPL loop
    while True:
        try:
            # Get input
            utterance = input("\n> ").strip()
            
            if not utterance:
                continue
            
            if utterance.lower() in ['quit', 'exit', 'q']:
                console.print("\n[yellow]Goodbye![/yellow]\n")
                break
            
            # Process
            result = day_state.process(utterance)
            
            # Display result
            if result.success:
                console.print(f"[green][OK] {result.message}[/green]")
            else:
                console.print(f"[red]✗ {result.message}[/red]")
            
            if result.needs_clarification and result.clarification_question:
                console.print(f"[yellow]? {result.clarification_question}[/yellow]")
        
        except KeyboardInterrupt:
            console.print("\n\n[yellow]Interrupted. Type 'quit' to exit.[/yellow]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            import traceback
            traceback.print_exc()


def run_web(config: Config):
    """Run Flask web UI."""
    print("Starting TimeBrief web server...")
    print(f"Database: {config.data_dir / 'voice_time.db'}")
    print("\nInitializing...")
    
    # Create app
    app = create_app(config)
    
    # Check Ollama is available
    if not app.day_state.plan_parser.llm.health_check():
        print("\n[WARNING] Ollama is not running or model not available")
        print(f"\nPlease ensure Ollama is running and model '{config.ollama.model}' is installed:")
        print(f"  ollama serve")
        print(f"  ollama pull {config.ollama.model}")
        print("\nContinuing anyway (some features will fail)...\n")
    
    print("\n[OK] Ready!")
    print("\nOpen your browser to: http://localhost:5000")
    print("Press Ctrl+C to stop\n")
    
    # Run Flask (debug=True for template auto-reload during development)
    app.run(debug=True, host='0.0.0.0', port=5000)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="TimeBrief - Voice-first time recording")
    parser.add_argument('--cli', action='store_true', help='Run in CLI mode')
    parser.add_argument('--init', action='store_true', help='Initialize database with sample data')
    parser.add_argument('--config', type=str, help='Path to config file', default='config.yaml')
    
    args = parser.parse_args()
    
    # Load config
    config_path = Path(args.config) if args.config else None
    config = Config.load(config_path)
    
    # Route to appropriate mode
    if args.init:
        init_database(config)
    elif args.cli:
        run_cli(config)
    else:
        run_web(config)


if __name__ == "__main__":
    main()
