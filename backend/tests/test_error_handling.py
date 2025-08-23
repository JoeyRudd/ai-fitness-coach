import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.services.rag_service import rag_service


class TestErrorHandling:
    """Test how the API handles various error conditions gracefully."""
    
    def test_rag_service_unavailable(self, client: TestClient):
        """Test behavior when RAG service is completely unavailable."""
        with patch('app.services.rag_service.rag_service.get_ai_response') as mock:
            mock.side_effect = Exception("RAG service unavailable")
            
            response = client.post("/api/v1/chat", json={
                "message": "Test message",
                "history": []
            })
            
            # Should handle gracefully - check what status code you want
            assert response.status_code in [500, 422, 503]
    
    def test_gemini_api_failure(self, client: TestClient):
        """Test behavior when Gemini API fails."""
        with patch('google.generativeai.GenerativeModel.generate_content') as mock:
            mock.side_effect = Exception("API key invalid or quota exceeded")
            
            response = client.post("/api/v1/chat", json={
                "message": "Test message",
                "history": []
            })
            
            # Should handle gracefully and continue working
            assert response.status_code == 200
            data = response.json()
            assert "response" in data
            # Should return some kind of response (either error fallback or general fallback)
            assert len(data["response"]) > 0
            assert isinstance(data["response"], str)
    
    def test_invalid_json_request(self, client: TestClient):
        """Test handling of malformed JSON requests."""
        response = client.post("/api/v1/chat", data="invalid json data")
        assert response.status_code == 422
        
        # Should return proper error message
        data = response.json()
        assert "detail" in data
    
    def test_malformed_request_data(self, client: TestClient):
        """Test handling of malformed request data."""
        # Test with wrong data types
        response = client.post("/api/v1/chat", json={
            "message": 123,  # Should be string
            "history": "not a list"  # Should be list
        })
        assert response.status_code == 422
        
        data = response.json()
        assert "detail" in data
    
    def test_missing_required_fields(self, client: TestClient):
        """Test handling of requests missing required fields."""
        # Test with empty object
        response = client.post("/api/v1/chat", json={})
        assert response.status_code == 422
        
        data = response.json()
        assert "detail" in data
    
    def test_invalid_history_format(self, client: TestClient):
        """Test handling of invalid history format."""
        response = client.post("/api/v1/chat", json={
            "message": "Test",
            "history": [
                {"role": "invalid_role", "content": "test"},  # Invalid role
                {"role": "user"},  # Missing content
                {"content": "test"}  # Missing role
            ]
        })
        assert response.status_code == 422
        
        data = response.json()
        assert "detail" in data
    
    def test_rag_index_not_ready(self, client: TestClient, force_fallback):
        """Test behavior when RAG index is not ready."""
        with patch.object(rag_service, '_rag_index') as mock_index:
            mock_index._ready = False
            
            response = client.post("/api/v1/chat", json={
                "message": "Test message",
                "history": []
            })
            
            # Should handle gracefully or return appropriate error
            assert response.status_code in [200, 500, 503]
    
    def test_memory_error_handling(self, client: TestClient):
        """Test handling of memory-related errors."""
        with patch('app.services.rag_service.rag_service.get_ai_response') as mock:
            mock.side_effect = MemoryError("Out of memory")
            
            response = client.post("/api/v1/chat", json={
                "message": "Test message",
                "history": []
            })
            
            # Should handle gracefully
            assert response.status_code in [500, 503]
    
    def test_timeout_handling(self, client: TestClient):
        """Test handling of timeout errors."""
        with patch('app.services.rag_service.rag_service.get_ai_response') as mock:
            mock.side_effect = TimeoutError("Request timed out")
            
            response = client.post("/api/v1/chat", json={
                "message": "Test message",
                "history": []
            })
            
            # Should handle gracefully
            assert response.status_code in [500, 408, 503]
    
    def test_network_error_handling(self, client: TestClient):
        """Test handling of network-related errors."""
        with patch('app.services.rag_service.rag_service.get_ai_response') as mock:
            mock.side_effect = ConnectionError("Network connection failed")
            
            response = client.post("/api/v1/chat", json={
                "message": "Test message",
                "history": []
            })
            
            # Should handle gracefully
            assert response.status_code in [500, 503]
    
    def test_validation_error_details(self, client: TestClient):
        """Test that validation errors provide useful details."""
        response = client.post("/api/v1/chat", json={
            "message": "",  # Empty message
            "history": []
        })
        
        assert response.status_code == 422
        data = response.json()
        
        # Should provide specific error details
        assert "detail" in data
        # Check that the error message is helpful
        assert len(str(data["detail"])) > 0
    
    def test_cors_error_handling(self, client: TestClient):
        """Test CORS error handling."""
        # Test with invalid origin
        response = client.get("/", headers={"Origin": "http://malicious-site.com"})
        
        # Should still work (CORS is handled by middleware)
        assert response.status_code == 200
