# Interview Coach API Package
"""
FastAPI backend for the AI Interview Coach system.

Provides REST API endpoints for:
- Starting interview sessions
- Getting interview questions
- Submitting candidate responses
- Retrieving evaluation results
"""

from .main import app

__all__ = ["app"]
