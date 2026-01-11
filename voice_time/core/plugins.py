"""
Plugin Architecture for TimeBrief.

Allows extensions without modifying core code.
Plugins can hook into events like:
- Timer start/stop
- Entry creation
- Gap detection
- Export
"""
import importlib
import importlib.util
import logging
from pathlib import Path
from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class PluginInfo:
    """Information about a loaded plugin."""
    name: str
    version: str
    description: str
    author: str
    enabled: bool = True


class PluginEvent:
    """Events that plugins can hook into."""
    TIMER_START = "timer_start"
    TIMER_STOP = "timer_stop"
    TIMER_PAUSE = "timer_pause"
    TIMER_RESUME = "timer_resume"

    ENTRY_CREATED = "entry_created"
    ENTRY_UPDATED = "entry_updated"
    ENTRY_DELETED = "entry_deleted"

    GAP_DETECTED = "gap_detected"
    DUPLICATE_DETECTED = "duplicate_detected"

    MATTER_CREATED = "matter_created"
    MATTER_UPDATED = "matter_updated"

    TASK_CREATED = "task_created"
    TASK_COMPLETED = "task_completed"

    MEMO_CREATED = "memo_created"
    ACTION_CREATED = "action_created"

    EXPORT_STARTED = "export_started"
    EXPORT_COMPLETED = "export_completed"

    APP_STARTUP = "app_startup"
    APP_SHUTDOWN = "app_shutdown"

    CONVERSATION_MESSAGE = "conversation_message"


