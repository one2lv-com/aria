"""
Build Lobby - Multi-Agent Communication System for ARIA Build Process
Allows multiple AI agents to coordinate, share state, and chat during builds.
"""

import json
import time
import threading
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import fcntl


class AgentRole(Enum):
    ORCHESTRATOR = "orchestrator"
    BUILDER = "builder"
    WATCHER = "watcher"
    REVIEWER = "reviewer"
    TESTER = "tester"


class MessageType(Enum):
    HANDOFF = "handoff"
    STATUS = "status"
    ERROR = "error"
    WARNING = "warning"
    CHAT = "chat"
    COMMAND = "command"
    ARTIFACT = "artifact"
    HEARTBEAT = "heartbeat"
    PHASE_CHANGE = "phase_change"


@dataclass
class Agent:
    id: str
    role: AgentRole
    name: str
    status: str = "active"
    metadata: Dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class LobbyMessage:
    id: str
    from_agent: str
    to_agent: str  # "all" for broadcast
    timestamp: str
    type: MessageType
    content: str
    metadata: Dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BuildLobby:
    """
    A persistent, file-backed lobby for multi-agent build coordination.
    Supports locking for concurrent access across processes/containers.
    """
    
    def __init__(self, lobby_path: str = "/root/agent/build_lobby.json"):
        self.lobby_path = Path(lobby_path)
        self.lock_path = Path(str(lobby_path) + ".lock")
        self._lock = threading.Lock()
        self._ensure_lobby()
    
    def _ensure_lobby(self):
        """Create lobby file if it doesn't exist."""
        if not self.lobby_path.exists():
            initial = {
                "lobby_id": f"aria-build-{uuid.uuid4().hex[:8]}",
                "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "participants": [],
                "build_state": {
                    "phase": "initializing",
                    "last_successful_step": "none",
                    "blockers": [],
                    "patches_applied": [],
                    "artifacts_cached": []
                },
                "messages": [],
                "sync_protocol": {
                    "heartbeat_interval_sec": 30,
                    "state_file": str(self.lobby_path),
                    "lock_file": str(self.lock_path)
                }
            }
            self._write(initial)
    
    def _acquire_lock(self):
        """Acquire file lock for cross-process safety."""
        self.lock_file = open(self.lock_path, 'w')
        fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_EX)
    
    def _release_lock(self):
        """Release file lock."""
        fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_UN)
        self.lock_file.close()
    
    def _read(self) -> Dict:
        with self._lock:
            self._acquire_lock()
            try:
                with open(self.lobby_path, 'r') as f:
                    return json.load(f)
            finally:
                self._release_lock()
    
    def _write(self, data: Dict):
        with self._lock:
            self._acquire_lock()
            try:
                with open(self.lobby_path, 'w') as f:
                    json.dump(data, f, indent=2)
            finally:
                self._release_lock()
    
    def register_agent(self, agent: Agent) -> None:
        """Register a new agent in the lobby."""
        data = self._read()
        # Remove existing agent with same ID
        data["participants"] = [p for p in data["participants"] if p["id"] != agent.id]
        data["participants"].append(asdict(agent))
        self._write(data)
    
    def update_agent_status(self, agent_id: str, status: str) -> None:
        data = self._read()
        for p in data["participants"]:
            if p["id"] == agent_id:
                p["status"] = status
                break
        self._write(data)
    
    def send_message(self, msg: LobbyMessage) -> None:
        data = self._read()
        data["messages"].append(asdict(msg))
        # Keep last 500 messages
        if len(data["messages"]) > 500:
            data["messages"] = data["messages"][-500:]
        self._write(data)
    
    def broadcast(self, from_agent: str, msg_type: MessageType, content: str, metadata: Dict = None) -> None:
        msg = LobbyMessage(
            id=uuid.uuid4().hex[:12],
            from_agent=from_agent,
            to_agent="all",
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            type=msg_type,
            content=content,
            metadata=metadata or {}
        )
        self.send_message(msg)
    
    def direct_message(self, from_agent: str, to_agent: str, msg_type: MessageType, content: str, metadata: Dict = None) -> None:
        msg = LobbyMessage(
            id=uuid.uuid4().hex[:12],
            from_agent=from_agent,
            to_agent=to_agent,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            type=msg_type,
            content=content,
            metadata=metadata or {}
        )
        self.send_message(msg)
    
    def update_build_state(self, **kwargs) -> None:
        data = self._read()
        data["build_state"].update(kwargs)
        self._write(data)
    
    def get_messages(self, since: str = None, for_agent: str = None) -> List[Dict]:
        data = self._read()
        msgs = data["messages"]
        if since:
            msgs = [m for m in msgs if m["timestamp"] > since]
        if for_agent:
            msgs = [m for m in msgs if m["to_agent"] in ("all", for_agent)]
        return msgs
    
    def get_state(self) -> Dict:
        return self._read()
    
    def add_blocker(self, blocker: str) -> None:
        data = self._read()
        if blocker not in data["build_state"]["blockers"]:
            data["build_state"]["blockers"].append(blocker)
        self._write(data)
    
    def remove_blocker(self, blocker: str) -> None:
        data = self._read()
        if blocker in data["build_state"]["blockers"]:
            data["build_state"]["blockers"].remove(blocker)
        self._write(data)
    
    def add_patch(self, patch: str) -> None:
        data = self._read()
        if patch not in data["build_state"]["patches_applied"]:
            data["build_state"]["patches_applied"].append(patch)
        self._write(data)
    
    def add_artifact(self, artifact: str) -> None:
        data = self._read()
        if artifact not in data["build_state"]["artifacts_cached"]:
            data["build_state"]["artifacts_cached"].append(artifact)
        self._write(data)
    
    def heartbeat(self, agent_id: str) -> None:
        self.update_agent_status(agent_id, "active")
        self.broadcast(agent_id, MessageType.HEARTBEAT, f"{agent_id} alive")


