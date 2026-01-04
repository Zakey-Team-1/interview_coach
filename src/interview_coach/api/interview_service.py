import logging

from typing import List, Optional

from interview_coach.crews.evaluation_crew.evaluation_crew import EvaluationCrew
from interview_coach.questions_flow import GenerateInterviewQuestionsFlow, InterviewSessionState
from rag.rag_service import ResumeRAGService
from interview_coach.api.session_manager import InterviewSession, session_manager

logger = logging.getLogger(__name__)        

# ============================================================================
# Interview Service (Wrapper for Flow)
# ============================================================================

class InterviewService:
    """
    Service class that wraps the InterviewServiceFlow for API use.
    
    Provides methods for:
    - Initializing sessions
    - Generating questions
    - Processing responses
    - Running evaluation
    """
    
    def __init__(self):
        self._sessions: dict[str, GenerateInterviewQuestionsFlow] = {}
        self.rag_service = ResumeRAGService()
    
    async def initialize_session(
        self,
        candidate_name: str,
        job_description: str,
        resume_pdf_path: Optional[str] = None
    ) -> InterviewSession:
        """
        Initialize a new interview session.
        
        Returns InterviewSession object for routes to use.
        """
        # Create and run the flow for initialization
        flow = GenerateInterviewQuestionsFlow()
        
        payload = {
            "candidate_name": candidate_name,
            "job_description": job_description,
            "resume_pdf_path": resume_pdf_path or ""
        }
        
        # Run initialization (this runs prepare_session -> roadmap creation -> question generation)
        # Note: Flow.kickoff is synchronous but will handle async methods internally
        flow.kickoff(payload)
        
        # Store flow for later use
        session_id = flow.state.session_id
        self._sessions[session_id] = flow
        
        # Create session in session_manager
        session = session_manager.create_session(
            session_id=session_id,
            candidate_name=candidate_name,
            job_description=job_description,
            resume_pdf_path=resume_pdf_path
        )
        
        session_manager.set_interview_questions(
            session_id=session_id,
            questions=flow.state.questions,
            topics=flow.state.interview_topics,
        )
        
        logger.info(f"✅ Session initialized: {session_id} with {len(flow.state.questions)} questions")
        
        return session_manager.get_session_or_raise(session_id)
    
    async def submit_responses(self, session_id: str, responses: List[str]) -> InterviewSession:
        """Store the batched responses and trigger evaluation."""
        flow = self._sessions.get(session_id)
        if not flow:
            raise ValueError(f"Session not found: {session_id}")

        session_manager.record_responses(session_id, responses)
        await self.run_evaluation(session_id)

        return session_manager.get_session_or_raise(session_id)
    
    async def run_evaluation(self, session_id: str) -> None:
        """
        Run evaluation on the completed interview.
        
        Updates session_manager with evaluation results.
        Returns nothing - routes get results from session_manager.
        """
        flow = self._sessions.get(session_id)
        if not flow:
            raise ValueError(f"Session not found: {session_id}")
        
        # Get session from session_manager
        session = session_manager.get_session_or_raise(session_id)
        
        # Build transcript text from session_manager transcript
        transcript_lines = []
        for entry in session.transcript_entries:
            transcript_lines.append(f"\n[QUESTION {entry.question_number} - {entry.topic}]")
            transcript_lines.append(f"Interviewer: {entry.question}")
            transcript_lines.append(f"Candidate: {entry.response}")
            if entry.follow_up_question:
                transcript_lines.append(f"Interviewer (Follow-up): {entry.follow_up_question}")
                transcript_lines.append(f"Candidate: {entry.follow_up_response or '[No response]'}")
        
        transcript_text = "\n".join(transcript_lines)
        
        logger.info(f"🔍 Running evaluation for session {session_id}...")
        
        # Run evaluation crew (sync kickoff)
        result = (
            EvaluationCrew()
            .crew()
            .kickoff(inputs={
                "interview_transcript": transcript_text,
                "job_description": flow.state.job_description
            })
        )
        
        # Extract evaluation report
        try:
            evaluation_report = result.raw  # type: ignore
        except (AttributeError, TypeError):
            evaluation_report = str(result)
        
        # Update session_manager with evaluation
        session_manager.complete_interview(
            session_id=session_id,
            evaluation_report=evaluation_report,
            scores={}  # Can parse scores from report if needed
        )
        
        logger.info(f"✅ Evaluation completed for session {session_id}")
    
    def get_flow_state(self, session_id: str) -> Optional[InterviewSessionState]:
        """Get the flow state for a session (for debugging/monitoring)."""
        flow = self._sessions.get(session_id)
        return flow.state if flow else None
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session from the flow storage."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False
    
    @property
    def active_session_count(self) -> int:
        """Number of active sessions in flow storage."""
        return len(self._sessions)


# Global service instance (singleton)
interview_service = InterviewService()
