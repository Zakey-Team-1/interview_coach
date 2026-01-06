import logging
from dataclasses import dataclass
from typing import List, Optional

from interview_coach.questions_flow import GenerateInterviewQuestionsFlow
from rag.rag_service import ResumeRAGService

logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class QuestionGenerationResult:
    """Result of question generation."""
    session_id: str
    candidate_name: str
    job_description: str
    questions: List[str]
    topics: List[str]


# ============================================================================
# Interview Service (Stateless Question Generation)
# ============================================================================

class InterviewService:
    """
    Stateless service for generating interview questions.
    
    This service uses the GenerateInterviewQuestionsFlow to create
    personalized interview questions based on job descriptions and resumes.
    No session state is persisted after the request completes.
    """
    
    def __init__(self):
        self.rag_service = ResumeRAGService()
    
    async def generate_questions(
        self,
        candidate_name: str,
        job_description: str,
        resume_pdf_path: Optional[str] = None
    ) -> QuestionGenerationResult:
        """
        Generate interview questions based on job description and optional resume.
        
        This is a stateless operation - the flow is created, executed, and
        discarded after returning the results.
        
        Args:
            candidate_name: Name of the candidate
            job_description: The job description to generate questions for
            resume_pdf_path: Optional path to resume PDF file
            
        Returns:
            QuestionGenerationResult with session_id (for reference only),
            candidate name, and list of generated questions
            
        Raises:
            ValueError: If job description is too short or invalid
            RuntimeError: If question generation fails
        """
        try:
            # Create and run the flow
            flow = GenerateInterviewQuestionsFlow()
            
            payload = {
                "candidate_name": candidate_name,
                "job_description": job_description,
                "resume_pdf_path": resume_pdf_path or ""
            }
            
            logger.info(f"🎯 Generating questions for {candidate_name}...")
            
            # Run the flow asynchronously
            await flow.kickoff_async(payload)
            
            # Extract results from flow state
            session_id = flow.state.session_id
            questions = flow.state.questions
            topics = flow.state.interview_topics
            
            logger.info(f"✅ Generated {len(questions)} questions for session {session_id}")
            
            return QuestionGenerationResult(
                session_id=session_id,
                candidate_name=candidate_name,
                job_description=job_description,
                questions=questions,
                topics=topics
            )
            
        except Exception as e:
            logger.exception(f"❌ Failed to generate questions: {e}")
            raise RuntimeError(f"Question generation failed: {str(e)}") from e


# Global service instance (singleton)
interview_service = InterviewService()
