# Interview Service Flow
"""
CrewAI Flow-based interview service for the FastAPI backend.
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import List

from crewai import LLM
from pydantic import BaseModel
from crewai.flow import Flow, listen, start, and_

from interview_coach.crews.supervisor_crew.supervisor_crew import SupervisorCrew
from interview_coach.crews.interview_crew.interview_crew import InterviewCrew
from rag.rag_service import ResumeRAGService

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
    
    questions: List[str] = []


# ============================================================================
# Interview Flow
# ============================================================================

class GenerateInterviewQuestionsFlow(Flow[InterviewSessionState]):
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
        
        logger.info(f"✅ All {len(self.state.questions)} questions generated and ready")
