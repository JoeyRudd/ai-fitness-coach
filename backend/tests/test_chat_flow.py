from fastapi.testclient import TestClient


def _post_chat(client: TestClient, message: str, history=None):
    if history is None:
        history = []
    payload = {"message": message, "history": history}
    return client.post("/api/v1/chat", json=payload)


def test_missing_api_key_fallback(client: TestClient, force_fallback):
    # Ensure _model is None so fallback path triggers for general intent
    resp = _post_chat(client, "How often should I train?")
    data = resp.json()
    assert resp.status_code == 200
    assert data["intent"] == "general"
    assert "I am in simple mode" in data["response"]


def test_progressive_tdee_completion(client: TestClient, force_fallback):
    # Sequence: ask calories -> ask sex -> provide sex -> ask age -> provide rest -> final TDEE
    history = []
    # User asks for calories
    r1 = _post_chat(client, "Can you calculate my calories?", history)
    d1 = r1.json()
    assert d1["intent"] == "tdee"
    assert d1["missing"]  # all missing
    assert "sex" in d1["missing"]
    assert d1["asked_this_intent"] == ["sex"]  # first asked
    history.append({"role": "user", "content": "Can you calculate my calories?"})
    history.append({"role": "assistant", "content": d1["response"]})

    # Provide sex
    r2 = _post_chat(client, "male", history)
    d2 = r2.json()
    assert d2["intent"] == "tdee"
    assert "sex" not in d2["missing"]
    assert d2["asked_this_intent"] == ["age"]
    history.append({"role": "user", "content": "male"})
    history.append({"role": "assistant", "content": d2["response"]})

    # Provide age
    r3 = _post_chat(client, "45", history)
    d3 = r3.json()
    assert "age" not in d3["missing"]
    assert d3["asked_this_intent"]  # next field asked
    next_field = d3["asked_this_intent"][0]
    assert next_field in ["weight_kg", "height_cm", "activity_factor"]
    history.append({"role": "user", "content": "45"})
    history.append({"role": "assistant", "content": d3["response"]})

    # Provide remaining in one message
    r4 = _post_chat(client, "80 kg 180 cm moderate", history)
    d4 = r4.json()
    assert d4["intent"] == "tdee"
    assert d4["missing"] == []
    assert d4["tdee"] is not None
    assert "Daily burn" in d4["response"]


def test_recall_height_flow(client: TestClient, force_fallback):
    history = []
    # Provide profile facts first
    h1 = _post_chat(client, "male 45 80 kg 5'11\" moderate", history).json()
    history.append({"role": "user", "content": "male 45 80 kg 5'11\" moderate"})
    # Ask recall
    h2 = _post_chat(client, "What is my height?", history).json()
    assert h2["intent"] == "recall"
    assert "height" in h2["response"].lower()
    assert "cm" in h2["response"].lower()


def test_general_query_with_mocked_generation(client: TestClient, mock_generate):
    mock_generate("Custom fixed reply")
    resp = _post_chat(client, "Tell me about protein.")
    data = resp.json()
    assert data["intent"] == "general"
    assert data["response"] == "Custom fixed reply"
