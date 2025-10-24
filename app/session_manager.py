"""
Session Manager - Per-user state (Cole's pattern)
"""
import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional

@dataclass
class UserSession:
    """User session state"""
    user_id: int
    cwd: str = "/workspace"
    thread_id: Optional[str] = None
    current_model: str = "deepseek/deepseek-r1:free"
    conversation_history: list = None
    created_at: str = None
    last_updated: str = None

    def __post_init__(self):
        if self.conversation_history is None:
            self.conversation_history = []
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()
        if self.last_updated is None:
            self.last_updated = datetime.utcnow().isoformat()

class SessionManager:
    """Manage user sessions with file persistence"""

    def __init__(self, sessions_dir: str = "data/sessions"):
        self.sessions_dir = sessions_dir
        os.makedirs(sessions_dir, exist_ok=True)

    def _session_path(self, user_id: int) -> str:
        """Get path to user's session file"""
        return os.path.join(self.sessions_dir, f"{user_id}.json")

    def load_session(self, user_id: int) -> UserSession:
        """Load user session or create new one"""
        path = self._session_path(user_id)

        if os.path.exists(path):
            with open(path, 'r') as f:
                data = json.load(f)
                # Convert list to proper format
                if isinstance(data.get('conversation_history'), list):
                    session = UserSession(**data)
                else:
                    session = UserSession(user_id=user_id)
        else:
            session = UserSession(user_id=user_id)

        return session

    def save_session(self, session: UserSession):
        """Persist session to disk"""
        session.last_updated = datetime.utcnow().isoformat()
        path = self._session_path(session.user_id)

        with open(path, 'w') as f:
            json.dump(asdict(session), f, indent=2)

    def update_cwd(self, user_id: int, cwd: str) -> UserSession:
        """
        Update working directory (Cole's thread-per-CWD pattern)
        Clears thread_id to force new thread with new context
        """
        session = self.load_session(user_id)
        session.cwd = cwd
        session.thread_id = None  # Force new thread
        self.save_session(session)
        return session

    def update_model(self, user_id: int, model: str) -> UserSession:
        """Switch model and reset conversation"""
        session = self.load_session(user_id)
        session.current_model = model
        session.conversation_history = []  # Fresh start
        self.save_session(session)
        return session

    def add_message(self, user_id: int, role: str, content: str) -> UserSession:
        """Add message to conversation history"""
        session = self.load_session(user_id)
        session.conversation_history.append({
            "role": role,
            "content": content
        })
        # Keep last 20 messages (context window management)
        if len(session.conversation_history) > 20:
            session.conversation_history = session.conversation_history[-20:]
        self.save_session(session)
        return session

    def reset_conversation(self, user_id: int) -> UserSession:
        """Clear conversation but keep cwd and model"""
        session = self.load_session(user_id)
        session.conversation_history = []
        session.thread_id = None
        self.save_session(session)
        return session
