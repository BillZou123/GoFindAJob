"""
Simple in-memory status tracker for autofill tasks
Tracks the progress of LinkedIn autofill operations
"""
from typing import Dict, Optional
import uuid
from datetime import datetime
import threading

# Thread-safe status storage
_status_lock = threading.Lock()
_tasks: Dict[str, Dict] = {}


def create_task(job_url: str, user_id: int) -> str:
    """
    Create a new autofill task and return its ID
    
    Args:
        job_url: The LinkedIn job URL being applied to
        user_id: The user ID initiating the task
    
    Returns:
        task_id: Unique task identifier
    """
    task_id = str(uuid.uuid4())
    
    with _status_lock:
        _tasks[task_id] = {
            "task_id": task_id,
            "job_url": job_url,
            "user_id": user_id,
            "status": "initializing",
            "current_step": "setup",
            "message": "Initializing autofill process...",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "progress": 0
        }
    
    return task_id


def update_task_status(task_id: str, step: str, message: str, progress: int = None):
    """
    Update the status of a running task
    
    Args:
        task_id: Task identifier
        step: Current step (e.g., "setup", "navigate", "login", "fill_form", "success", "error")
        message: Human-readable message describing current status
        progress: Progress percentage (0-100)
    """
    with _status_lock:
        if task_id in _tasks:
            _tasks[task_id]["current_step"] = step
            _tasks[task_id]["message"] = message
            _tasks[task_id]["updated_at"] = datetime.utcnow().isoformat()
            
            # Determine overall status from step
            if step == "error":
                _tasks[task_id]["status"] = "failed"
            elif step == "success":
                _tasks[task_id]["status"] = "completed"
            elif step == "pausing":
                _tasks[task_id]["status"] = "completed"
            else:
                _tasks[task_id]["status"] = "in_progress"
            
            if progress is not None:
                _tasks[task_id]["progress"] = progress


def get_task_status(task_id: str) -> Optional[Dict]:
    """
    Get the current status of a task
    
    Args:
        task_id: Task identifier
    
    Returns:
        Task status dict or None if not found
    """
    with _status_lock:
        if task_id in _tasks:
            return _tasks[task_id].copy()
    
    return None


def cleanup_old_tasks(older_than_hours: int = 24):
    """
    Clean up old completed tasks (optional maintenance)
    
    Args:
        older_than_hours: Remove tasks older than this many hours
    """
    from datetime import timedelta
    
    with _status_lock:
        now = datetime.utcnow()
        cutoff = now - timedelta(hours=older_than_hours)
        
        tasks_to_delete = []
        for task_id, task in _tasks.items():
            if task["status"] in ["completed", "failed"]:
                created = datetime.fromisoformat(task["created_at"])
                if created < cutoff:
                    tasks_to_delete.append(task_id)
        
        for task_id in tasks_to_delete:
            del _tasks[task_id]
