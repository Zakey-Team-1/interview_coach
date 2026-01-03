# API Request/Response Models
"""
Pydantic models for API request and response schemas.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ============================================================================
# Enums
# ============================================================================

class InterviewStatus(str, Enum):
    """Status of an interview session."""
    INITIALIZING = "initializing"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    AWAITING_RESPONSE = "awaiting_response"
    EVALUATING = "evaluating"
    COMPLETED = "completed"
    ERROR = "error"


class QuestionStatus(str, Enum):
    """Status of a question in the interview."""
    PENDING = "pending"
    ASKED = "asked"
    ANSWERED = "answered"
    FOLLOW_UP_ASKED = "follow_up_asked"
    COMPLETED = "completed"


# ============================================================================
# Request Models
# ============================================================================

class StartInterviewRequest(BaseModel):
    """Request to start a new interview session."""
    resume_pdf_path: Optional[str] = Field(
        None, 
        description="Path to the candidate's resume PDF file"
    )
    job_description: str = Field(
        ..., 
        description="The job description to interview for",
        min_length=50
    )
    candidate_name: str = Field(
        default="Candidate",
        description="Name of the candidate"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "resume_pdf_path": "/path/to/resume.pdf",
                "job_description": "We are looking for a Senior Python Developer with 5+ years of experience...",
                "candidate_name": "John Doe"
            }
        }
    }


class SubmitResponseRequest(BaseModel):
    """Request to submit a candidate's response."""
    response: str = Field(
        ..., 
        description="The candidate's response to the current question",
        min_length=1
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "response": "In my previous role at XYZ Company, I led a team of 5 developers..."
            }
        }
    }


# ============================================================================
# Response Models
# ============================================================================

class SessionInfo(BaseModel):
    """Basic session information."""
    session_id: str
    status: InterviewStatus
    candidate_name: str
    created_at: datetime
    current_question_index: int
    total_questions: int


class StartInterviewResponse(BaseModel):
    """Response after starting a new interview."""
    session_id: str
    status: InterviewStatus
    message: str
    candidate_name: str
    total_questions: int
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "session_id": "session_20260103_143022",
                "status": "ready",
                "message": "Interview session initialized. Call /session/{session_id}/question to get the first question.",
                "candidate_name": "John Doe",
                "total_questions": 6
            }
        }
    }


class QuestionResponse(BaseModel):
    """Response containing the current interview question."""
    session_id: str
    question_number: int
    total_questions: int
    question: str
    topic: str
    resume_context: Optional[str] = Field(
        None,
        description="Relevant context from the candidate's resume"
    )
    is_follow_up: bool = False
    status: QuestionStatus
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "session_id": "session_20260103_143022",
                "question_number": 1,
                "total_questions": 6,
                "question": "Can you walk me through a challenging Python project you've worked on?",
                "topic": "Python Development Experience",
                "resume_context": "Candidate has 5 years of Python experience...",
                "is_follow_up": False,
                "status": "asked"
            }
        }
    }


class SubmitResponseResponse(BaseModel):
    """Response after submitting a candidate answer."""
    session_id: str
    acknowledged: bool
    message: str
    has_follow_up: bool
    interview_complete: bool
    next_action: str
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "session_id": "session_20260103_143022",
                "acknowledged": True,
                "message": "Response recorded. Follow-up question available.",
                "has_follow_up": True,
                "interview_complete": False,
                "next_action": "GET /session/{session_id}/question"
            }
        }
    }


class TranscriptEntry(BaseModel):
    """Single entry in the interview transcript."""
    question_number: int
    topic: str
    question: str
    response: str
    follow_up_question: Optional[str] = None
    follow_up_response: Optional[str] = None
    timestamp: datetime


class InterviewTranscript(BaseModel):
    """Complete interview transcript."""
    session_id: str
    candidate_name: str
    entries: List[TranscriptEntry]
    total_duration_seconds: Optional[float] = None


class EvaluationResponse(BaseModel):
    """Response containing the interview evaluation."""
    session_id: str
    candidate_name: str
    status: InterviewStatus
    evaluation_report: str
    scores: Dict[str, Any] = Field(default_factory=dict)
    transcript: InterviewTranscript
    completed_at: datetime
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "session_id": "session_20260103_143022",
                "candidate_name": "John Doe",
                "status": "completed",
                "evaluation_report": "## Interview Evaluation\n\n...",
                "scores": {"technical": 8.5, "communication": 9.0, "overall": 8.7},
                "completed_at": "2026-01-03T14:45:30"
            }
        }
    }


class SessionStatusResponse(BaseModel):
    """Response containing session status details."""
    session_id: str
    status: InterviewStatus
    candidate_name: str
    current_question_index: int
    total_questions: int
    questions_completed: int
    created_at: datetime
    last_activity: datetime
    awaiting_response: bool


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    detail: str
    session_id: Optional[str] = None
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "error": "SessionNotFound",
                "detail": "No session found with ID: session_invalid",
                "session_id": "session_invalid"
            }
        }
    }


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    timestamp: datetime
    active_sessions: int
