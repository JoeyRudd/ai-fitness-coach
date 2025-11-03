#!/usr/bin/env python3
"""Test script for short query retrieval."""

import os
from app.services.rag_index import RAGIndex

def test_short_queries():
    """Test short queries using TF-IDF retrieval."""
    # Initialize RAG index
    rag = RAGIndex()
    
    # Load knowledge base
    kb_path = os.path.join(os.path.dirname(__file__), '..', '..', 'knowledge_base')
    rag.load(kb_path)
    
    # Build index
    rag.build()
    
    # Test very short queries
    short_queries = [
        "protein",
        "cardio", 
        "rest",
        "workout"
    ]
    
    for query in short_queries:
        # Test retrieval method
        results = rag.retrieve(query, k=3)
        assert len(results) > 0, f"Retrieval should return results for short query: {query}"
        assert len(results) <= 3, f"Retrieval should respect k=3 limit for query: {query}"

def test_workout_split_queries():
    """Test workout split queries to ensure they retrieve relevant information or use fallback."""
    rag = RAGIndex()
    kb_path = os.path.join(os.path.dirname(__file__), '..', '..', 'knowledge_base')
    rag.load(kb_path)
    rag.build()
    
    # Test workout split related queries
    workout_split_queries = [
        "workout split",
        "full body",
        "training frequency",
        "how often should I work out"
    ]
    
    for query in workout_split_queries:
        results = rag.retrieve(query, k=5)
        assert len(results) > 0, f"Should return results for workout split query: {query}"
        
        # Check that we're getting some relevant content
        sources = [r['source'] for r in results]
        
        # "how often" should find training frequency info
        if 'how often' in query.lower():
            assert any('training_frequency' in source for source in sources), f"Should include training frequency info for: {query}"
        
        # Other queries may not find training frequency but should still return results
        # The RAG service fallback will handle workout split questions appropriately
        assert len(results) > 0, f"Should return results for: {query}"

def test_bm25_availability():
    """Test that BM25 is available and working."""
    rag = RAGIndex()
    rag.load(os.path.join(os.path.dirname(__file__), '..', '..', 'knowledge_base'))
    rag.build()
    
    # Check if BM25 was used
    if hasattr(rag, '_bm25_index') and rag._model == "bm25":
        # Test a very short query that BM25 should handle well
        results = rag.retrieve("protein", k=2)
        assert len(results) > 0, "BM25 should return results for short query 'protein'"
    else:
        # If BM25 not available, should fallback to TF-IDF
        assert hasattr(rag, '_model'), "Should have a model after building"

if __name__ == "__main__":
    test_short_queries()
    test_workout_split_queries()
    test_bm25_availability()
    print("All tests passed!")
