# Model configuration for production
MODEL_CONFIG = {
    # TF-IDF configuration
    "max_features": 5000,
    "ngram_range": (1, 2),
    "sublinear_tf": True,
    "max_df": 0.9,
}
