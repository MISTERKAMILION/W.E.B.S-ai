# automation/automation.py (additions)
from ctypes import Union
from datetime import datetime
from typing import Any, Dict

from automation.actions import AutomationAction, AutomationResult

from .state import StateManager, AutomationState
from .workflow import WorkflowEngine, Workflow
from .validator import CommandValidator

class Automation:
    def __init__(self):
        # ... existing initialization ...
        
        # New components
        self.state = StateManager()
        self.workflow_engine = WorkflowEngine(self)
        self.validator = CommandValidator()
    
    def execute(self, action: Union[AutomationAction, Dict[str, Any]]) -> AutomationResult:
        """Execute with state management and validation."""
        if isinstance(action, dict):
            action = AutomationAction.from_dict(action)
        
        # Update state
        self.state.begin_action(action.module, action.action)
        
        try:
            # Validate terminal commands
            if action.module == "terminal" and action.action == "run":
                command = action.params.get("command", "")
                if command:
                    self.validator.validate(command)
                    warnings = self.validator.get_last_warnings()
                    if warnings:
                        # Log warnings but continue
                        self.state.message = f"Warning: {', '.join(warnings)}"
            
            # Execute
            started_at = datetime.now()
            result = self._execute_internal(action)
            result.started_at = started_at
            result.completed_at = datetime.now()
            result.execution_time = (result.completed_at - started_at).total_seconds()
            
            # Update state
            self.state.complete_action(f"Completed {action.module}.{action.action}")
            
            # Log
            self.logger.log_action(action.to_dict(), result.to_dict())
            
            return result
            
        except Exception as e:
            self.state.update(
                AutomationState.FAILED,
                message=f"Failed: {str(e)}"
            )
            raise