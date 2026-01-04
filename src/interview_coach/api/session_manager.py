"""Session Manager
Manages interview sessions with thread-safe state management.
Supports concurrent interview sessions with proper isolation.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from threading import Lock
from dataclasses import dataclass, field

from .models import InterviewStatus, TranscriptEntry

logger = logging.getLogger(__name__)


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
    questions: List[str] = field(default_factory=list)
    responses: List[str] = field(default_factory=list)

    # Transcript and evaluation
    transcript_entries: List[TranscriptEntry] = field(default_factory=list)
    evaluation_report: str = ""
    scores: Dict[str, Any] = field(default_factory=dict)

    # RAG session
    rag_session_id: str = ""

    @property
    def total_questions(self) -> int:
        return len(self.questions)

    @property
    def questions_completed(self) -> int:
        return len(self.responses)

    @property
    def awaiting_response(self) -> bool:
        return self.status == InterviewStatus.READY


class SessionManager:
    """Thread-safe session manager for interview sessions."""

    _instance: Optional['SessionManager'] = None
    _lock = Lock()

    def __new__(cls):
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
        resume_pdf_path: Optional[str] = None,
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
            )
            self._sessions[session_id] = session
            logger.info(f"Created session: {session_id} for {candidate_name}")
            return session

    def get_session(self, session_id: str) -> Optional[InterviewSession]:
        """Retrieve a session by ID."""
        with self._session_lock:
            return self._sessions.get(session_id)

    def get_session_or_raise(self, session_id: str) -> InterviewSession:
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

    def set_interview_questions(
        self,
        session_id: str,
        questions: List[str],
        topics: Optional[List[str]] = None,
    ) -> None:
        """Store the generated questions for a session."""
        session = self.get_session_or_raise(session_id)
        session.questions = questions
        session.interview_topics = topics or []
        session.status = InterviewStatus.READY
        self.update_session(session)
        logger.info(f"Session {session_id}: Stored {len(questions)} interview questions")

    def record_responses(self, session_id: str, responses: List[str]) -> None:
        """Record all candidate responses and build the transcript."""
        session = self.get_session_or_raise(session_id)

        if len(responses) != len(session.questions):
            raise ValueError(
                f"Expected {len(session.questions)} responses but received {len(responses)}"
            )

        session.responses = responses
        session.transcript_entries = []

        now = datetime.now()
        for idx, (question, response) in enumerate(zip(session.questions, responses)):
            topic = session.interview_topics[idx] if idx < len(session.interview_topics) else ""
            session.transcript_entries.append(
                TranscriptEntry(
                    question_number=idx + 1,
                    topic=topic,
                    question=question,
                    response=response,
                    timestamp=now,
                )
            )

        session.status = InterviewStatus.EVALUATING
        self.update_session(session)

    def complete_interview(
        self,
        session_id: str,
        evaluation_report: str,
        scores: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Mark interview as completed with evaluation results."""
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

    @property
    def active_session_count(self) -> int:
        """Count of active sessions."""
        with self._session_lock:
            return len(self._sessions)


# Global session manager instance
session_manager = SessionManager()
