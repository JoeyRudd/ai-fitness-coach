#!/usr/bin/env python3
"""Test script for hybrid RRF retrieval."""

import os
from app.services.rag_index import RAGIndex

def test_hybrid_retrieval():
    """Test the hybrid RRF retrieval method."""
    # Initialize RAG index
    rag = RAGIndex()
    
    # Load knowledge base
    kb_path = os.path.join(os.path.dirname(__file__), '..', '..', 'knowledge_base')
    rag.load(kb_path)
    
    # Build index
    rag.build()
    
    # Test queries
    test_queries = [
        "protein intake",
        "cardio frequency", 
        "strength training basics",
        "recovery rest days"
    ]
    
    for query in test_queries:
        # Test hybrid method
        hybrid_results = rag.hybrid_retrieve(query, k=2)
        assert len(hybrid_results) > 0, f"Hybrid RRF should return results for query: {query}"
        
        # Test regular method for comparison
        regular_results = rag.retrieve(query, k=2)
        assert len(regular_results) > 0, f"Regular retrieval should return results for query: {query}"
        
        # Both methods should return results
        assert len(hybrid_results) <= 2, f"Hybrid should respect k=2 limit for query: {query}"
        assert len(regular_results) <= 2, f"Regular should respect k=2 limit for query: {query}"

def test_hybrid_method_available():
    """Test that hybrid_retrieve method exists and is callable."""
    rag = RAGIndex()
    assert hasattr(rag, 'hybrid_retrieve'), "RAGIndex should have hybrid_retrieve method"
    assert callable(rag.hybrid_retrieve), "hybrid_retrieve should be callable"
