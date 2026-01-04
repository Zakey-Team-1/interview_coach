
import logging
from datetime import datetime
from pathlib import Path

from rag.rag_service import ResumeRAGService


logger = logging.getLogger(__name__)

class TestRAG:

    def __init__(self):
        self.session_id = "session_20231101_120000"
        self.resume_pdf_path = "/home/ibrahim/Downloads/CV - Base.pdf"
        self.rag_service = ResumeRAGService()
        self.resume_contexts = []
        self.interview_topics = [        "1. Architectural Design of RAG Systems: Describe your end-to-end process for building and productionalizing a RAG system using AWS Bedrock and LangChain. Specifically, explain how you select vector embedding strategies and optimize retrieval accuracy for domain-specific data. | Competency Assessed: AI Implementation & Vector Databases",
        "2. Infrastructure-as-Code and Scalability: Explain how you utilize Terraform or Pulumi to manage cloud-native infrastructure for ML applications. How do you handle environment drift and ensure high availability within a microservices architecture on AWS? | Competency Assessed: Infrastructure-as-Code (IaC) & AWS Ecosystem",
        "3. MLOps and Automated Lifecycle Management: Detail your experience developing CI/CD pipelines for automated model deployment. How do you integrate model versioning, monitoring/logging, and automated integration testing using SageMaker and Boto3? | Competency Assessed: MLOps, CI/CD, & Model Deployment",
        "4. Data Lake Governance and Engineering: You are tasked with architecting a data lake solution using Glue, Athena, and Lake Formation. How do you ensure data integrity, implement error-proofing strategies, and maintain performance for downstream AI products? | Competency Assessed: Data Engineering & AWS Data Lake Architecture",
        "5. Technical Visualization and Synthesis: Discuss a project where you performed complex exploratory data analysis (EDA). How did you apply Advanced Python (OOP) and tools like QuickSight or Tableau to synthesize datasets into actionable technical insights for stakeholders? | Competency Assessed: Data Visualization & Analytical Synthesis",
        "6. Advanced LLM Fine-tuning and Production Strategy: Describe your strategy for fine-tuning LLMs and managing their deployment. How do you balance the trade-offs between model performance, API latency, and cost-efficiency in a production-grade microservices environment? | Competency Assessed: LLM Fine-tuning & Productionalization"
        ]       
        


    def ingest_resume_to_rag(self):
        """Ingest resume PDF into RAG system if provided."""

        
        if not self.resume_pdf_path:
            logger.info("📝 No PDF provided - skipping RAG ingestion")
            return
        
        logger.info("🔄 Ingesting resume into RAG system...")
        pdf_path = Path(self.resume_pdf_path)
        
        if not pdf_path.exists():
            logger.warning(f"⚠️ Resume file not found: {pdf_path}")
            return
        
        time_stamp = datetime.now()
        
        try:
            result = self.rag_service.ingest_pdf_resume(
                pdf_path=str(pdf_path),
                session_id=self.session_id,
                metadata={
                    "candidate_name": "Ibrahim Younis",
                    "timestamp": time_stamp.isoformat()
                }
            )
            logger.info(f"✅ Resume ingested: {result['num_chunks']} chunks")
        except Exception as e:
            logger.error(f"⚠️ Error ingesting resume: {e}")
            
    def prepare_resume_contexts(self):
        """Retrieve resume context for each topic."""
        logger.info("📚 Retrieving resume context for each topic...")
        
        
        
        for topic in self.interview_topics:
            context = ""
            if self.resume_pdf_path:
                try:
                    results = self.rag_service.retrieve_context(
                        query=topic,
                        session_id=self.session_id,
                        k=3
                    )
                    context = "\n".join(results)
                except Exception as e:
                    logger.warning(f"RAG query failed for '{topic}': {e}")
            
            self.resume_contexts.append(context)
        
        logger.info("✅ Resume contexts retrieved")


def run_test_rag():
    test_rag = TestRAG()
    test_rag.ingest_resume_to_rag()
    test_rag.prepare_resume_contexts()
    for idx, context in enumerate(test_rag.resume_contexts):
        print(f"--- Context for Topic {idx+1} ---\n{context}\n")