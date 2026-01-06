# API Routes
"""
FastAPI route handlers for the Interview Coach API.

Simplified stateless service with only two endpoints:
1. POST /sessions - Generate interview questions
2. POST /evaluate - Evaluate interview transcript
"""

import logging
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form

from .models import (
    StartInterviewResponse,
    ErrorResponse,
    StandaloneEvaluationRequest,
    StandaloneEvaluationResponse,
)
from .interview_service import InterviewService, interview_service
from .evaluation_service import (
    EvaluationService,
    evaluation_service,
    QuestionAnswerPair,
)

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


def get_evaluation_service():
    """Dependency to get the global evaluation service singleton."""
    return evaluation_service


# ============================================================================
# Question Generation Endpoint
# ============================================================================

@router.post(
    "/sessions",
    response_model=StartInterviewResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Generate interview questions",
    description="""
    Generate personalized interview questions based on a job description and optional resume.
    
    This endpoint:
    1. Accepts job description and optional resume upload
    2. Analyzes the job requirements and candidate background
    3. Returns a curated list of interview questions
    
    The response includes a session_id for reference, but this service is stateless.
    """,
    tags=["questions"]
)
async def start_interview(
    candidate_name: str = Form("Candidate"),
    job_description: str = Form(..., min_length=50),
    resume_pdf: UploadFile | None = File(None),
    service: InterviewService = Depends(get_interview_service)
) -> StartInterviewResponse:
    """
    Generate interview questions based on job description and optional resume.
    
    Returns:
        - session_id: Reference identifier
        - questions: List of interview questions
        - candidate_name: Name of the candidate
        - total_questions: Number of questions generated
    """
    try:
        resume_path = None
        if resume_pdf is not None:
            resume_path = await _save_resume_upload(resume_pdf)

        result = await service.generate_questions(
            candidate_name=candidate_name,
            job_description=job_description,
            resume_pdf_path=resume_path
        )
        
        return StartInterviewResponse(
            session_id=result.session_id,
            status="ready",
            message="Interview questions generated successfully. Use POST /evaluate to evaluate responses.",
            candidate_name=result.candidate_name,
            total_questions=len(result.questions),
            questions=result.questions
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Error generating questions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate questions: {str(e)}")


# ============================================================================
# Evaluation Endpoint
# ============================================================================

@router.post(
    "/evaluate",
    response_model=StandaloneEvaluationResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Evaluate an interview transcript",
    description="""
    Evaluate an interview transcript against a job description.
    
    This stateless endpoint evaluates interview performance by analyzing:
    - Job description requirements
    - Question-answer pairs from the interview
    - Candidate's responses to each question
    
    Returns a comprehensive evaluation report with:
    - Executive summary
    - Top strengths with specific examples
    - Areas for growth
    - Actionable advice for improvement
    """,
    tags=["evaluation"]
)
async def evaluate_transcript(
    request: StandaloneEvaluationRequest,
    service: EvaluationService = Depends(get_evaluation_service)
) -> StandaloneEvaluationResponse:
    """
    Evaluate an interview transcript without requiring an active session.
    
    This endpoint is fully stateless and can evaluate any interview transcript.
    Perfect for:
    - Evaluating interviews conducted outside the system
    - Re-evaluating past interviews
    - Testing different evaluation criteria
    """
    try:
        # Convert request models to service dataclasses
        transcript = [
            QuestionAnswerPair(
                question=qa.question,
                answer=qa.answer
            )
            for qa in request.transcript
        ]
        
        # Run evaluation
        result = await service.evaluate(
            job_description=request.job_description,
            transcript=transcript,
            candidate_name=request.candidate_name
        )
        
        return StandaloneEvaluationResponse(
            evaluation_report=result.evaluation_report,
            candidate_name=result.candidate_name,
            questions_evaluated=result.questions_evaluated,
            evaluated_at=result.evaluated_at,
            scores=result.scores
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        logger.exception(f"Evaluation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception(f"Unexpected error during evaluation: {e}")
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")