class PluginRegistry:
    """
    Central registry for plugins and event hooks.
    """

    def __init__(self):
        self._plugins: Dict[str, PluginInfo] = {}
        self._hooks: Dict[str, List[Callable]] = {}
        self._plugin_instances: Dict[str, Any] = {}

    def register(
        self,
        name: str,
        version: str = "1.0.0",
        description: str = "",
        author: str = ""
    ) -> Callable:
        """
        Decorator to register a plugin class.

        Usage:
            @plugin_registry.register("my_plugin", "1.0", "Description")
            class MyPlugin:
                def on_timer_start(self, timer_data):
                    ...
        """
        def decorator(cls):
            self._plugins[name] = PluginInfo(
                name=name,
                version=version,
                description=description,
                author=author
            )

            # Instantiate the plugin
            try:
                instance = cls()
                self._plugin_instances[name] = instance

                # Auto-register event handlers
                self._auto_register_handlers(name, instance)

                logger.info(f"Plugin registered: {name} v{version}")
            except Exception as e:
                logger.error(f"Failed to instantiate plugin {name}: {e}")
                self._plugins[name].enabled = False

            return cls

        return decorator

    def _auto_register_handlers(self, plugin_name: str, instance: Any) -> None:
        """Auto-register methods that match event names."""
        event_methods = {
            "on_timer_start": PluginEvent.TIMER_START,
            "on_timer_stop": PluginEvent.TIMER_STOP,
            "on_timer_pause": PluginEvent.TIMER_PAUSE,
            "on_timer_resume": PluginEvent.TIMER_RESUME,
            "on_entry_created": PluginEvent.ENTRY_CREATED,
            "on_entry_updated": PluginEvent.ENTRY_UPDATED,
            "on_entry_deleted": PluginEvent.ENTRY_DELETED,
            "on_gap_detected": PluginEvent.GAP_DETECTED,
            "on_duplicate_detected": PluginEvent.DUPLICATE_DETECTED,
            "on_matter_created": PluginEvent.MATTER_CREATED,
            "on_task_created": PluginEvent.TASK_CREATED,
            "on_task_completed": PluginEvent.TASK_COMPLETED,
            "on_memo_created": PluginEvent.MEMO_CREATED,
            "on_action_created": PluginEvent.ACTION_CREATED,
            "on_export_started": PluginEvent.EXPORT_STARTED,
            "on_export_completed": PluginEvent.EXPORT_COMPLETED,
            "on_app_startup": PluginEvent.APP_STARTUP,
            "on_app_shutdown": PluginEvent.APP_SHUTDOWN,
            "on_conversation_message": PluginEvent.CONVERSATION_MESSAGE,
        }

        for method_name, event in event_methods.items():
            if hasattr(instance, method_name) and callable(getattr(instance, method_name)):
                self.hook(event)(getattr(instance, method_name))

    def hook(self, event: str) -> Callable:
        """
        Decorator to register a function as an event hook.

        Usage:
            @plugin_registry.hook(PluginEvent.TIMER_START)
            def my_handler(event_data):
                ...
        """
        def decorator(func: Callable) -> Callable:
            if event not in self._hooks:
                self._hooks[event] = []
            self._hooks[event].append(func)
            return func
        return decorator

    def emit(self, event: str, data: Dict[str, Any] = None) -> List[Any]:
        """
        Emit an event to all registered hooks.
        Returns list of results from all handlers.
        """
        if event not in self._hooks:
            return []

        results = []
        event_data = {
            "event": event,
            "timestamp": datetime.now().isoformat(),
            "data": data or {}
        }

        for handler in self._hooks[event]:
            try:
                result = handler(event_data)
                results.append(result)
            except Exception as e:
                logger.error(f"Plugin handler error for {event}: {e}")

        return results

    def load_plugin_file(self, path: Path) -> bool:
        """Load a plugin from a Python file."""
        try:
            spec = importlib.util.spec_from_file_location(path.stem, path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                return True
        except Exception as e:
            logger.error(f"Failed to load plugin {path}: {e}")
        return False

    def load_plugins_directory(self, directory: Path) -> int:
        """Load all plugins from a directory."""
        if not directory.exists():
            return 0

        loaded = 0
        for path in directory.glob("*.py"):
            if path.name.startswith("_"):
                continue
            if self.load_plugin_file(path):
                loaded += 1

        return loaded

    def get_plugins(self) -> List[PluginInfo]:
        """Get list of all registered plugins."""
        return list(self._plugins.values())

    def enable_plugin(self, name: str) -> bool:
        """Enable a plugin."""
        if name in self._plugins:
            self._plugins[name].enabled = True
            return True
        return False

    def disable_plugin(self, name: str) -> bool:
        """Disable a plugin."""
        if name in self._plugins:
            self._plugins[name].enabled = False
            return True
        return False

    def get_plugin_instance(self, name: str) -> Optional[Any]:
        """Get a plugin instance by name."""
        return self._plugin_instances.get(name)


# Global plugin registry
plugin_registry = PluginRegistry()


# Convenience decorators
def plugin(name: str, version: str = "1.0.0", description: str = "", author: str = ""):
    """Decorator to register a plugin class."""
    return plugin_registry.register(name, version, description, author)


def hook(event: str):
    """Decorator to register an event hook."""
    return plugin_registry.hook(event)


# ==================== Example Built-in Plugins ====================

@plugin("activity_logger", "1.0.0", "Logs all activities for debugging", "TimeBrief")
class ActivityLoggerPlugin:
    """Example plugin that logs all events."""

    def __init__(self):
        self.log_file = None

    def on_timer_start(self, event_data: Dict):
        logger.debug(f"Timer started: {event_data['data']}")

    def on_timer_stop(self, event_data: Dict):
        logger.debug(f"Timer stopped: {event_data['data']}")

    def on_entry_created(self, event_data: Dict):
        logger.debug(f"Entry created: {event_data['data']}")

    def on_gap_detected(self, event_data: Dict):
        logger.info(f"Gap detected: {event_data['data']}")


@plugin("daily_summary", "1.0.0", "Generates end-of-day summary", "TimeBrief")
class DailySummaryPlugin:
    """Plugin that can generate daily summaries."""

    def __init__(self):
        self._today_entries = []

    def on_entry_created(self, event_data: Dict):
        self._today_entries.append(event_data['data'])

    def on_app_shutdown(self, event_data: Dict):
        if self._today_entries:
            total = sum(e.get('duration_hours', 0) for e in self._today_entries)
            logger.info(f"Daily summary: {len(self._today_entries)} entries, {total:.1f}h total")


@plugin("sound_feedback", "1.0.0", "Plays sounds on events", "TimeBrief")
class SoundFeedbackPlugin:
    """Plugin for audio feedback on events."""

    def __init__(self):
        self.enabled = True
        self._sounds = {
            PluginEvent.TIMER_START: "timer_start.wav",
            PluginEvent.TIMER_STOP: "timer_stop.wav",
            PluginEvent.ENTRY_CREATED: "success.wav",
            PluginEvent.GAP_DETECTED: "alert.wav"
        }

    def on_timer_start(self, event_data: Dict):
        if self.enabled:
            self._play_sound("timer_start")

    def on_timer_stop(self, event_data: Dict):
        if self.enabled:
            self._play_sound("timer_stop")

    def on_entry_created(self, event_data: Dict):
        if self.enabled:
            self._play_sound("success")

    def _play_sound(self, sound_name: str):
        """Play a sound (stub - implement with actual audio library)."""
        # In real implementation, use winsound on Windows or similar
        logger.debug(f"Would play sound: {sound_name}")
