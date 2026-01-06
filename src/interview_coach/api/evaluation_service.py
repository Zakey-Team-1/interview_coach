# Evaluation Service
"""
Service for evaluating interview transcripts using the EvaluationCrew.

This service provides a standalone evaluation capability that can be used
to assess candidate performance based on job descriptions and interview transcripts.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any

from interview_coach.crews.evaluation_crew.evaluation_crew import EvaluationCrew

logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class QuestionAnswerPair:
    """Represents a single question-answer pair from an interview."""
    question: str
    answer: str


@dataclass
class EvaluationInput:
    """Input data required for evaluation."""
    job_description: str
    transcript: List[QuestionAnswerPair]
    candidate_name: Optional[str] = None


@dataclass
class EvaluationResult:
    """Result of an interview evaluation."""
    evaluation_report: str
    scores: Dict[str, Any]
    evaluated_at: datetime
    candidate_name: Optional[str]
    questions_evaluated: int


# ============================================================================
# Evaluation Service
# ============================================================================

class EvaluationService:
    """
    Service class for running interview evaluations using the EvaluationCrew.
    
    This service is stateless and can evaluate any interview transcript
    against a job description without requiring an active interview session.
    
    Usage:
        service = EvaluationService()
        result = await service.evaluate(
            job_description="Senior Python Developer...",
            transcript=[
                QuestionAnswerPair(1, "Tell me about...", "I have experience..."),
                ...
            ]
        )
    """
    
    def __init__(self):
        """Initialize the evaluation service."""
        logger.info("EvaluationService initialized")
    
    def _format_transcript(self, transcript: List[QuestionAnswerPair]) -> str:
        """
        Format the question-answer pairs into a readable transcript string.
        
        Args:
            transcript: List of question-answer pairs
            
        Returns:
            Formatted transcript string for the evaluation crew
        """
        lines = []
        for i, qa in enumerate(transcript, 1):
            lines.append(f"\n[QUESTION {i}]")
            lines.append(f"Interviewer: {qa.question}")
            lines.append(f"Candidate: {qa.answer}")
        
        return "\n".join(lines)
    
    async def evaluate(
        self,
        job_description: str,
        transcript: List[QuestionAnswerPair],
        candidate_name: Optional[str] = None
    ) -> EvaluationResult:
        """
        Evaluate an interview transcript against a job description.
        
        Args:
            job_description: The job description for the role
            transcript: List of question-answer pairs from the interview
            candidate_name: Optional name of the candidate
            
        Returns:
            EvaluationResult containing the evaluation report and metadata
            
        Raises:
            ValueError: If transcript is empty or job_description is too short
        """
        # Validate inputs
        if not transcript:
            raise ValueError("Interview transcript cannot be empty")
        
        if len(job_description.strip()) < 50:
            raise ValueError("Job description must be at least 50 characters")
        
        # Format transcript for evaluation
        transcript_text = self._format_transcript(transcript)
        
        logger.info(
            f"🔍 Running evaluation for {candidate_name or 'candidate'} "
            f"with {len(transcript)} Q&A pairs..."
        )
        
        # Run the evaluation crew
        try:
            result = await (
                EvaluationCrew()
                .crew()
                .kickoff_async(inputs={
                    "interview_transcript": transcript_text,
                    "job_description": job_description
                })
            )
            
            # Extract evaluation report
            try:
                evaluation_report = result.raw  # type: ignore
            except (AttributeError, TypeError):
                evaluation_report = str(result)
            
            logger.info(f"✅ Evaluation completed successfully")
            
            return EvaluationResult(
                evaluation_report=evaluation_report,
                scores={},  # Scores can be parsed from report if needed
                evaluated_at=datetime.now(),
                candidate_name=candidate_name,
                questions_evaluated=len(transcript)
            )
            
        except Exception as e:
            logger.exception(f"❌ Evaluation failed: {e}")
            raise RuntimeError(f"Evaluation failed: {str(e)}") from e
    
    async def evaluate_from_input(self, evaluation_input: EvaluationInput) -> EvaluationResult:
        """
        Evaluate using an EvaluationInput object.
        
        Convenience method that accepts the dataclass directly.
        
        Args:
            evaluation_input: EvaluationInput containing job description and transcript
            
        Returns:
            EvaluationResult containing the evaluation report
        """
        return await self.evaluate(
            job_description=evaluation_input.job_description,
            transcript=evaluation_input.transcript,
            candidate_name=evaluation_input.candidate_name
        )


# Global service instance (singleton)
evaluation_service = EvaluationService()
