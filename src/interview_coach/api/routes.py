# API Routes
"""
FastAPI route handlers for the Interview Coach API.
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends

from .models import (
    StartInterviewRequest,
    StartInterviewResponse,
    SubmitResponseRequest,
    SubmitResponseResponse,
    QuestionResponse,
    EvaluationResponse,
    SessionStatusResponse,
    InterviewTranscript,
    ErrorResponse,
    InterviewStatus,
    QuestionStatus,
)
from .session_manager import session_manager, InterviewSession
from .interview_service import interview_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["interview"])


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
    description="Initialize a new interview session with job description and optional resume."
)
async def start_interview(
    request: StartInterviewRequest,
    background_tasks: BackgroundTasks,
    service: InterviewService = Depends(get_interview_service)
) -> StartInterviewResponse:
    """
    Start a new interview session.
    
    This endpoint:
    1. Creates a new session
    2. Ingests resume into RAG (if provided)
    3. Generates interview roadmap
    4. Returns session ID for subsequent calls
    """
    try:
        session = await service.initialize_session(
            candidate_name=request.candidate_name,
            job_description=request.job_description,
            resume_pdf_path=request.resume_pdf_path
        )
        
        return StartInterviewResponse(
            session_id=session.session_id,
            status=session.status,
            message="Interview session initialized. Call GET /sessions/{session_id}/question to get the first question.",
            candidate_name=session.candidate_name,
            total_questions=session.total_questions
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
        current_question_index=session.current_question_index,
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
# Interview Flow Endpoints
# ============================================================================

@router.get(
    "/sessions/{session_id}/question",
    response_model=QuestionResponse,
    responses={404: {"model": ErrorResponse}, 400: {"model": ErrorResponse}},
    summary="Get current question",
    description="Get the current interview question for the candidate to answer."
)
async def get_current_question(
    session_id: str,
    service: InterviewService = Depends(get_interview_service)
) -> QuestionResponse:
    """
    Get the current interview question.
    
    Questions are pre-generated during session initialization.
    This endpoint retrieves the current question from the pre-generated list.
    """
    session = session_manager.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
    
    if session.status == InterviewStatus.COMPLETED:
        raise HTTPException(
            status_code=400, 
            detail="Interview already completed. Call GET /sessions/{session_id}/evaluation for results."
        )
    
    if session.status == InterviewStatus.EVALUATING:
        raise HTTPException(
            status_code=400,
            detail="Interview is being evaluated. Please wait."
        )
    
    if session.status not in [InterviewStatus.READY, InterviewStatus.IN_PROGRESS, InterviewStatus.AWAITING_RESPONSE]:
        raise HTTPException(
            status_code=400,
            detail=f"Session not ready for questions. Status: {session.status}"
        )
    
    try:
        # Get question state
        question_state = session.current_question
        if question_state is None:
            raise HTTPException(status_code=400, detail="No more questions available")
        
        # Retrieve pre-generated question if not already set
        if question_state.status == QuestionStatus.PENDING:
            # Retrieve question from service
            question_text = await service.generate_question(session_id=session_id)
            session_manager.set_current_question(session_id, question_text, is_follow_up=False)
            # Refresh session
            session = session_manager.get_session_or_raise(session_id)
            question_state = session.current_question
        
        return QuestionResponse(
            session_id=session_id,
            question_number=session.current_question_index + 1,
            total_questions=session.total_questions,
            question=question_state.primary_question or "",
            topic=question_state.topic,
            resume_context=question_state.resume_context if question_state.resume_context else None,
            is_follow_up=False,
            status=question_state.status
        )
        
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception(f"Error getting question: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate question: {str(e)}")


@router.post(
    "/sessions/{session_id}/response",
    response_model=SubmitResponseResponse,
    responses={404: {"model": ErrorResponse}, 400: {"model": ErrorResponse}},
    summary="Submit candidate response",
    description="Submit the candidate's response to the current question."
)
async def submit_response(
    session_id: str,
    request: SubmitResponseRequest,
    service: InterviewService = Depends(get_interview_service)
) -> SubmitResponseResponse:
    """
    Submit a response to the current question.
    
    After submission, the interview moves to the next question.
    If all questions complete, interview moves to evaluation.
    """
    session = session_manager.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
    
    if session.status != InterviewStatus.AWAITING_RESPONSE:
        raise HTTPException(
            status_code=400,
            detail=f"Not expecting a response. Current status: {session.status}"
        )
    
    question_state = session.current_question
    if question_state is None:
        raise HTTPException(status_code=400, detail="No active question")
    
    try:
        # Determine if this is a follow-up response
        is_follow_up = question_state.status == QuestionStatus.FOLLOW_UP_ASKED
        
        # Record the response
        session_manager.submit_response(session_id, request.response, is_follow_up)
        
        # Always advance to next question (no follow-ups)
        has_more = session_manager.advance_to_next_question(session_id)
        interview_complete = not has_more
        
        if interview_complete:
            # Trigger evaluation in background
            await service.run_evaluation(session_id)
        
        # Refresh session state
        session = session_manager.get_session_or_raise(session_id)
        
        if interview_complete:
            next_action = f"GET /api/v1/sessions/{session_id}/evaluation"
            message = "Interview complete. Evaluation in progress."
        else:
            next_action = f"GET /api/v1/sessions/{session_id}/question"
            message = "Response recorded. Next question available."
        
        return SubmitResponseResponse(
            session_id=session_id,
            acknowledged=True,
            message=message,
            has_follow_up=False,
            interview_complete=interview_complete,
            next_action=next_action
        )
        
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception(f"Error submitting response: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process response: {str(e)}")


@router.post(
    "/sessions/{session_id}/skip",
    response_model=SubmitResponseResponse,
    responses={404: {"model": ErrorResponse}, 400: {"model": ErrorResponse}},
    summary="Skip current question",
    description="Skip the current question and move to the next one."
)
async def skip_question(session_id: str) -> SubmitResponseResponse:
    """Skip the current question and move to the next."""
    session = session_manager.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
    
    if session.status not in [InterviewStatus.AWAITING_RESPONSE, InterviewStatus.IN_PROGRESS]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot skip in current state: {session.status}"
        )
    
    # Record skip as empty response
    question_state = session.current_question
    if question_state:
        is_follow_up = question_state.status == QuestionStatus.FOLLOW_UP_ASKED
        session_manager.submit_response(session_id, "[SKIPPED]", is_follow_up)
    
    # Always advance on skip
    has_more = session_manager.advance_to_next_question(session_id)
    
    return SubmitResponseResponse(
        session_id=session_id,
        acknowledged=True,
        message="Question skipped." if has_more else "Question skipped. Interview complete.",
        has_follow_up=False,
        interview_complete=not has_more,
        next_action=f"GET /api/v1/sessions/{session_id}/question" if has_more else f"GET /api/v1/sessions/{session_id}/evaluation"
    )


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
