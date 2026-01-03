"""
Google Gemini Embeddings Wrapper

This module provides a LangChain-compatible wrapper for Google Gemini embeddings.
"""

from typing import List

from google import genai
from google.genai import types
from langchain_core.embeddings import Embeddings

from dotenv import load_dotenv
import os

load_dotenv()  # Load environment variables from .env file



class GeminiEmbeddings(Embeddings):
    """
    Wrapper for Google Gemini embeddings that's compatible with LangChain.
    
    Uses gemini-embedding-001 model for generating text embeddings.
    """
    
    def __init__(
        self,
        model: str = "gemini-embedding-001",
        output_dimensionality: int = 768,
        api_key: str = os.getenv("GOOGLE_API_KEY") # type: ignore
    ):
        """
        Initialize Gemini embeddings.
        
        Args:
            model: Gemini embedding model name (default: gemini-embedding-001)
            output_dimensionality: Output dimension for embeddings (default: 768)
            api_key: Google API key (optional, will use GOOGLE_API_KEY env var)
        """
        self.model = model
        self.output_dimensionality = output_dimensionality
        
            
        if api_key:
            self.client = genai.Client(api_key=api_key)
        else:
            self.client = genai.Client()
        
        self.config = types.EmbedContentConfig(
            output_dimensionality=output_dimensionality
        )
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a list of documents.
        
        Args:
            texts: List of text documents to embed
            
        Returns:
            List of embeddings (each embedding is a list of floats)
        """
        embeddings = []
        
        for text in texts:
            result = self.client.models.embed_content(
                model=self.model,
                contents=text,
                config=self.config
            )
            
            # Ensure the API returned embeddings
            if not result or not getattr(result, "embeddings", None):
                raise RuntimeError("Gemini API did not return embeddings for the provided text input.")

            embedding_obj = result.embeddings[0] #type: ignore
            values = getattr(embedding_obj, "values", None)
            if not values:
                raise RuntimeError("Gemini API returned an embedding object without 'values'.")

            embeddings.append(list(values))
        
        return embeddings
    
    def embed_query(self, text: str) -> List[float]:
        """
        Embed a single query text.
        
        Args:
            text: Query text to embed
            
        Returns:
            Embedding as a list of floats
        """
        result = self.client.models.embed_content(
            model=self.model,
            contents=text,
            config=self.config
        )
        
        # Ensure the API returned embeddings
        if not result or not getattr(result, "embeddings", None):
            raise RuntimeError("Gemini API did not return embeddings for the provided query text.")

        embedding_obj = result.embeddings[0] #type: ignore
        values = getattr(embedding_obj, "values", None)
        if not values:
            raise RuntimeError("Gemini API returned an embedding object without 'values' for the query.")

        return list(values)
    
    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Async version of embed_documents.
        
        Args:
            texts: List of text documents to embed
            
        Returns:
            List of embeddings
        """
        # For now, use synchronous version
        # TODO: Implement async if needed
        return self.embed_documents(texts)
    
    async def aembed_query(self, text: str) -> List[float]:
        """
        Async version of embed_query.
        
        Args:
            text: Query text to embed
            
        Returns:
            Embedding as a list of floats
        """
        # For now, use synchronous version
        # TODO: Implement async if needed
        return self.embed_query(text)
