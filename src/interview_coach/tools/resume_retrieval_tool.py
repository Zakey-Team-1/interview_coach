"""
Resume Retrieval Tool for CrewAI

This tool allows agents to retrieve relevant context from the candidate's resume
stored in the RAG system.
"""

from typing import Type

from pydantic import BaseModel, Field

from crewai.tools import BaseTool

from rag.rag_service import ResumeRAGService


class ResumeRetrievalInput(BaseModel):
    """Input schema for ResumeRetrievalTool."""
    
    query: str = Field(
        ..., 
        description="The question or topic to search for in the resume. "
                   "For example: 'technical skills', 'work experience at Google', "
                   "'education background', 'projects related to machine learning'"
    )
    num_results: int = Field(
        default=4,
        description="Number of relevant resume sections to retrieve (default: 4)"
    )


class ResumeRetrievalTool(BaseTool):
    """
    Tool for retrieving relevant information from a candidate's resume.
    
    This tool uses RAG to fetch only the relevant portions of the resume
    based on the query, avoiding the need to include the entire resume
    in every prompt.
    """
    
    name: str = "Resume Retrieval Tool"
    description: str = (
        "Retrieves relevant sections from the candidate's resume based on a query. "
        "Use this tool when you need specific information from the resume such as "
        "work experience, skills, education, projects, or achievements. "
        "This is more efficient than reading the entire resume."
    )
    args_schema: Type[BaseModel] = ResumeRetrievalInput
    
    # RAG service instance (can be injected or created)
    rag_service: ResumeRAGService
    session_id: str = None

    def __init__(self, rag_service: ResumeRAGService | None = None, session_id: str | None = None, **kwargs):
        """
        Initialize the tool with RAG service.
        
        Args:
            rag_service: Instance of ResumeRAGService (will be enforced)
            session_id: Current session ID
        """
        super().__init__(**kwargs)
        # Always use the ResumeRAGService implementation. If the provided
        # rag_service is not an instance of ResumeRAGService, replace it.
        if not isinstance(rag_service, ResumeRAGService):
            self.rag_service = ResumeRAGService()
        else:
            self.rag_service = rag_service

        # allow session_id to be optional
        self.session_id = session_id or "default"
    
    def _run(self, query: str, num_results: int = 4) -> str:
        """
        Retrieve relevant resume sections based on the query.
        
        Args:
            query: The question or topic to search for
            num_results: Number of results to retrieve
            
        Returns:
            Relevant resume sections as formatted text
        """
        try:
            # Retrieve relevant chunks
            contexts = self.rag_service.retrieve_context(
                query=query,
                k=num_results,
                session_id=self.session_id
            )
            
            if not contexts:
                return "No relevant information found in the resume for this query."
            
            # Format the results
            result = f"Relevant Resume Sections for '{query}':\n\n"
            for i, context in enumerate(contexts, 1):
                result += f"Section {i}:\n{context}\n\n"
            
            return result.strip()
            
        except Exception as e:
            return f"Error retrieving resume information: {str(e)}"
