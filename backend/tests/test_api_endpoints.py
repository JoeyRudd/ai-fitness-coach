import pytest
from fastapi.testclient import TestClient
from app.models.chat import ChatMessage, Profile

class TestAPIEndpoints:
    """Test all API endpoints for proper functionality and responses."""
    
    def test_healthz_endpoint(self, client: TestClient):
        """Test the health check endpoint returns proper status."""
        response = client.get("/healthz")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
    
    def test_root_endpoint(self, client: TestClient):
        """Test the root endpoint returns system information."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields exist
        assert "message" in data
        assert "model" in data
        assert "rag_status" in data
        assert "rag_backend" in data
        assert "rag_chunks" in data
        
        # Check data types and values
        assert isinstance(data["message"], str)
        assert isinstance(data["rag_status"], str)
        assert data["rag_status"] in ["ready", "not ready"]
        assert data["rag_backend"] in ["tfidf", "none"]
    
    def test_chat_api_root(self, client: TestClient):
        """Test the chat API root endpoint."""
        response = client.get("/api/v1/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "chat"
    
    def test_chat_endpoint_success(self, client: TestClient, mock_generate):
        """Test successful chat request with valid data."""
        mock_generate("Here's some great fitness advice for you!")
        
        request_data = {
            "message": "How should I start working out?",
            "history": []
        }
        
        response = client.post("/api/v1/chat", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "response" in data
        assert "profile" in data
        assert "tdee" in data
        assert "missing" in data
        assert "asked_this_intent" in data
        assert "intent" in data
        
        # Check response content
        assert len(data["response"]) > 0
        assert isinstance(data["profile"], dict)
    
    def test_chat_endpoint_with_history(self, client: TestClient, mock_generate):
        """Test chat endpoint with conversation history."""
        mock_generate("Based on our conversation, here's what I recommend...")
        
        request_data = {
            "message": "What's next?",
            "history": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi! How can I help you today?"}
            ]
        }
        
        response = client.post("/api/v1/chat", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["response"] is not None
    
    
    def test_chat_endpoint_empty_message(self, client: TestClient, mock_generate):
        """Test chat endpoint with empty message (should be rejected)."""
        request_data = {
            "message": "",
            "history": []
        }
        
        response = client.post("/api/v1/chat", json=request_data)
        assert response.status_code == 422  # Validation error - empty message not allowed
        
        data = response.json()
        assert "detail" in data
    
    def test_chat_endpoint_missing_message(self, client: TestClient):
        """Test chat endpoint with missing message field."""
        request_data = {
            "history": []
        }
        
        response = client.post("/api/v1/chat", json=request_data)
        assert response.status_code == 422  # Validation error
    
    def test_chat_endpoint_missing_history(self, client: TestClient):
        """Test chat endpoint with missing history field."""
        request_data = {
            "message": "Test message"
        }
        
        response = client.post("/api/v1/chat", json=request_data)
        assert response.status_code == 200  # History is optional with default []
    
    def test_chat_endpoint_large_message(self, client: TestClient, mock_generate):
        """Test chat endpoint with very long message."""
        mock_generate("I can handle long messages!")
        
        long_message = "This is a very long message " * 100  # ~2800 characters
        
        request_data = {
            "message": long_message,
            "history": []
        }
        
        response = client.post("/api/v1/chat", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["response"] is not None
    
    def test_chat_endpoint_special_characters(self, client: TestClient, mock_generate):
        """Test chat endpoint handles special characters properly."""
        mock_generate("Special characters handled!")
        
        special_message = "Hello! How are you? I'm doing great. Let's talk about fitness & nutrition!"
        
        request_data = {
            "message": special_message,
            "history": []
        }
        
        response = client.post("/api/v1/chat", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["response"] is not None
