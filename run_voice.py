#!/usr/bin/env python3
"""
Voice Time Recording System - Voice Mode with Hotkey

Press and hold a key to record voice input, release to process.

Default keys:
  - F13: Push-to-talk (hold to record)
  - Ctrl+Shift+T: Toggle recording on/off
  - Ctrl+Shift+Space: Alternative push-to-talk

NO WAKE WORD - Uses hotkey activation only.
"""
import sys
import signal
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich.table import Table
from rich import box

# Add voice_time to path
sys.path.insert(0, str(Path(__file__).parent))

from voice_time.config import Config
from voice_time.database.schema import init_db
from voice_time.database.queries import get_active_matters
from voice_time.llm.client import OllamaClient
from voice_time.core.state_machine import DayState
from voice_time.voice.hotkey import create_push_to_talk


def main():
    """Run voice-activated time recording with hotkey."""
    console = Console()
    
    # Load config
    config = Config.load()
    
    # Show welcome
    console.print(Panel.fit(
        "[bold blue]Voice Time Recording System - Voice Mode[/bold blue]\n\n"
        "[green]Hotkey Activation:[/green]\n"
        "  • Press and hold [bold]Ctrl+Space[/bold] to record (push-to-talk)\n"
        "  • Or press [bold]Ctrl+Shift+T[/bold] to toggle recording\n\n"
        "[yellow]NO wake word - use hotkey to activate[/yellow]\n\n"
        "Press [bold red]Ctrl+C[/bold red] to exit",
        border_style="blue",
        title="🎤 Voice Mode"
    ))
    
    # Initialize database
    console.print("\n[cyan]Initializing database...[/cyan]")
    db_path = config.data_dir / "voice_time.db"
    session = init_db(db_path)
    
    # Initialize LLM client
    console.print("[cyan]Connecting to Ollama...[/cyan]")
    llm_client = OllamaClient(config.ollama)
    
    # Check Ollama is available
    if not llm_client.health_check():
        console.print("[red]Error: Ollama is not running or model not available[/red]")
        console.print(f"\nPlease ensure Ollama is running and model '{config.ollama.model}' is installed:")
        console.print(f"  ollama serve")
        console.print(f"  ollama pull {config.ollama.model}")
        sys.exit(1)
    
    # Initialize state machine
    console.print("[cyan]Loading state machine...[/cyan]")
    day_state = DayState(session, llm_client, config)
    
    # Show active matters
    matters = get_active_matters(session)
    if matters:
        console.print("\n[bold]Active Matters:[/bold]")
        for matter in matters[:5]:  # Show first 5
            aliases = [a.alias for a in matter.aliases]
            console.print(f"  • {matter.display_name} - {', '.join(aliases[:2])}")
        if len(matters) > 5:
            console.print(f"  ... and {len(matters) - 5} more")
    
    console.print("\n[green]✓ Ready![/green]")
    console.print("\n[bold yellow]Listening for hotkey... Press Ctrl+Space to talk![/bold yellow]\n")
    
    # Create status display
    status_table = Table(box=box.ROUNDED, show_header=False, padding=(0, 1))
    status_table.add_column("Status", style="cyan")
    status_table.add_row("🎧 Waiting for hotkey...")
    
    # Processing state
    processing_state = {"recording": False, "processing": False}
    
    def on_transcript(text: str):
        """Handle transcribed text."""
        processing_state["processing"] = True
        
        console.print(f"\n[bold green]You said:[/bold green] {text}")
        console.print("[cyan]Processing...[/cyan]")
        
        # Process through state machine
        result = day_state.process(text)
        
        # Display result
        if result.success:
            console.print(f"[green]✓ {result.message}[/green]\n")
        else:
            console.print(f"[red]✗ {result.message}[/red]\n")
        
        if result.needs_clarification and result.clarification_question:
            console.print(f"[yellow]? {result.clarification_question}[/yellow]\n")
        
        console.print("[bold yellow]Ready for next command... (Press hotkey)[/bold yellow]\n")
        processing_state["processing"] = False
    
    # Create push-to-talk listener
    ptt = create_push_to_talk(
        on_transcript=on_transcript,
        ptt_key="<ctrl>+<space>",
        toggle_key="<ctrl>+<shift>+t"
    )
    
    # Start listening
    ptt.start()
    
    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        console.print("\n\n[yellow]Shutting down...[/yellow]")
        ptt.stop()
        console.print("[green]Goodbye![/green]\n")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Keep running
    try:
        import time
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        signal_handler(None, None)


if __name__ == "__main__":
    main()