# Global lobby instance
_lobby_instance: Optional[BuildLobby] = None


def get_lobby() -> BuildLobby:
    global _lobby_instance
    if _lobby_instance is None:
        _lobby_instance = BuildLobby()
    return _lobby_instance


# Convenience functions for agents
def join_lobby(agent_id: str, role: AgentRole, name: str, metadata: Dict = None) -> BuildLobby:
    lobby = get_lobby()
    agent = Agent(id=agent_id, role=role, name=name, metadata=metadata or {})
    lobby.register_agent(agent)
    lobby.broadcast(agent_id, MessageType.CHAT, f"{name} ({role.value}) joined the build lobby")
    return lobby


def leave_lobby(agent_id: str, reason: str = "completed") -> None:
    lobby = get_lobby()
    lobby.update_agent_status(agent_id, reason)
    lobby.broadcast(agent_id, MessageType.CHAT, f"{agent_id} left: {reason}")


def log_build_phase(phase: str, details: str = "") -> None:
    lobby = get_lobby()
    lobby.update_build_state(phase=phase, last_successful_step=phase)
    lobby.broadcast("system", MessageType.PHASE_CHANGE, f"Phase: {phase} - {details}")


def log_error(error: str, agent_id: str = "system") -> None:
    lobby = get_lobby()
    lobby.add_blocker(error)
    lobby.broadcast(agent_id, MessageType.ERROR, error)


def log_warning(warning: str, agent_id: str = "system") -> None:
    lobby = get_lobby()
    lobby.broadcast(agent_id, MessageType.WARNING, warning)


def chat(from_agent: str, content: str, to_agent: str = "all") -> None:
    lobby = get_lobby()
    if to_agent == "all":
        lobby.broadcast(from_agent, MessageType.CHAT, content)
    else:
        lobby.direct_message(from_agent, to_agent, MessageType.CHAT, content)


if __name__ == "__main__":
    # Demo usage
    lobby = join_lobby("kai-primary", AgentRole.ORCHESTRATOR, "Kai Primary")
    lobby.broadcast("kai-primary", MessageType.STATUS, "Build lobby initialized")
    
    # Simulate another agent joining
    join_lobby("colab-worker", AgentRole.BUILDER, "Colab Worker")
    
    # Simulate build phases
    log_build_phase("patches_applied", "PEP668 and root patches applied")
    log_build_phase("colab_handoff", "Handing off to cloud builder")
    
    print("Lobby state:")
    print(json.dumps(lobby.get_state(), indent=2))
