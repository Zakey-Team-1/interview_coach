# Interview Service Flow
"""
CrewAI Flow-based interview service for the FastAPI backend.
Provides step-by-step interview execution with user response handling.
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from crewai import LLM
from pydantic import BaseModel
from crewai.flow import Flow, listen, start, and_

from interview_coach.crews.supervisor_crew.supervisor_crew import SupervisorCrew
from interview_coach.crews.interview_crew.interview_crew import InterviewCrew
from interview_coach.crews.evaluation_crew.evaluation_crew import EvaluationCrew
from rag.rag_service import ResumeRAGService
from interview_coach.api.session_manager import session_manager, InterviewSession

logger = logging.getLogger(__name__)


# ============================================================================
# State Models
# ============================================================================

class InterviewSessionState(BaseModel):
    """State for an API-driven interview session."""
    # Input data
    resume_pdf_path: str = ""
    job_description: str = ""
    candidate_name: str = "Candidate"
    
    # Session metadata
    session_id: str = ""
    timestamp: str = ""
    
    # Interview roadmap
    interview_topics: List[str] = []
    resume_contexts: List[str] = []
    
    # Pre-generated questions (generated all in parallel after roadmap)
    questions: List[str] = []
    
    # Current interview progress
    current_question_index: int = 0
    current_question: str = ""
    
    # Transcript: list of (question, response) pairs
    transcript: List[dict] = []
    
    # Candidate response (set externally via API)
    pending_response: Optional[str] = None
    
    # Evaluation
    evaluation_report: str = ""
    
    # Status flags
    is_initialized: bool = False
    is_interview_complete: bool = False
    is_evaluated: bool = False


# ============================================================================
# Interview Flow
# ============================================================================

class InterviewServiceFlow(Flow[InterviewSessionState]):
    """
    CrewAI Flow for API-driven interview sessions.
    
    This flow is designed to work with the FastAPI backend:
    1. Initialize session with JD and resume
    2. Generate interview roadmap
    3. For each question:
       - Generate question
       - Wait for candidate response (via API)
       - Record transcript
    4. Run evaluation
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rag_service = ResumeRAGService()
        self.llm = LLM(model="gemini/gemini-3-flash-preview")
    
    # ========================================================================
    # Initialization Phase
    # ========================================================================
    
    @start()
    def prepare_session(self, payload: dict):
        """Initialize the interview session with provided data."""
        logger.info("🚀 Preparing interview session...")
        
        # Extract payload data
        self.state.resume_pdf_path = payload.get('resume_pdf_path', '')
        self.state.job_description = payload.get('job_description', '')
        self.state.candidate_name = payload.get('candidate_name', 'Candidate')
        
        # Generate session metadata
        self.state.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.state.timestamp = datetime.now().isoformat()
        
        logger.info(f"📋 Session ID: {self.state.session_id}")
        logger.info(f"👤 Candidate: {self.state.candidate_name}")
    
    @listen(prepare_session)
    def preprocess_job_description(self):
        """Clean and preprocess the job description."""
        logger.info("🧹 Cleaning job description...")
        
        response = self.llm.call(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a text preprocessing assistant. "
                        "Clean and preprocess job description text by removing all "
                        "unnecessary details. Focus on technical aspects only. "
                        "Remove all legal and HR-related content."
                    )
                },
                {
                    "role": "user",
                    "content": f"Please clean the following job description:\n\n{self.state.job_description}"
                }
            ],
        )
        
        self.state.job_description = response
        logger.info("✅ Job description cleaned")
    
    @listen(prepare_session)
    def ingest_resume_to_rag(self):
        """Ingest resume PDF into RAG system if provided."""
        if not self.state.resume_pdf_path:
            logger.info("📝 No PDF provided - skipping RAG ingestion")
            return
        
        logger.info("🔄 Ingesting resume into RAG system...")
        pdf_path = Path(self.state.resume_pdf_path)
        
        if not pdf_path.exists():
            logger.warning(f"⚠️ Resume file not found: {pdf_path}")
            return
        
        try:
            result = self.rag_service.ingest_pdf_resume(
                pdf_path=str(pdf_path),
                session_id=self.state.session_id,
                metadata={
                    "candidate_name": self.state.candidate_name,
                    "timestamp": self.state.timestamp
                }
            )
            logger.info(f"✅ Resume ingested: {result['num_chunks']} chunks")
        except Exception as e:
            logger.error(f"⚠️ Error ingesting resume: {e}")
    
    @listen(and_(ingest_resume_to_rag, preprocess_job_description))
    def create_interview_roadmap(self):
        """Generate interview roadmap using SupervisorCrew."""
        logger.info("🗺️ Creating interview roadmap...")
        
        result = (
            SupervisorCrew()
            .crew()
            .kickoff(inputs={"job_description": self.state.job_description})
        )
        
        # Extract topics from result
        try:
            # Access the pydantic output from the task
            interview_topics_model = result.outputs.get("create_interview_roadmap")  # type: ignore
            if interview_topics_model and hasattr(interview_topics_model, 'interview_topics'):
                self.state.interview_topics = interview_topics_model.interview_topics
                logger.info(f"✅ Created {len(self.state.interview_topics)} interview topics")
                for topic in self.state.interview_topics:
                    logger.info(f"   • {topic}")
            else:
                logger.warning("⚠️ Failed to extract structured topics")
                self.state.interview_topics = []
        except Exception as e:
            logger.error(f"⚠️ Error extracting topics: {e}")
            self.state.interview_topics = []
    
    @listen(create_interview_roadmap)
    def prepare_resume_contexts(self):
        """Retrieve resume context for each topic."""
        logger.info("📚 Retrieving resume context for each topic...")
        
        self.state.resume_contexts = []
        
        for topic in self.state.interview_topics:
            context = ""
            if self.state.resume_pdf_path:
                try:
                    results = self.rag_service.retrieve_context(
                        query=topic,
                        session_id=self.state.session_id,
                        k=3
                    )
                    context = "\n".join(results)
                except Exception as e:
                    logger.warning(f"RAG query failed for '{topic}': {e}")
            
            self.state.resume_contexts.append(context)
        
        logger.info("✅ Resume contexts retrieved")
    
    @listen(prepare_resume_contexts)
    async def generate_all_questions(self):
        """Generate all interview questions upfront in parallel."""
        logger.info("❓ Generating all interview questions in parallel...")
        
        tasks = []
        
        # Create async tasks for each topic
        for i, topic in enumerate(self.state.interview_topics):
            resume_context = (
                self.state.resume_contexts[i]
                if i < len(self.state.resume_contexts)
                else ""
            )
            
            inputs = {
                "current_question": topic,
                "resume_context": resume_context or "No resume context available.",
                "candidate_name": self.state.candidate_name,
                "session_id": self.state.session_id,
            }
            
            # Use kickoff_async for parallel execution
            tasks.append(InterviewCrew().crew().kickoff_async(inputs=inputs))
            
        # Wait for all generations to complete
        results = await asyncio.gather(*tasks)
        
        self.state.questions = []
        for result in results:
            # Handle result extraction (CrewOutput usually has .raw)
            if hasattr(result, 'raw'):
                question_text = result.raw.strip()
            else:
                question_text = str(result).strip()
            
            self.state.questions.append(question_text)
            logger.info(f"      ✓ {question_text[:80]}...")
        
        self.state.is_initialized = True
        logger.info(f"✅ All {len(self.state.questions)} questions generated and ready")
        

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
        self._sessions: dict[str, InterviewServiceFlow] = {}
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
        flow = InterviewServiceFlow()
        
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
        
        # Set interview topics in session_manager
        session_manager.set_interview_topics(
            session_id=session_id,
            topics=flow.state.interview_topics,
            resume_contexts=flow.state.resume_contexts
        )
        
        logger.info(f"✅ Session initialized: {session_id} with {len(flow.state.questions)} questions")
        
        return session
    
    async def generate_question(
        self,
        session_id: str,
    ) -> str:
        """
        Retrieve the next pre-generated interview question.
        
        All questions are generated upfront during initialization.
        This method simply retrieves them from state.
        
        Returns just the question text string.
        """
        flow = self._sessions.get(session_id)
        if not flow:
            raise ValueError(f"Session not found: {session_id}")
        
        # Get session from session_manager
        session = session_manager.get_session_or_raise(session_id)
        
        # Get current question from pre-generated list
        if session.current_question_index >= len(flow.state.questions):
            raise ValueError("No more questions available")
        
        # Return pre-generated question
        question_text = flow.state.questions[session.current_question_index]
        logger.info(f"📝 Question {session.current_question_index + 1}/{len(flow.state.questions)}: {question_text[:80]}...")
        
        return question_text
    
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
