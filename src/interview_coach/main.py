#!/usr/bin/env python
"""
Interview Coach - Main Flow Module

This module provides the CrewAI Flow-based interview system.
For API-based interviews, use the FastAPI server instead:
    python -m interview_coach.api.main
    # or: uvicorn interview_coach.api.main:app --reload
"""
import sys
from typing import Optional

from interview_coach.questions_flow import GenerateInterviewQuestionsFlow

def kickoff_generate_questions():
    """
    Run the interview coach flow with default/demo mode.
    """
    flow = GenerateInterviewQuestionsFlow()
    flow.kickoff()


def plot_generate_questions():
    """
    Generate a visual plot of the interview coach flow.
    """
    flow = GenerateInterviewQuestionsFlow()
    flow.plot()


def run_generate_questions_with_trigger(payload: Optional[dict] = None):
    """
    Run the interview coach flow with a trigger payload.
    
    Args:
        payload: Dictionary containing:
            - resume_pdf_path: Path to candidate's resume PDF
            - job_description: Job description text
            - candidate_name: Name of the candidate
    """
    flow = GenerateInterviewQuestionsFlow()
    flow.kickoff({"crewai_trigger_payload": payload or {}})


def serve(host: str = "0.0.0.0", port: int = 8000):
    """
    Start the FastAPI server for API-based interviews.
    """
    from interview_coach.api.main import run_server
    run_server(host=host, port=port, reload=False)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "serve":
        serve()
    else:
        kickoff_generate_questions()
