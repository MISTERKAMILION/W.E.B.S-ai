"""Structured logging for automation actions.

Provides comprehensive logging of all automation operations to both
human-readable logs and structured JSON logs for analysis.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class AutomationLogger:
    """Structured logger for automation actions and results."""

    def __init__(self, log_dir: str = "logs/automation"):
        """Initialize the logger.

        Args:
            log_dir: Directory to store log files.
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Setup structured logger
        self.logger = logging.getLogger("automation")
        self.logger.setLevel(logging.INFO)

        # Remove existing handlers to avoid duplicates
        self.logger.handlers = []

        # Human-readable log handler
        log_file = self.log_dir / f"automation_{datetime.now().strftime('%Y%m%d')}.log"
        handler = logging.FileHandler(log_file)
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
        self.logger.addHandler(handler)

    def log_action(self, action: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Log an action and its result.

        Args:
            action: Action dictionary from AutomationAction.to_dict()
            result: Result dictionary from AutomationResult.to_dict()
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action_id": action.get("id", "unknown"),
            "action": action,
            "result": result,
        }

        # Write to structured JSON log
        json_log_file = (
            self.log_dir / f"actions_{datetime.now().strftime('%Y%m%d')}.jsonl"
        )
        try:
            with open(json_log_file, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            self.logger.error(f"Failed to write JSON log: {e}")

        # Write to human-readable log
        action_id = action.get("id", "???")
        module = action.get("module", "?")
        action_name = action.get("action", "?")
        status = result.get("status", "unknown")
        execution_time = result.get("execution_time", 0)
        error = result.get("error")

        if status == "success":
            self.logger.info(
                f"{action_id} - SUCCESS - {module}.{action_name} ({execution_time:.3f}s)"
            )
        elif status == "failure":
            self.logger.error(
                f"{action_id} - FAILURE - {module}.{action_name} - {error}"
            )
        elif status == "timeout":
            self.logger.warning(
                f"{action_id} - TIMEOUT - {module}.{action_name}"
            )
        else:
            self.logger.info(
                f"{action_id} - {status.upper()} - {module}.{action_name}"
            )

    def get_stats(self) -> Dict[str, Any]:
        """Get execution statistics for today.

        Returns:
            Dictionary with stats about executed actions.
        """
        stats = {
            "total": 0,
            "success": 0,
            "failure": 0,
            "timeout": 0,
            "avg_execution_time": 0.0,
            "modules": {},
            "actions_by_type": {},
            "total_execution_time": 0.0,
        }

        json_log_file = (
            self.log_dir / f"actions_{datetime.now().strftime('%Y%m%d')}.jsonl"
        )

        if not json_log_file.exists():
            return stats

        try:
            with open(json_log_file) as f:
                for line in f:
                    if line.strip():
                        try:
                            entry = json.loads(line)
                            result = entry.get("result", {})
                            action = entry.get("action", {})

                            stats["total"] += 1

                            # Status stats
                            status = result.get("status")
                            if status == "success":
                                stats["success"] += 1
                            elif status == "failure":
                                stats["failure"] += 1
                            elif status == "timeout":
                                stats["timeout"] += 1

                            # Module stats
                            module = result.get("module", "unknown")
                            stats["modules"][module] = (
                                stats["modules"].get(module, 0) + 1
                            )

                            # Action type stats
                            action_type = f"{result.get('module')}.{result.get('action')}"
                            stats["actions_by_type"][action_type] = (
                                stats["actions_by_type"].get(action_type, 0) + 1
                            )

                            # Execution time
                            exec_time = result.get("execution_time", 0)
                            stats["total_execution_time"] += exec_time

                        except json.JSONDecodeError:
                            pass
        except Exception as e:
            self.logger.error(f"Failed to read stats: {e}")

        # Calculate average
        if stats["total"] > 0:
            stats["avg_execution_time"] = round(
                stats["total_execution_time"] / stats["total"], 3
            )

        return stats

    def get_recent_actions(self, limit: int = 10) -> list:
        """Get most recent actions.

        Args:
            limit: Maximum number of actions to return.

        Returns:
            List of action dictionaries.
        """
        json_log_file = (
            self.log_dir / f"actions_{datetime.now().strftime('%Y%m%d')}.jsonl"
        )

        actions = []
        if not json_log_file.exists():
            return actions

        try:
            with open(json_log_file) as f:
                lines = f.readlines()
                # Get last N lines
                for line in lines[-limit:]:
                    if line.strip():
                        try:
                            entry = json.loads(line)
                            actions.append(entry)
                        except json.JSONDecodeError:
                            pass
        except Exception as e:
            self.logger.error(f"Failed to read recent actions: {e}")

        return actions

    def clear_logs(self, older_than_days: int = 7) -> int:
        """Clear old log files.

        Args:
            older_than_days: Delete logs older than this many days.

        Returns:
            Number of files deleted.
        """
        cutoff = datetime.now().timestamp() - (older_than_days * 86400)
        deleted = 0

        try:
            for log_file in self.log_dir.glob("*.log"):
                if log_file.stat().st_mtime < cutoff:
                    log_file.unlink()
                    deleted += 1

            for json_file in self.log_dir.glob("*.jsonl"):
                if json_file.stat().st_mtime < cutoff:
                    json_file.unlink()
                    deleted += 1
        except Exception as e:
            self.logger.error(f"Failed to clear old logs: {e}")

        return deleted
