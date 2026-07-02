"""
State management for user sessions
"""

from typing import Dict, Optional
from datetime import datetime, timedelta
from app.models.user_state import UserState, UserStep, SessionData
from app.config import Config


class StateManager:
    """Manage user states and sessions"""
    
    _instance = None
    _sessions: Dict[int, Dict] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def create_session(self, user_id: int) -> bool:
        """Create a new session for user"""
        if user_id in self._sessions:
            return False
        
        self._sessions[user_id] = {
            "state": UserState.INIT,
            "data": SessionData(),
            "last_active": datetime.now(),
            "step": UserStep.INIT
        }
        return True
    
    def get_session(self, user_id: int) -> Optional[Dict]:
        """Get user session"""
        return self._sessions.get(user_id)
    
    def update_state(self, user_id: int, state: UserState, step: UserStep) -> bool:
        """Update user state"""
        session = self.get_session(user_id)
        if not session:
            return False
        
        session["state"] = state
        session["step"] = step
        session["last_active"] = datetime.now()
        return True
    
    def get_state(self, user_id: int) -> Optional[UserState]:
        """Get user state"""
        session = self.get_session(user_id)
        return session["state"] if session else None
    
    def get_step(self, user_id: int) -> Optional[UserStep]:
        """Get user step"""
        session = self.get_session(user_id)
        return session["step"] if session else None
    
    def get_data(self, user_id: int) -> Optional[SessionData]:
        """Get user session data"""
        session = self.get_session(user_id)
        return session["data"] if session else None
    
    def clear_session(self, user_id: int) -> bool:
        """Clear user session"""
        if user_id in self._sessions:
            session = self._sessions[user_id]
            if "data" in session:
                session["data"].clear()
            del self._sessions[user_id]
            return True
        return False
    
    def is_active(self, user_id: int) -> bool:
        """Check if user has active session"""
        session = self.get_session(user_id)
        if not session:
            return False
        
        # Check for timeout
        if self.is_timeout(user_id):
            self.clear_session(user_id)
            return False
        
        return True
    
    def is_timeout(self, user_id: int) -> bool:
        """Check if user session has timed out"""
        session = self.get_session(user_id)
        if not session:
            return True
        
        last_active = session["last_active"]
        timeout = Config.SESSION_TIMEOUT
        return (datetime.now() - last_active).total_seconds() > timeout
    
    def update_last_active(self, user_id: int) -> bool:
        """Update user last active time"""
        session = self.get_session(user_id)
        if not session:
            return False
        
        session["last_active"] = datetime.now()
        return True
    
    def get_all_active_sessions(self) -> Dict[int, Dict]:
        """Get all active sessions"""
        return self._sessions
    
    def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        now = datetime.now()
        expired_users = []
        
        for user_id, session in self._sessions.items():
            if (now - session["last_active"]).total_seconds() > Config.SESSION_TIMEOUT:
                expired_users.append(user_id)
        
        for user_id in expired_users:
            self.clear_session(user_id)
        
        return len(expired_users)
