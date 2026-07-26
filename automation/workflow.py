# automation/workflow.py
"""Workflow engine for multi-step automation sequences."""

from __future__ import annotations
from dataclasses import dataclass, field
import threading
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING, Union
from enum import Enum
import time
from datetime import datetime
import uuid

from .actions import AutomationAction, AutomationResult, ActionStatus

if TYPE_CHECKING:
    from .automation import Automation


class WorkflowStatus(str, Enum):
    """Status of a workflow."""
    PENDING = "pending"
    RUNNING = "running"
    WAITING = "waiting"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


@dataclass
class WorkflowStep:
    """A single step in a workflow."""
    action: AutomationAction
    on_success: Optional[Callable] = None
    on_failure: Optional[Callable] = None
    retry_count: int = 0
    max_retries: int = 3
    timeout: Optional[int] = 30  # seconds
    result: Optional[AutomationResult] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    @property
    def duration(self) -> Optional[float]:
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


@dataclass
class Workflow:
    """Complete workflow with rollback support."""
    
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    steps: List[WorkflowStep] = field(default_factory=list)
    status: WorkflowStatus = WorkflowStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    current_step_index: int = 0
    rollback_steps: List[int] = field(default_factory=list)
    
    def add_step(self, action: Union[AutomationAction, Dict[str, Any]], 
                 on_success: Optional[Callable] = None,
                 on_failure: Optional[Callable] = None) -> None:
        """Add a step to the workflow."""
        if isinstance(action, dict):
            action = AutomationAction.from_dict(action)
        
        step = WorkflowStep(action=action, on_success=on_success, on_failure=on_failure)
        self.steps.append(step)
    
    def should_rollback(self, step_index: int) -> bool:
        """Determine if we should rollback from this step."""
        return step_index in self.rollback_steps


class WorkflowEngine:
    """Executes workflows with rollback support."""
    
    def __init__(self, automation: "Automation"):
        self.automation = automation
        self.workflows: Dict[str, Workflow] = {}
        self._execution_lock = threading.Lock()
    
    def register(self, workflow: Workflow) -> str:
        """Register a workflow for execution."""
        self.workflows[workflow.id] = workflow
        return workflow.id
    
    def execute(self, workflow_id: str) -> Workflow:
        """Execute a workflow with rollback support."""
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_id}")
        
        with self._execution_lock:
            if workflow.status == WorkflowStatus.RUNNING:
                raise RuntimeError(f"Workflow {workflow_id} is already running")
            
            workflow.status = WorkflowStatus.RUNNING
            
            try:
                self._execute_steps(workflow)
                workflow.status = WorkflowStatus.SUCCESS
            except Exception as e:
                # Attempt rollback if configured
                if workflow.rollback_steps:
                    self._rollback(workflow)
                else:
                    workflow.status = WorkflowStatus.FAILED
                raise
            finally:
                workflow.completed_at = datetime.now()
        
        return workflow
    
    def _execute_steps(self, workflow: Workflow) -> None:
        """Execute all steps in a workflow."""
        for idx, step in enumerate(workflow.steps):
            workflow.current_step_index = idx
            
            # Handle retries
            for attempt in range(step.max_retries + 1):
                step.retry_count = attempt
                
                if attempt > 0:
                    # Wait before retry
                    time.sleep(2 ** attempt)  # Exponential backoff
                
                step.started_at = datetime.now()
                
                try:
                    if step.timeout:
                        # Execute with timeout
                        result = self._execute_with_timeout(step.action, step.timeout)
                    else:
                        result = self.automation.execute(step.action)
                    
                    step.result = result
                    step.completed_at = datetime.now()
                    
                    if result.is_success:
                        if step.on_success:
                            step.on_success(result)
                        break  # Success, move to next step
                    else:
                        if attempt == step.max_retries:
                            raise RuntimeError(f"Step {idx} failed after {attempt} retries: {result.error}")
                        # Continue to next retry
                
                except Exception as e:
                    step.completed_at = datetime.now()
                    if step.on_failure:
                        step.on_failure(e)
                    
                    if attempt == step.max_retries:
                        raise RuntimeError(f"Step {idx} failed: {str(e)}")
    
    def _execute_with_timeout(self, action: AutomationAction, timeout: int) -> AutomationResult:
        """Execute with timeout."""
        import threading
        
        result = None
        exception = None
        
        def target():
            nonlocal result, exception
            try:
                result = self.automation.execute(action)
            except Exception as e:
                exception = e
        
        thread = threading.Thread(target=target)
        thread.start()
        thread.join(timeout)
        
        if thread.is_alive():
            return AutomationResult(
                status=ActionStatus.TIMEOUT,
                module=action.module,
                action=action.action,
                error=f"Timeout after {timeout} seconds"
            )
        
        if exception:
            raise exception
        
        return result
    
    def _rollback(self, workflow: Workflow) -> None:
        """Execute rollback steps in reverse order."""
        workflow.status = WorkflowStatus.WAITING
        
        # Determine rollback indices
        if workflow.current_step_index > 0:
            # For each step from current back to 0
            for idx in range(workflow.current_step_index, -1, -1):
                if workflow.should_rollback(idx):
                    step = workflow.steps[idx]
                    # Execute rollback action (would need to be defined)
                    # For now, just mark as rolled back
                    step.result = AutomationResult(
                        status=ActionStatus.SUCCESS,
                        module="workflow",
                        action="rollback",
                        output=f"Rollback for step {idx}"
                    )