#!/usr/bin/env python
"""
Interview Coach - Main Flow Module

This module provides the CrewAI Flow-based interview system.
For API-based interviews, use the FastAPI server instead:
    python -m interview_coach.api.main
    # or: uvicorn interview_coach.api.main:app --reload
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from crewai import LLM
from pydantic import BaseModel

from crewai.flow import Flow, listen, start, and_

from interview_coach.crews.interview_crew.interview_crew import InterviewCrew
from interview_coach.crews.supervisor_crew.supervisor_crew import SupervisorCrew
from interview_coach.crews.evaluation_crew.evaluation_crew import EvaluationCrew
from rag.rag_service import ResumeRAGService


class InterviewState(BaseModel):
    # Input data
    resume_pdf_path: str = ""  # Path to PDF resume
    job_description: str = ""
    candidate_name: str = ""
    
    # Interview session data
    interview_topics: List[str] = []
    resume_contexts: List[str] = []  # Resume context for each topic
    questions: List[str] = []  # Pre-generated questions
    interview_transcript: str = ""
    interview_roadmap: str = ""
    
    # Evaluation results
    evaluation_report: str = ""
    scores: dict = {}
    
    # Metadata
    session_id: str = ""
    timestamp: str = ""


class InterviewCoachFlow(Flow[InterviewState]):
    """
    Main flow for the AI Interview Coach system.
    
    This flow orchestrates:
    1. Ingesting resume into RAG system (if PDF provided)
    2. Conducting an interview based on resume and job description
    3. Evaluating the candidate's performance
    4. Generating reports and saving results
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initialize RAG service
        self.rag_service = ResumeRAGService()

    @start()
    def prepare_interview(self, crewai_trigger_payload: dict):
        """
        Initialize the interview session with candidate data.
        
        Expected inputs:
        - resume_pdf_path: Path to PDF resume
        - job_description: The target job description
        - candidate_name: The candidate's name (optional)
        """
        print("🚀 Preparing interview session...")

        # Use trigger payload if available
        if crewai_trigger_payload:
            self.state.resume_pdf_path = crewai_trigger_payload.get('resume_pdf_path', '')
            self.state.job_description = crewai_trigger_payload.get('job_description', '')
            self.state.candidate_name = crewai_trigger_payload.get('candidate_name', 'Candidate')
            print(f"✅ Loaded data for: {self.state.candidate_name}")
        else:
            # Default/demo mode
            print("⚠️  No payload provided. Using demo mode.")
            self.state.job_description = "Sample job description"
            self.state.candidate_name = "Demo Candidate"
        
        # Generate session metadata
        self.state.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.state.timestamp = datetime.now().isoformat()
        
        print(f"📋 Session ID: {self.state.session_id}")
    
    @listen(prepare_interview)
    def preprocess_job_description(self):
        """
        Clean and preprocess the job description text.
        """
        print("\n🧹 Cleaning job description...")
        
        llm = LLM(
            model="gemini/gemini-3-flash-preview",
        )
        
        response = llm.call(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a text preprocessing assistant. "
                        "Your task is to clean and preprocess job description text by removing all "
                        "unnecessary details, we are interested in the technical aspects only."
                        "Get rid of all legal and HR related content."
                    )
                },
                {
                    "role": "user",
                    "content": f"Please clean the following job description:\n\n{self.state.job_description}"
                }
            ],
        )
        

        self.state.job_description = response
        print("✅ Job description cleaned")

    @listen(prepare_interview)
    def ingest_resume_to_rag(self):
        """
        Ingest the resume into RAG system if PDF path is provided.
        This allows for efficient retrieval of resume context during the interview.
        """
        # Check if PDF path is provided
        if self.state.resume_pdf_path:
            print("\n🔄 Ingesting resume into RAG system...")
            
            pdf_path = Path(self.state.resume_pdf_path)
            
            if not pdf_path.exists():
                print(f"⚠️  Warning: PDF file not found at {pdf_path}")
                print("   Continuing without RAG...")
                return
            
            try:
                # Ingest PDF into RAG
                result = self.rag_service.ingest_pdf_resume(
                    pdf_path=str(pdf_path),
                    session_id=self.state.session_id,
                    metadata={
                        "candidate_name": self.state.candidate_name,
                        "timestamp": self.state.timestamp
                    }
                )
                                
                
                print(f"✅ Resume ingested: {result['num_chunks']} chunks created")
                print(f"   RAG is now active for session {self.state.session_id}")
                
            except Exception as e:
                print(f"⚠️  Error ingesting resume: {e}")
                print("   Continuing without RAG...")
        else:
            print("\n📝 No PDF provided - using text resume directly")
            
            
    @listen(and_(ingest_resume_to_rag, preprocess_job_description))
    def create_interview_roadmap(self):
        """
        Use the SupervisorCrew to create an interview roadmap based on the job description.
        """
        print("\n🗺️  Creating interview roadmap...")
        
        result = (
            SupervisorCrew()
            .crew()
            .kickoff(inputs={
                "job_description": self.state.job_description
            })
        )
        
        # Extract interview topics from the result
        interview_topics_model = result.outputs.get("create_interview_roadmap")  # type: ignore
        if interview_topics_model and hasattr(interview_topics_model, 'interview_topics'):
            self.state.interview_topics = interview_topics_model.interview_topics
            self.state.interview_roadmap = "\n".join(
                [f"- {topic}" for topic in self.state.interview_topics]
            )
            print("✅ Interview roadmap created:")
            for topic in self.state.interview_topics:
                print(f"   • {topic}")
        else:
            print("⚠️  Failed to extract interview topics from roadmap")
            self.state.interview_roadmap = ""

    @listen(create_interview_roadmap)
    def prepare_resume_contexts(self):
        """Retrieve resume context for each topic."""
        print("\n📚 Retrieving resume context for each topic...")
        
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
                    print(f"   ⚠️ RAG query failed for '{topic}': {e}")
            
            self.state.resume_contexts.append(context)
        
        print("✅ Resume contexts retrieved")
    
    @listen(prepare_resume_contexts)
    async def generate_all_questions(self):
        """Generate all interview questions upfront in parallel."""
        print("\n❓ Generating all interview questions in parallel...")
        
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
        full_transcript = []
        
        for i, result in enumerate(results, 1):
            # Handle result extraction
            if hasattr(result, 'raw'):
                question_text = result.raw.strip()
            else:
                question_text = str(result).strip()
            
            self.state.questions.append(question_text)
            full_transcript.append(f"\n[QUESTION {i}]\n{question_text}\n")
            print(f"   ✓ Question {i}: {question_text[:60]}...")
        
        self.state.interview_transcript = "\n".join(full_transcript)
        print(f"✅ All {len(self.state.questions)} questions generated and ready")

    # @listen(generate_all_questions)
    # def evaluate_performance(self):
    #     """
    #     Run the evaluation crew to analyze the interview performance.
    #     """
    #     print("\n📊 Evaluating interview performance...")
        
    #     result = (
    #         EvaluationCrew()
    #         .crew()
    #         .kickoff(inputs={
    #             "interview_transcript": self.state.interview_transcript,
    #             "job_description": self.state.job_description
    #         })
    #     )

    #     self.state.evaluation_report = result.raw # type: ignore
    #     print("✅ Evaluation completed")

    # @listen(evaluate_performance)
    # def save_results(self):
    #     """
    #     Save interview results and evaluation to files.
    #     """
    #     print("\n💾 Saving results...")
        
    #     # Create results directory if it doesn't exist
    #     results_dir = Path("interview_results")
    #     results_dir.mkdir(exist_ok=True)
        
    #     session_dir = results_dir / self.state.session_id
    #     session_dir.mkdir(exist_ok=True)
        
    #     # Save interview transcript
    #     transcript_file = session_dir / "interview_transcript.txt"
    #     with open(transcript_file, "w") as f:
    #         f.write(f"Interview Session: {self.state.session_id}\n")
    #         f.write(f"Candidate: {self.state.candidate_name}\n")
    #         f.write(f"Timestamp: {self.state.timestamp}\n")
    #         f.write("\n" + "="*80 + "\n\n")
    #         f.write(self.state.interview_transcript)
        
    #     # Save evaluation report
    #     evaluation_file = session_dir / "evaluation_report.txt"
    #     with open(evaluation_file, "w") as f:
    #         f.write(f"Evaluation Report: {self.state.session_id}\n")
    #         f.write(f"Candidate: {self.state.candidate_name}\n")
    #         f.write(f"Timestamp: {self.state.timestamp}\n")
    #         f.write("\n" + "="*80 + "\n\n")
    #         f.write(self.state.evaluation_report)
        
    #     # Save metadata as JSON
    #     metadata_file = session_dir / "session_metadata.json"
    #     with open(metadata_file, "w") as f:
    #         json.dump({
    #             "session_id": self.state.session_id,
    #             "candidate_name": self.state.candidate_name,
    #             "timestamp": self.state.timestamp,
    #             "jd_length": len(self.state.job_description),
    #             "transcript_length": len(self.state.interview_transcript),
    #             "scores": self.state.scores,
    #             "resume_pdf_path": self.state.resume_pdf_path
    #         }, f, indent=2)
        
    #     print(f"✅ Results saved to: {session_dir}")
    #     print(f"   - Interview transcript: {transcript_file.name}")
    #     print(f"   - Evaluation report: {evaluation_file.name}")
    #     print(f"   - Session metadata: {metadata_file.name}")


def kickoff():
    """
    Run the interview coach flow with default/demo mode.
    """
    flow = InterviewCoachFlow()
    flow.kickoff()


def plot():
    """
    Generate a visual plot of the interview coach flow.
    """
    flow = InterviewCoachFlow()
    flow.plot()


def run_with_trigger(payload: Optional[dict] = None):
    """
    Run the interview coach flow with a trigger payload.
    
    Args:
        payload: Dictionary containing:
            - resume_pdf_path: Path to candidate's resume PDF
            - job_description: Job description text
            - candidate_name: Name of the candidate
    """
    flow = InterviewCoachFlow()
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
        kickoff()
