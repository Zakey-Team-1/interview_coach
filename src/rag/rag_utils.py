"""
Utility functions for RAG system management and testing.
"""

from pathlib import Path
from rag.rag_service import ResumeRAGService


def test_rag_ingestion(pdf_path: str):
    """
    Test PDF ingestion and retrieval.
    
    Args:
        pdf_path: Path to a test PDF resume
    """
    print("🧪 Testing RAG System")
    print("=" * 80)
    
    # Initialize service
    rag_service = ResumeRAGService()
    
    # Ingest PDF
    print(f"\n1. Ingesting PDF: {pdf_path}")
    result = rag_service.ingest_pdf_resume(
        pdf_path=pdf_path,
        session_id="test_session_001"
    )
    
    print(f"\n   Results:")
    print(f"   - Text length: {result['text_length']} characters")
    print(f"   - Number of chunks: {result['num_chunks']}")
    print(f"   - File hash: {result['file_hash'][:16]}...")
    
    # Test retrieval
    print(f"\n2. Testing retrieval...")
    
    test_queries = [
        "technical skills and programming languages",
        "work experience and previous roles",
        "education background and degrees",
        "notable projects or achievements"
    ]
    
    for query in test_queries:
        print(f"\n   Query: '{query}'")
        contexts = rag_service.retrieve_context(query, k=2)
        
        if contexts:
            print(f"   Found {len(contexts)} relevant sections:")
            for i, context in enumerate(contexts, 1):
                preview = context[:150].replace('\n', ' ')
                print(f"      {i}. {preview}...")
        else:
            print("   No results found")
    
    print("\n" + "=" * 80)
    print("✅ RAG system test completed!")


def list_stored_sessions():
    """
    List all stored RAG sessions.
    """
    rag_service = ResumeRAGService()
    persist_dir = rag_service.persist_directory
    
    if not persist_dir.exists():
        print("No RAG database found.")
        return
    
    # List ChromaDB collections
    print("📚 Stored RAG Sessions:")
    print("=" * 80)
    
    collections = list(persist_dir.glob("*"))
    
    if not collections:
        print("No sessions found.")
    else:
        for i, collection in enumerate(collections, 1):
            print(f"{i}. {collection.name}")
    
    print("=" * 80)


def clear_all_sessions():
    """
    Clear all RAG sessions (use with caution).
    """
    import shutil
    
    rag_service = ResumeRAGService()
    persist_dir = rag_service.persist_directory
    
    if not persist_dir.exists():
        print("No RAG database found.")
        return
    
    confirm = input("⚠️  Are you sure you want to delete all RAG sessions? (yes/no): ")
    
    if confirm.lower() == 'yes':
        shutil.rmtree(persist_dir)
        print("✅ All RAG sessions cleared.")
    else:
        print("❌ Operation cancelled.")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python rag_utils.py test <pdf_path>    - Test RAG with a PDF")
        print("  python rag_utils.py list               - List stored sessions")
        print("  python rag_utils.py clear              - Clear all sessions")
    else:
        command = sys.argv[1]
        
        if command == "test" and len(sys.argv) >= 3:
            test_rag_ingestion(sys.argv[2])
        elif command == "list":
            list_stored_sessions()
        elif command == "clear":
            clear_all_sessions()
        else:
            print("Invalid command or missing arguments.")
