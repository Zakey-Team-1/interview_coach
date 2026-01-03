"""
RAG Service for Resume Processing

This module handles:
- PDF ingestion and parsing
- Text chunking and embedding
- Vector storage and retrieval
- Context retrieval for interview questions
"""

import hashlib
from pathlib import Path
from typing import List, Optional

import pymupdf  # PyMuPDF for PDF processing
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma


from rag.gemini_embeddings import GeminiEmbeddings
from rag.rag_config import (
    CHUNKING_CONFIG,
    EMBEDDING_CONFIG,
    VECTORSTORE_CONFIG,
    RETRIEVAL_CONFIG
)


class ResumeRAGService:
    """
    RAG service for managing resume embeddings and retrieval.
    """
    
    def __init__(self, persist_directory: Optional[str] = None):
        """
        Initialize the RAG service.
        
        Args:
            persist_directory: Directory to persist the vector database
                             (defaults to value from config)
        """
        if persist_directory is None:
            persist_directory = VECTORSTORE_CONFIG["persist_directory"]
        
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize Gemini embeddings
        self.embeddings = GeminiEmbeddings(
            model=EMBEDDING_CONFIG["model"],
            output_dimensionality=EMBEDDING_CONFIG["output_dimensionality"]
        )
        
        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNKING_CONFIG["chunk_size"],
            chunk_overlap=CHUNKING_CONFIG["chunk_overlap"],
            length_function=len,
            separators=CHUNKING_CONFIG["separators"]
        )
        
        # Vector store will be initialized per session
        self.vectorstore = None
        self.current_session_id = None
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        Extract text content from a PDF file.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Extracted text content
        """
        doc = pymupdf.open(pdf_path)
        text = ""
        
        for page in doc:
            text += page.get_text() + "\n"  # type: ignore
        
        doc.close()
        return text
    
    def process_resume(self, resume_content: str, session_id: str, metadata: Optional[dict] = None) -> int:
        """
        Process resume text and create embeddings.
        
        Args:
            resume_content: The resume text content
            session_id: Unique session identifier
            metadata: Additional metadata to attach to chunks
            
        Returns:
            Number of chunks created
        """
        # Create chunks
        chunks = self.text_splitter.split_text(resume_content)
        
        # Prepare metadata
        if metadata is None:
            metadata = {}
        
        metadata.update({
            "session_id": session_id,
            "source": "resume",
            "total_chunks": len(chunks)
        })
        
        # Create metadata for each chunk
        metadatas = [
            {**metadata, "chunk_id": i} 
            for i in range(len(chunks))
        ]
        
        # Create or update vector store for this session
        collection_name = self._get_collection_name(session_id)
        
        self.vectorstore = Chroma.from_texts(
            texts=chunks,
            embedding=self.embeddings,
            metadatas=metadatas,
            collection_name=collection_name,
            persist_directory=str(self.persist_directory)
        )
        
        self.current_session_id = session_id
        
        print(f"✅ Processed resume into {len(chunks)} chunks")
        return len(chunks)
    
    def ingest_pdf_resume(self, pdf_path: str, session_id: str, metadata: Optional[dict] = None) -> dict:
        """
        Complete pipeline: Extract text from PDF and process into RAG.
        
        Args:
            pdf_path: Path to the PDF resume file
            session_id: Unique session identifier
            metadata: Additional metadata
            
        Returns:
            Dictionary with processing results
        """
        # Extract text from PDF
        print(f"📄 Extracting text from PDF: {pdf_path}")
        resume_text = self.extract_text_from_pdf(pdf_path)
        
        # Process the text
        num_chunks = self.process_resume(resume_text, session_id, metadata)
        
        # Calculate file hash for tracking
        file_hash = self._calculate_file_hash(pdf_path)
        
        return {
            "session_id": session_id,
            "pdf_path": pdf_path,
            "file_hash": file_hash,
            "num_chunks": num_chunks,
            "text_length": len(resume_text)
        }
    
    def retrieve_context(self, query: str, k: Optional[int] = None, session_id: Optional[str] = None) -> List[str]:
        """
        Retrieve relevant resume chunks based on a query.
        
        Args:
            query: The query/question to search for
            k: Number of chunks to retrieve (defaults to config value)
            session_id: Session ID to retrieve from (uses current if None)
            
        Returns:
            List of relevant text chunks
        """
        # Set default if k is None/0 and enforce maximum
        k = min(k or RETRIEVAL_CONFIG["default_k"], RETRIEVAL_CONFIG["max_k"])

        if session_id and session_id != self.current_session_id:
            self._load_session(session_id)
        
        if not self.vectorstore:
            raise ValueError("No vector store loaded. Please ingest a resume first.")
        
        # Perform similarity search
        results = self.vectorstore.similarity_search(query, k=k)
        
        # Extract text from results
        contexts = [doc.page_content for doc in results]
        
        return contexts
        
    def _load_session(self, session_id: str):
        """
        Load a specific session's vector store.
        
        Args:
            session_id: Session ID to load
        """
        collection_name = self._get_collection_name(session_id)
        
        self.vectorstore = Chroma(
            collection_name=collection_name,
            embedding_function=self.embeddings,
            persist_directory=str(self.persist_directory)
        )
        
        self.current_session_id = session_id
    
    def _get_collection_name(self, session_id: str) -> str:
        """
        Generate a collection name from session ID.
        
        Args:
            session_id: Session ID
            
        Returns:
            Collection name
        """
        # Create a valid collection name (alphanumeric + underscores)
        return f"resume_{session_id.replace('-', '_')}"
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """
        Calculate SHA256 hash of a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Hex digest of the file hash
        """
        sha256_hash = hashlib.sha256()
        
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        
        return sha256_hash.hexdigest()
    
    def clear_session(self, session_id: str):
        """
        Clear/delete a session's data from the vector store.
        
        Args:
            session_id: Session ID to clear
        """
        collection_name = self._get_collection_name(session_id)
        
        # Delete the collection
        try:
            client = self.vectorstore._client if self.vectorstore else Chroma._client # type: ignore
            client.delete_collection(collection_name)
            print(f"✅ Cleared session: {session_id}")
        except Exception as e:
            print(f"⚠️  Could not clear session {session_id}: {e}")
