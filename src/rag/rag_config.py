"""
RAG System Configuration

Centralized configuration for the RAG system.
Modify these settings to customize RAG behavior.
"""

# ============================================================================
# PDF Processing Configuration
# ============================================================================

PDF_CONFIG = {
    # Maximum file size in MB
    "max_file_size_mb": 10,
    
    # Supported file extensions
    "supported_extensions": [".pdf"],
}

# ============================================================================
# Text Chunking Configuration
# ============================================================================

CHUNKING_CONFIG = {
    # Size of each text chunk in characters
    "chunk_size": 1000,
    
    # Overlap between chunks in characters
    # Higher overlap can improve context continuity
    "chunk_overlap": 200,
    
    # Text separators (in order of preference)
    "separators": ["\n\n", "\n", ". ", " ", ""],
}

# ============================================================================
# Embedding Configuration
# ============================================================================

EMBEDDING_CONFIG = {
    # Google Gemini embedding model
    # Options: "gemini-embedding-001", "text-embedding-004"
    "model": "gemini-embedding-001",
    
    # Output dimensionality for embeddings
    # Options: 768 (default), 256, 512
    "output_dimensionality": 768,
    
    # Batch size for embedding generation
    "batch_size": 100,
}

# ============================================================================
# Vector Store Configuration
# ============================================================================

VECTORSTORE_CONFIG = {
    # Directory to persist vector database
    "persist_directory": "./chroma_db",
    
    # Collection name prefix
    "collection_prefix": "resume",
    
    # Distance metric for similarity search
    # Options: "cosine", "l2", "ip" (inner product)
    "distance_metric": "cosine",
}

# ============================================================================
# Retrieval Configuration
# ============================================================================

RETRIEVAL_CONFIG = {
    # Default number of chunks to retrieve
    "default_k": 4,
    
    # Maximum number of chunks to retrieve
    "max_k": 10,
    
    # Minimum similarity score (0-1)
    # Lower = more permissive, Higher = more strict
    "min_similarity_score": 0.0,
    
    # Enable MMR (Maximal Marginal Relevance) for diversity
    "use_mmr": False,
    
    # MMR diversity factor (0-1)
    # 0 = maximum relevance, 1 = maximum diversity
    "mmr_diversity": 0.3,
}

# ============================================================================
# Session Management
# ============================================================================

SESSION_CONFIG = {
    # Auto-delete sessions older than N days (0 = never)
    "auto_delete_days": 0,
    
    # Maximum number of sessions to keep (0 = unlimited)
    "max_sessions": 0,
}

# ============================================================================
# Performance Configuration
# ============================================================================

PERFORMANCE_CONFIG = {
    # Enable caching of embeddings
    "cache_embeddings": True,
    
    # Cache directory
    "cache_directory": "./.embedding_cache",
    
    # Enable query result caching
    "cache_results": True,
    
    # Result cache TTL in seconds
    "cache_ttl": 3600,
}

# ============================================================================
# Logging Configuration
# ============================================================================

LOGGING_CONFIG = {
    # Enable detailed logging
    "verbose": True,
    
    # Log file path (None = no file logging)
    "log_file": None,
    
    # Log level: "DEBUG", "INFO", "WARNING", "ERROR"
    "log_level": "INFO",
}

# ============================================================================
# Advanced Features
# ============================================================================

ADVANCED_CONFIG = {
    # Enable hybrid search (keyword + semantic)
    "hybrid_search": False,
    
    # Keyword search weight (0-1) when using hybrid
    "keyword_weight": 0.3,
    
    # Enable re-ranking of results
    "enable_reranking": False,
    
    # Re-ranking model (if enabled)
    "reranking_model": None,
}

# ============================================================================
# Helper Functions
# ============================================================================

def get_config(section: str) -> dict:
    """
    Get configuration for a specific section.
    
    Args:
        section: Configuration section name
        
    Returns:
        Configuration dictionary
    """
    configs = {
        "pdf": PDF_CONFIG,
        "chunking": CHUNKING_CONFIG,
        "embedding": EMBEDDING_CONFIG,
        "vectorstore": VECTORSTORE_CONFIG,
        "retrieval": RETRIEVAL_CONFIG,
        "session": SESSION_CONFIG,
        "performance": PERFORMANCE_CONFIG,
        "logging": LOGGING_CONFIG,
        "advanced": ADVANCED_CONFIG,
    }
    
    return configs.get(section, {})


def update_config(section: str, key: str, value):
    """
    Update a configuration value.
    
    Args:
        section: Configuration section name
        key: Configuration key
        value: New value
    """
    configs = {
        "pdf": PDF_CONFIG,
        "chunking": CHUNKING_CONFIG,
        "embedding": EMBEDDING_CONFIG,
        "vectorstore": VECTORSTORE_CONFIG,
        "retrieval": RETRIEVAL_CONFIG,
        "session": SESSION_CONFIG,
        "performance": PERFORMANCE_CONFIG,
        "logging": LOGGING_CONFIG,
        "advanced": ADVANCED_CONFIG,
    }
    
    if section in configs:
        configs[section][key] = value
    else:
        raise ValueError(f"Unknown configuration section: {section}")


def print_all_configs():
    """Print all configuration sections."""
    sections = [
        ("PDF Processing", PDF_CONFIG),
        ("Text Chunking", CHUNKING_CONFIG),
        ("Embedding", EMBEDDING_CONFIG),
        ("Vector Store", VECTORSTORE_CONFIG),
        ("Retrieval", RETRIEVAL_CONFIG),
        ("Session Management", SESSION_CONFIG),
        ("Performance", PERFORMANCE_CONFIG),
        ("Logging", LOGGING_CONFIG),
        ("Advanced Features", ADVANCED_CONFIG),
    ]
    
    print("=" * 80)
    print("RAG SYSTEM CONFIGURATION")
    print("=" * 80)
    
    for section_name, config in sections:
        print(f"\n{section_name}:")
        print("-" * 80)
        for key, value in config.items():
            print(f"  {key}: {value}")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    # Print all configurations when run directly
    print_all_configs()
