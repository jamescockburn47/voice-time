"""Task stack for handling interruptions."""
from typing import Optional, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class TaskContext:
    """Context for a task that can be pushed/popped from stack."""
    matter_id: Optional[str]
    activity_type_id: Optional[str]
    planned_task_id: Optional[str]
    started_at: datetime
    description: str


class TaskStack:
    """
    Stack for managing interrupted tasks.
    
    When a user says "quick call about Brown" while working on Smith,
    we push Smith onto the stack and switch to Brown. When they say
    "back to what I was doing", we pop Smith from the stack.
    """
    
    def __init__(self):
        self._stack: list[TaskContext] = []
    
    def push(self, context: TaskContext):
        """Push current task context onto stack."""
        self._stack.append(context)
    
    def pop(self) -> Optional[TaskContext]:
        """Pop and return most recent task context."""
        if self._stack:
            return self._stack.pop()
        return None
    
    def peek(self) -> Optional[TaskContext]:
        """Peek at most recent task without popping."""
        if self._stack:
            return self._stack[-1]
        return None
    
    def clear(self):
        """Clear the entire stack."""
        self._stack.clear()
    
    def is_empty(self) -> bool:
        """Check if stack is empty."""
        return len(self._stack) == 0
    
    def size(self) -> int:
        """Get number of items on stack."""
        return len(self._stack)
    
    def get_all(self) -> list[TaskContext]:
        """Get all items on stack (for display purposes)."""
        return self._stack.copy()
