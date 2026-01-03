# Session Manager
"""
Manages interview sessions with thread-safe state management.
Supports concurrent interview sessions with proper isolation.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional, List, Any
from threading import Lock
from dataclasses import dataclass, field
from enum import Enum

from .models import InterviewStatus, QuestionStatus, TranscriptEntry

logger = logging.getLogger(__name__)


@dataclass
class QuestionState:
    """State of a single question in the interview."""
    index: int
    topic: str
    resume_context: str
    primary_question: Optional[str] = None
    primary_response: Optional[str] = None
    follow_up_question: Optional[str] = None
    follow_up_response: Optional[str] = None
    status: QuestionStatus = QuestionStatus.PENDING
    asked_at: Optional[datetime] = None
    answered_at: Optional[datetime] = None


@dataclass
class InterviewSession:
    """Complete state of an interview session."""
    session_id: str
    candidate_name: str
    job_description: str
    resume_pdf_path: Optional[str]
    status: InterviewStatus
    created_at: datetime
    last_activity: datetime
    
    # Interview content
    interview_topics: List[str] = field(default_factory=list)
    questions: List[QuestionState] = field(default_factory=list)
    current_question_index: int = 0
    
    # Transcript and evaluation
    transcript_entries: List[TranscriptEntry] = field(default_factory=list)
    evaluation_report: str = ""
    scores: Dict[str, Any] = field(default_factory=dict)
    
    # RAG session
    rag_session_id: str = ""
    
    # Response queue for async handling
    pending_response: Optional[str] = None
    response_event: Optional[asyncio.Event] = None
    
    @property
    def total_questions(self) -> int:
        return len(self.interview_topics)
    
    @property
    def questions_completed(self) -> int:
        return sum(1 for q in self.questions if q.status == QuestionStatus.COMPLETED)
    
    @property
    def awaiting_response(self) -> bool:
        return self.status == InterviewStatus.AWAITING_RESPONSE
    
    @property
    def current_question(self) -> Optional[QuestionState]:
        if 0 <= self.current_question_index < len(self.questions):
            return self.questions[self.current_question_index]
        return None


class SessionManager:
    """
    Thread-safe session manager for concurrent interview sessions.
    
    Provides:
    - Session creation and retrieval
    - State persistence
    - Async response handling
    - Session cleanup
    """
    
    _instance: Optional['SessionManager'] = None
    _lock = Lock()
    
    def __new__(cls):
        """Singleton pattern for session manager."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._sessions: Dict[str, InterviewSession] = {}
        self._session_lock = Lock()
        self._initialized = True
        logger.info("SessionManager initialized")
    
    def create_session(
        self,
        session_id: str,
        candidate_name: str,
        job_description: str,
        resume_pdf_path: Optional[str] = None
    ) -> InterviewSession:
        """Create a new interview session."""
        with self._session_lock:
            if session_id in self._sessions:
                raise ValueError(f"Session {session_id} already exists")
            
            now = datetime.now()
            session = InterviewSession(
                session_id=session_id,
                candidate_name=candidate_name,
                job_description=job_description,
                resume_pdf_path=resume_pdf_path,
                status=InterviewStatus.INITIALIZING,
                created_at=now,
                last_activity=now,
                rag_session_id=session_id,
                response_event=asyncio.Event()
            )
            self._sessions[session_id] = session
            logger.info(f"Created session: {session_id} for {candidate_name}")
            return session
    
    def get_session(self, session_id: str) -> Optional[InterviewSession]:
        """Retrieve a session by ID."""
        with self._session_lock:
            return self._sessions.get(session_id)
    
    def get_session_or_raise(self, session_id: str) -> InterviewSession:
        """Retrieve a session or raise an exception if not found."""
        session = self.get_session(session_id)
        if session is None:
            raise KeyError(f"Session not found: {session_id}")
        return session
    
    def update_session(self, session: InterviewSession) -> None:
        """Update session state."""
        with self._session_lock:
            session.last_activity = datetime.now()
            self._sessions[session.session_id] = session
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        with self._session_lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                logger.info(f"Deleted session: {session_id}")
                return True
            return False
    
    def list_sessions(self) -> List[InterviewSession]:
        """List all active sessions."""
        with self._session_lock:
            return list(self._sessions.values())
    
    @property
    def active_session_count(self) -> int:
        """Count of active sessions."""
        with self._session_lock:
            return len(self._sessions)
    
    def set_interview_topics(
        self, 
        session_id: str, 
        topics: List[str],
        resume_contexts: Optional[List[str]] = None
    ) -> None:
        """Set the interview topics and initialize question states."""
        session = self.get_session_or_raise(session_id)
        
        session.interview_topics = topics
        session.questions = []
        
        for i, topic in enumerate(topics):
            context = resume_contexts[i] if resume_contexts and i < len(resume_contexts) else ""
            session.questions.append(QuestionState(
                index=i,
                topic=topic,
                resume_context=context
            ))
        
        session.status = InterviewStatus.READY
        self.update_session(session)
        logger.info(f"Session {session_id}: Set {len(topics)} interview topics")
    
    def set_current_question(
        self, 
        session_id: str, 
        question_text: str,
        is_follow_up: bool = False
    ) -> None:
        """Set the current question text."""
        session = self.get_session_or_raise(session_id)
        question = session.current_question
        
        if question is None:
            raise ValueError("No current question available")
        
        if is_follow_up:
            question.follow_up_question = question_text
            question.status = QuestionStatus.FOLLOW_UP_ASKED
        else:
            question.primary_question = question_text
            question.status = QuestionStatus.ASKED
            question.asked_at = datetime.now()
        
        session.status = InterviewStatus.AWAITING_RESPONSE
        self.update_session(session)
    
    def submit_response(
        self, 
        session_id: str, 
        response: str,
        is_follow_up: bool = False
    ) -> None:
        """Submit a candidate response."""
        session = self.get_session_or_raise(session_id)
        question = session.current_question
        
        if question is None:
            raise ValueError("No current question to respond to")
        
        if is_follow_up:
            question.follow_up_response = response
            question.status = QuestionStatus.COMPLETED
            question.answered_at = datetime.now()
        else:
            question.primary_response = response
            question.status = QuestionStatus.ANSWERED
            question.answered_at = datetime.now()
        
        # Store for async retrieval
        session.pending_response = response
        if session.response_event:
            session.response_event.set()
        
        session.status = InterviewStatus.IN_PROGRESS
        self.update_session(session)
    
    async def wait_for_response(
        self, 
        session_id: str, 
        timeout: float = 300.0
    ) -> Optional[str]:
        """Wait for a candidate response (async)."""
        session = self.get_session_or_raise(session_id)
        
        if session.response_event is None:
            session.response_event = asyncio.Event()
        
        session.response_event.clear()
        session.status = InterviewStatus.AWAITING_RESPONSE
        self.update_session(session)
        
        try:
            await asyncio.wait_for(session.response_event.wait(), timeout=timeout)
            response = session.pending_response
            session.pending_response = None
            return response
        except asyncio.TimeoutError:
            logger.warning(f"Session {session_id}: Response timeout")
            return None
    
    def advance_to_next_question(self, session_id: str) -> bool:
        """Move to the next question. Returns False if interview is complete."""
        session = self.get_session_or_raise(session_id)
        
        # Save transcript entry for completed question
        if session.current_question and session.current_question.status == QuestionStatus.COMPLETED:
            entry = TranscriptEntry(
                question_number=session.current_question_index + 1,
                topic=session.current_question.topic,
                question=session.current_question.primary_question or "",
                response=session.current_question.primary_response or "",
                follow_up_question=session.current_question.follow_up_question,
                follow_up_response=session.current_question.follow_up_response,
                timestamp=session.current_question.asked_at or datetime.now()
            )
            session.transcript_entries.append(entry)
        
        # Check if there are more questions
        if session.current_question_index + 1 >= len(session.questions):
            session.status = InterviewStatus.EVALUATING
            self.update_session(session)
            return False
        
        session.current_question_index += 1
        session.status = InterviewStatus.IN_PROGRESS
        self.update_session(session)
        return True
    
    def complete_interview(
        self, 
        session_id: str,
        evaluation_report: str,
        scores: Optional[Dict[str, Any]] = None
    ) -> None:
        """Mark interview as completed with evaluation."""
        session = self.get_session_or_raise(session_id)
        session.evaluation_report = evaluation_report
        session.scores = scores or {}
        session.status = InterviewStatus.COMPLETED
        self.update_session(session)
        logger.info(f"Session {session_id}: Interview completed")
    
    def set_error(self, session_id: str, error_message: str) -> None:
        """Mark session as error state."""
        session = self.get_session_or_raise(session_id)
        session.status = InterviewStatus.ERROR
        session.evaluation_report = f"Error: {error_message}"
        self.update_session(session)
        logger.error(f"Session {session_id}: Error - {error_message}")


# Global session manager instance
session_manager = SessionManager()
