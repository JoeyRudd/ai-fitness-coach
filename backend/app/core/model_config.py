# Lightweight model configuration for production
MODEL_CONFIG = {
    "sentence_transformer_model": "all-MiniLM-L6-v2",  # 22MB instead of 400MB+
    "max_seq_length": 384,  # Reduce context window
    "embedding_dim": 384,   # Smaller embeddings
    "batch_size": 1,        # Process one at a time to save memory
    "device": "cpu",        # Explicit CPU usage
    "trust_remote_code": False,  # Security and size optimization
}
