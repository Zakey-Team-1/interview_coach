# API Routes
"""
FastAPI route handlers for the Interview Coach API.
"""

import logging
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form

from .models import (
    StartInterviewResponse,
    SubmitResponsesRequest,
    SubmitResponsesResponse,
    EvaluationResponse,
    SessionStatusResponse,
    InterviewTranscript,
    ErrorResponse,
    InterviewStatus,
)
from .session_manager import session_manager
from .interview_service import InterviewService, interview_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["interview"])

RESUME_UPLOAD_DIR = Path("uploads/resumes")
RESUME_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_RESUME_EXTENSIONS = {".pdf"}


async def _save_resume_upload(file: UploadFile) -> str:
    """Persist an uploaded resume PDF and return the stored path."""
    filename = Path(file.filename or "resume").name
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_RESUME_EXTENSIONS:
        raise ValueError("Only PDF resume uploads are supported.")

    target_path = RESUME_UPLOAD_DIR / f"{uuid4().hex}_{filename}"
    content = await file.read()
    target_path.write_bytes(content)
    await file.close()
    logger.info(f"Saved uploaded resume to {target_path}")
    return str(target_path.resolve())


def get_interview_service():
    """Dependency to get the global interview service singleton."""
    return interview_service


# ============================================================================
# Session Management Endpoints
# ============================================================================

@router.post(
    "/sessions",
    response_model=StartInterviewResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Start a new interview session",
    description="Initialize a new interview session with job description and an optional resume upload."
)
async def start_interview(
    candidate_name: str = Form("Candidate"),
    job_description: str = Form(..., min_length=50),
    resume_pdf: UploadFile | None = File(None),
    service: InterviewService = Depends(get_interview_service)
) -> StartInterviewResponse:
    """
    Start a new interview session.
    
    This endpoint:
    1. Creates a new session
    2. Persists an uploaded resume (if provided)
    3. Ingests the resume into RAG
    4. Generates interview roadmap
    5. Returns session ID for subsequent calls
    """
    try:
        resume_path = None
        if resume_pdf is not None:
            resume_path = await _save_resume_upload(resume_pdf)

        session = await service.initialize_session(
            candidate_name=candidate_name,
            job_description=job_description,
            resume_pdf_path=resume_path
        )
        
        return StartInterviewResponse(
            session_id=session.session_id,
            status=session.status,
            message="Interview questions generated. Submit all responses via POST /sessions/{session_id}/responses.",
            candidate_name=session.candidate_name,
            total_questions=session.total_questions,
            questions=session.questions
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Error starting interview: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start interview: {str(e)}")


@router.get(
    "/sessions/{session_id}",
    response_model=SessionStatusResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Get session status",
    description="Retrieve the current status and details of an interview session."
)
async def get_session_status(session_id: str) -> SessionStatusResponse:
    """Get the current status of an interview session."""
    session = session_manager.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
    
    return SessionStatusResponse(
        session_id=session.session_id,
        status=session.status,
        candidate_name=session.candidate_name,
        total_questions=session.total_questions,
        questions_completed=session.questions_completed,
        created_at=session.created_at,
        last_activity=session.last_activity,
        awaiting_response=session.awaiting_response
    )


@router.delete(
    "/sessions/{session_id}",
    responses={404: {"model": ErrorResponse}},
    summary="Delete a session",
    description="Delete an interview session and clean up resources."
)
async def delete_session(session_id: str) -> dict:
    """Delete an interview session."""
    if not session_manager.delete_session(session_id):
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
    
    return {"message": f"Session {session_id} deleted successfully"}


# ============================================================================
# Batch Interview Flow Endpoints
# ============================================================================

@router.post(
    "/sessions/{session_id}/responses",
    response_model=SubmitResponsesResponse,
    responses={404: {"model": ErrorResponse}, 400: {"model": ErrorResponse}},
    summary="Submit all responses",
    description="Submit the candidate's responses to every pre-generated question at once."
)
async def submit_responses(
    session_id: str,
    request: SubmitResponsesRequest,
    service: InterviewService = Depends(get_interview_service)
) -> SubmitResponsesResponse:
    """Accept all responses and trigger evaluation."""
    try:
        session = session_manager.get_session(session_id)
        if session is None:
            raise KeyError(f"Session not found: {session_id}")

        expected = session.total_questions
        received = len(request.responses)
        if expected != received:
            raise ValueError(f"Expected {expected} responses but received {received}")

        session = await service.submit_responses(session_id, request.responses)

        message = (
            "Responses recorded. Evaluation in progress."
            if session.status == InterviewStatus.EVALUATING
            else "Responses recorded. Evaluation complete."
        )
        next_action = f"GET /api/v1/sessions/{session_id}/evaluation"
        return SubmitResponsesResponse(
            session_id=session_id,
            acknowledged=True,
            message=message,
            evaluation_status=session.status,
            next_action=next_action,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception(f"Error submitting responses: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to record responses: {str(e)}")


# ============================================================================
# Interview Flow Endpoints
# ============================================================================

# ============================================================================
# Results Endpoints
# ============================================================================

@router.get(
    "/sessions/{session_id}/transcript",
    response_model=InterviewTranscript,
    responses={404: {"model": ErrorResponse}},
    summary="Get interview transcript",
    description="Get the complete transcript of all questions and responses."
)
async def get_transcript(session_id: str) -> InterviewTranscript:
    """Get the interview transcript."""
    session = session_manager.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
    
    return InterviewTranscript(
        session_id=session_id,
        candidate_name=session.candidate_name,
        entries=session.transcript_entries,
        total_duration_seconds=(
            (session.last_activity - session.created_at).total_seconds()
            if session.status == InterviewStatus.COMPLETED else None
        )
    )


@router.get(
    "/sessions/{session_id}/evaluation",
    response_model=EvaluationResponse,
    responses={404: {"model": ErrorResponse}, 400: {"model": ErrorResponse}},
    summary="Get evaluation results",
    description="Get the evaluation report for a completed interview."
)
async def get_evaluation(session_id: str) -> EvaluationResponse:
    """Get the interview evaluation results."""
    session = session_manager.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
    
    if session.status == InterviewStatus.EVALUATING:
        raise HTTPException(
            status_code=400,
            detail="Evaluation in progress. Please try again shortly."
        )
    
    if session.status != InterviewStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Interview not completed. Current status: {session.status}"
        )
    
    return EvaluationResponse(
        session_id=session_id,
        candidate_name=session.candidate_name,
        status=session.status,
        evaluation_report=session.evaluation_report,
        scores=session.scores,
        transcript=InterviewTranscript(
            session_id=session_id,
            candidate_name=session.candidate_name,
            entries=session.transcript_entries,
            total_duration_seconds=(session.last_activity - session.created_at).total_seconds()
        ),
        completed_at=session.last_activity
    )
