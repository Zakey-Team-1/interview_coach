# API Request/Response Models
"""
Pydantic models for API request and response schemas.

Simplified models for stateless service:
- Question generation (sessions endpoint)
- Standalone evaluation
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


# ============================================================================
# Response Models for Question Generation
# ============================================================================

class StartInterviewResponse(BaseModel):
    """Response after generating interview questions."""
    session_id: str
    status: str
    message: str
    candidate_name: str
    total_questions: int
    questions: List[str]
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "session_id": "session_20260106_143022",
                "status": "ready",
                "message": "Interview questions generated successfully. Use POST /evaluate to evaluate responses.",
                "candidate_name": "John Doe",
                "total_questions": 6,
                "questions": [
                    "Describe a challenging Python project you led.",
                    "How do you ensure code quality in critical systems?"
                ]
            }
        }
    }


# ============================================================================
# Error Response
# ============================================================================

class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    detail: str
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "error": "ValidationError",
                "detail": "Job description must be at least 50 characters"
            }
        }
    }


# ============================================================================
# Standalone Evaluation Models
# ============================================================================

class QuestionAnswerPairModel(BaseModel):
    """A single question-answer pair from an interview."""
    question: str = Field(..., description="The interview question asked", min_length=1)
    answer: str = Field(..., description="The candidate's response to the question", min_length=1)
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "question": "Tell me about a challenging Python project you led.",
                "answer": "I led a migration of our monolithic application to microservices using FastAPI..."
            }
        }
    }


class StandaloneEvaluationRequest(BaseModel):
    """Request for standalone interview evaluation without an active session."""
    job_description: str = Field(
        ...,
        description="The job description for the role being interviewed for",
        min_length=50
    )
    transcript: List[QuestionAnswerPairModel] = Field(
        ...,
        description="List of question-answer pairs from the interview",
        min_length=1
    )
    candidate_name: Optional[str] = Field(
        None,
        description="Optional name of the candidate being evaluated"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "job_description": "We are looking for a Senior Python Developer with 5+ years of experience in building scalable web applications. The ideal candidate should have strong experience with FastAPI, async programming, and microservices architecture...",
                "transcript": [
                    {
                        "question": "Tell me about a challenging Python project you led.",
                        "answer": "I led a migration of our monolithic application to microservices..."
                    },
                    {
                        "question": "How do you ensure code quality in critical systems?",
                        "answer": "We adopted a testing pyramid approach with unit tests, integration tests..."
                    }
                ],
                "candidate_name": "John Doe"
            }
        }
    }


class StandaloneEvaluationResponse(BaseModel):
    """Response containing the standalone evaluation results."""
    evaluation_report: str = Field(..., description="The detailed evaluation report in Markdown format")
    candidate_name: Optional[str] = Field(None, description="Name of the evaluated candidate")
    questions_evaluated: int = Field(..., description="Number of questions evaluated")
    evaluated_at: datetime = Field(..., description="Timestamp when evaluation was completed")
    scores: Dict[str, Any] = Field(default_factory=dict, description="Optional parsed scores")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "evaluation_report": "## 🌟 Executive Summary\n\nGreat job demonstrating your technical depth...",
                "candidate_name": "John Doe",
                "questions_evaluated": 6,
                "evaluated_at": "2026-01-06T14:30:00",
                "scores": {"technical": 8.5, "communication": 9.0, "overall": 8.7}
            }
        }
    }
