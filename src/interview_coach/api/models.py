# API Request/Response Models
"""
Pydantic models for API request and response schemas.
"""

from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


# ============================================================================
# Enums
# ============================================================================

class InterviewStatus(str, Enum):
    """Status of an interview session."""
    INITIALIZING = "initializing"
    READY = "ready"
    EVALUATING = "evaluating"
    COMPLETED = "completed"
    ERROR = "error"


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


# ============================================================================
# Response Models
# ============================================================================

class SessionInfo(BaseModel):
    """Basic session information."""
    session_id: str
    status: InterviewStatus
    candidate_name: str
    created_at: datetime
    total_questions: int
    questions_completed: int
    awaiting_response: bool


class StartInterviewResponse(BaseModel):
    """Response after starting a new interview."""
    session_id: str
    status: InterviewStatus
    message: str
    candidate_name: str
    total_questions: int
    questions: List[str]
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "session_id": "session_20260103_143022",
                "status": "ready",
                "message": "Interview questions generated. Submit all responses via POST /sessions/{session_id}/responses.",
                "candidate_name": "John Doe",
                "total_questions": 6,
                "questions": [
                    "Describe a challenging Python project you led.",
                    "How do you ensure code quality in critical systems?"
                ]
            }
        }
    }


class SubmitResponsesRequest(BaseModel):
    """Request to submit all responses to the interview questions."""
    responses: List[str] = Field(
        ..., description="Responses to the interview questions in order"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "responses": [
                    "I led a migration of our monolith to microservices...",
                    "We adopted a testing pyramid..."
                ]
            }
        }
    }


class SubmitResponsesResponse(BaseModel):
    """Acknowledges receipt of the batched responses."""
    session_id: str
    acknowledged: bool
    message: str
    evaluation_status: InterviewStatus
    next_action: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "session_id": "session_20260103_143022",
                "acknowledged": True,
                "message": "Responses recorded. Evaluation in progress.",
                "evaluation_status": "evaluating",
                "next_action": "GET /api/v1/sessions/{session_id}/evaluation"
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
