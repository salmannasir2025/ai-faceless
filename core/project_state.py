"""
Project State Manager - Single source of truth for the pipeline
"""
import json
import os
import portalocker
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path


class ProjectState:
    """
    Manages the project state in a JSON file.
    Acts as the single source of truth for the pipeline.
    Allows stateless agents and prevents data loss on restart.
    """
    
    def __init__(self, project_id: str, state_file: str = None):
        self.project_id = project_id
        self.state_file = state_file or f"output/{project_id}_state.json"
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(self.state_file) or "output", exist_ok=True)
        
        # Initialize or load state
        if os.path.exists(self.state_file):
            self.load()
        else:
            self._init_new()
    
    def _init_new(self):
        """Initialize a new project state."""
        self.state = {
            "project_id": self.project_id,
            "status": "idle",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "hardware_profile": "UNKNOWN",
            "agents": {},
            "metadata": {},
            "errors": [],
            "current_agent": None
        }
        self.save()
    
    def load(self):
        """Load state from file."""
        try:
            with open(self.state_file, 'r') as f:
                self.state = json.load(f)
        except (json.JSONDecodeError, IOError):
            self._init_new()
    
    def save(self):
        """Save state to file with locking."""
        self.state["updated_at"] = datetime.now().isoformat()
        
        try:
            # Use portalocker for safe file access
            with portalocker.Lock(self.state_file, timeout=1, mode='w') as f:
                json.dump(self.state, f, indent=2)
        except portalocker.exceptions.LockException:
            print(f"⚠️ Could not lock {self.state_file}, retrying...")
            # Fallback: try again with basic file operations
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
    
    # === Status Management ===
    
    def set_status(self, status: str):
        """Set overall project status."""
        self.state["status"] = status
        self.save()
    
    def set_hardware_profile(self, profile: str):
        """Set hardware profile."""
        self.state["hardware_profile"] = profile
        self.save()
    
    def set_metadata(self, key: str, value: Any):
        """Set metadata key-value."""
        self.state["metadata"][key] = value
        self.save()
    
    def add_error(self, error: str):
        """Add an error message."""
        self.state["errors"].append({
            "timestamp": datetime.now().isoformat(),
            "error": error
        })
        self.save()
    
    # === Agent Management ===
    
    def register_agent(self, agent_name: str):
        """Register a new agent in the state."""
        if "agents" not in self.state:
            self.state["agents"] = {}
        
        self.state["agents"][agent_name] = {
            "status": "registered",
            "started_at": None,
            "completed_at": None,
            "output": None,
            "metadata": {}
        }
        self.save()
    
    def set_agent_status(self, agent_name: str, status: str, metadata: dict = None):
        """Update agent status."""
        if agent_name not in self.state["agents"]:
            self.register_agent(agent_name)
        
        agent_state = self.state["agents"][agent_name]
        old_status = agent_state.get("status")
        agent_state["status"] = status
        
        if status == "in_progress" and not agent_state.get("started_at"):
            agent_state["started_at"] = datetime.now().isoformat()
        elif status in ["completed", "failed"] and not agent_state.get("completed_at"):
            agent_state["completed_at"] = datetime.now().isoformat()
        
        if metadata:
            agent_state["metadata"].update(metadata)
        
        # Update current agent
        if status == "in_progress":
            self.state["current_agent"] = agent_name
        
        self.save()
    
    def set_agent_output(self, agent_name: str, output: Any):
        """Set agent output data."""
        if agent_name not in self.state["agents"]:
            self.register_agent(agent_name)
        
        self.state["agents"][agent_name]["output"] = output
        self.save()
    
    def get_agent_status(self, agent_name: str) -> Optional[str]:
        """Get agent status."""
        return self.state.get("agents", {}).get(agent_name, {}).get("status")
    
    def get_agent_output(self, agent_name: str) -> Any:
        """Get agent output."""
        return self.state.get("agents", {}).get(agent_name, {}).get("output")
    
    def get_current_agent(self) -> Optional[str]:
        """Get the currently running agent."""
        return self.state.get("current_agent")
    
    # === Query Methods ===
    
    def is_complete(self) -> bool:
        """Check if project is complete."""
        return self.state.get("status") == "completed"
    
    def has_errors(self) -> bool:
        """Check if project has errors."""
        return len(self.state.get("errors", [])) > 0
    
    def get_summary(self) -> dict:
        """Get a summary of the project state."""
        agents = self.state.get("agents", {})
        completed = sum(1 for a in agents.values() if a.get("status") == "completed")
        in_progress = sum(1 for a in agents.values() if a.get("status") == "in_progress")
        
        return {
            "project_id": self.project_id,
            "status": self.state.get("status"),
            "agents_total": len(agents),
            "agents_completed": completed,
            "agents_in_progress": in_progress,
            "current_agent": self.state.get("current_agent"),
            "errors": len(self.state.get("errors", []))
        }
    
    def get_all(self) -> dict:
        """Get full state."""
        return self.state.copy()
    
    def reset(self):
        """Reset the project state."""
        self._init_new()


# Default state file for quick access
DEFAULT_STATE = "project_state.json"


def get_state(project_id: str = "default", state_file: str = None) -> ProjectState:
    """Get or create a project state."""
    if state_file is None:
        state_file = DEFAULT_STATE
    return ProjectState(project_id, state_file)


if __name__ == "__main__":
    # Test
    state = get_state("test_project")
    state.set_metadata("target_duration", 60)
    state.set_metadata("language", "Urdu")
    state.register_agent("scout")
    state.set_agent_status("scout", "in_progress")
    state.set_agent_status("scout", "completed", {"sources_found": 5})
    
    print(json.dumps(state.get_all(), indent=2))