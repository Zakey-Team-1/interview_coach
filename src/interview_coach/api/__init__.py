# Interview Coach API Package
"""
FastAPI backend for the AI Interview Coach system.

Provides REST API endpoints for:
- Starting interview sessions
- Getting interview questions
- Submitting candidate responses
- Retrieving evaluation results
- Standalone interview evaluation
"""

from .main import app
from .interview_service import InterviewService, interview_service
from .evaluation_service import EvaluationService, evaluation_service

__all__ = [
    "app",
    "InterviewService",
    "interview_service", 
    "EvaluationService",
    "evaluation_service",
]
