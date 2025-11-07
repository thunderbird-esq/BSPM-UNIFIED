"""
Semantic Embedding Utilities

Provides text embedding and similarity functions for the memory system.
Uses sentence-transformers for creating semantic embeddings.
"""

import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


def create_embedding(
    text: str,
    model: SentenceTransformer,
    normalize: bool = True
) -> np.ndarray:
    """
    Create semantic embedding for text.

    Args:
        text: Input text to embed
        model: SentenceTransformer model instance
        normalize: Whether to normalize the embedding vector

    Returns:
        384-dimensional vector (all-MiniLM-L6-v2) or model-specific dimensions

    Example:
        >>> model = SentenceTransformer('all-MiniLM-L6-v2')
        >>> embedding = create_embedding("Create a boss sprite", model)
        >>> embedding.shape
        (384,)
    """
    if not text or not text.strip():
        logger.warning("Empty text provided for embedding, returning zero vector")
        # Return zero vector with appropriate dimensions
        return np.zeros(model.get_sentence_embedding_dimension())

    try:
        embedding = model.encode(
            text.strip(),
            convert_to_tensor=False,
            normalize_embeddings=normalize
        )
        return np.array(embedding, dtype=np.float32)
    except Exception as e:
        logger.error(f"Error creating embedding: {e}")
        raise


def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """
    Calculate cosine similarity between two vectors.

    Args:
        vec1: First embedding vector
        vec2: Second embedding vector

    Returns:
        Similarity score between -1 and 1 (typically 0 to 1 for normalized vectors)

    Example:
        >>> vec1 = np.array([1.0, 0.0, 0.0])
        >>> vec2 = np.array([1.0, 0.0, 0.0])
        >>> cosine_similarity(vec1, vec2)
        1.0
    """
    if vec1.shape != vec2.shape:
        raise ValueError(
            f"Vector dimensions must match: {vec1.shape} vs {vec2.shape}"
        )

    # Handle zero vectors
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)

    if norm1 == 0 or norm2 == 0:
        logger.warning("Zero vector encountered in cosine similarity calculation")
        return 0.0

    similarity = np.dot(vec1, vec2) / (norm1 * norm2)

    # Clamp to [-1, 1] to handle floating point errors
    return float(np.clip(similarity, -1.0, 1.0))


def batch_embeddings(
    texts: List[str],
    model: SentenceTransformer,
    batch_size: int = 32,
    show_progress: bool = False,
    normalize: bool = True
) -> np.ndarray:
    """
    Create embeddings for multiple texts efficiently.

    Args:
        texts: List of text strings to embed
        model: SentenceTransformer model instance
        batch_size: Number of texts to process at once
        show_progress: Whether to display progress bar
        normalize: Whether to normalize the embedding vectors

    Returns:
        Array of shape (len(texts), embedding_dim)

    Example:
        >>> model = SentenceTransformer('all-MiniLM-L6-v2')
        >>> texts = ["Create sprite", "Design character", "Write code"]
        >>> embeddings = batch_embeddings(texts, model)
        >>> embeddings.shape
        (3, 384)
    """
    if not texts:
        logger.warning("Empty text list provided for batch embeddings")
        return np.array([])

    # Filter out empty texts and track indices
    valid_texts = []
    valid_indices = []
    for i, text in enumerate(texts):
        if text and text.strip():
            valid_texts.append(text.strip())
            valid_indices.append(i)

    if not valid_texts:
        logger.warning("No valid texts in batch, returning zero vectors")
        dim = model.get_sentence_embedding_dimension()
        return np.zeros((len(texts), dim), dtype=np.float32)

    try:
        embeddings = model.encode(
            valid_texts,
            batch_size=batch_size,
            convert_to_tensor=False,
            show_progress_bar=show_progress,
            normalize_embeddings=normalize
        )

        # If some texts were invalid, create full array with zero vectors
        if len(valid_texts) < len(texts):
            dim = model.get_sentence_embedding_dimension()
            full_embeddings = np.zeros((len(texts), dim), dtype=np.float32)
            full_embeddings[valid_indices] = embeddings
            return full_embeddings

        return np.array(embeddings, dtype=np.float32)

    except Exception as e:
        logger.error(f"Error creating batch embeddings: {e}")
        raise


def semantic_search(
    query_embedding: np.ndarray,
    corpus_embeddings: np.ndarray,
    top_k: int = 5,
    min_similarity: float = 0.0
) -> List[tuple]:
    """
    Find most similar embeddings to a query using cosine similarity.

    Args:
        query_embedding: Query vector of shape (embedding_dim,)
        corpus_embeddings: Corpus vectors of shape (n_documents, embedding_dim)
        top_k: Number of top results to return
        min_similarity: Minimum similarity threshold

    Returns:
        List of (index, similarity_score) tuples, sorted by similarity

    Example:
        >>> query = create_embedding("boss sprite", model)
        >>> corpus = batch_embeddings(["enemy sprite", "hero sprite"], model)
        >>> results = semantic_search(query, corpus, top_k=2)
        >>> [(idx, score) for idx, score in results]
        [(0, 0.92), (1, 0.78)]
    """
    if corpus_embeddings.size == 0:
        return []

    if len(corpus_embeddings.shape) == 1:
        corpus_embeddings = corpus_embeddings.reshape(1, -1)

    # Calculate similarities
    similarities = np.array([
        cosine_similarity(query_embedding, corpus_vec)
        for corpus_vec in corpus_embeddings
    ])

    # Filter by minimum similarity
    valid_indices = np.where(similarities >= min_similarity)[0]

    if len(valid_indices) == 0:
        return []

    # Get top-k results
    top_indices = valid_indices[np.argsort(-similarities[valid_indices])][:top_k]

    return [(int(idx), float(similarities[idx])) for idx in top_indices]


def cluster_embeddings(
    embeddings: np.ndarray,
    n_clusters: int = 5,
    random_state: int = 42
) -> np.ndarray:
    """
    Cluster embeddings using K-means.

    Useful for organizing knowledge into topics or finding patterns.

    Args:
        embeddings: Array of shape (n_samples, embedding_dim)
        n_clusters: Number of clusters to create
        random_state: Random seed for reproducibility

    Returns:
        Cluster labels array of shape (n_samples,)

    Example:
        >>> embeddings = batch_embeddings(texts, model)
        >>> labels = cluster_embeddings(embeddings, n_clusters=3)
        >>> labels
        array([0, 0, 1, 2, 1])
    """
    try:
        from sklearn.cluster import KMeans
    except ImportError:
        logger.error("scikit-learn not installed, required for clustering")
        raise ImportError("Please install scikit-learn: pip install scikit-learn")

    if embeddings.shape[0] < n_clusters:
        logger.warning(
            f"Number of samples ({embeddings.shape[0]}) less than "
            f"clusters ({n_clusters}), using n_samples as n_clusters"
        )
        n_clusters = embeddings.shape[0]

    kmeans = KMeans(
        n_clusters=n_clusters,
        random_state=random_state,
        n_init=10
    )

    return kmeans.fit_predict(embeddings)


def get_embedding_model(
    model_name: str = 'all-MiniLM-L6-v2',
    device: Optional[str] = None,
    cache_folder: Optional[str] = None
) -> SentenceTransformer:
    """
    Load a sentence transformer model.

    Args:
        model_name: Name of the model to load
        device: Device to use ('cpu', 'cuda', 'mps', or None for auto)
        cache_folder: Custom cache directory for models

    Returns:
        Loaded SentenceTransformer model

    Recommended models:
        - 'all-MiniLM-L6-v2': Fast, 384 dims, good balance (default)
        - 'all-mpnet-base-v2': Better quality, 768 dims, slower
        - 'paraphrase-multilingual-MiniLM-L12-v2': Multilingual support
    """
    try:
        model = SentenceTransformer(
            model_name,
            device=device,
            cache_folder=cache_folder
        )
        logger.info(
            f"Loaded embedding model '{model_name}' "
            f"(dimensions: {model.get_sentence_embedding_dimension()})"
        )
        return model
    except Exception as e:
        logger.error(f"Error loading embedding model '{model_name}': {e}")
        raise


def embedding_to_list(embedding: np.ndarray) -> List[float]:
    """
    Convert numpy embedding to list for JSON serialization.

    Args:
        embedding: Numpy array embedding

    Returns:
        List of floats
    """
    return embedding.astype(float).tolist()


def list_to_embedding(embedding_list: List[float]) -> np.ndarray:
    """
    Convert list back to numpy embedding.

    Args:
        embedding_list: List of floats

    Returns:
        Numpy array of shape (len(embedding_list),)
    """
    return np.array(embedding_list, dtype=np.float32)


if __name__ == "__main__":
    # Example usage and testing
    print("Loading embedding model...")
    model = get_embedding_model()

    # Single embedding
    text = "Create a boss sprite for the game"
    embedding = create_embedding(text, model)
    print(f"\nSingle embedding shape: {embedding.shape}")

    # Batch embeddings
    texts = [
        "Create a boss sprite",
        "Design a hero character",
        "Write game dialogue",
        "Implement combat system",
        "Create background music"
    ]
    embeddings = batch_embeddings(texts, model)
    print(f"Batch embeddings shape: {embeddings.shape}")

    # Similarity search
    query = "boss enemy sprite design"
    query_emb = create_embedding(query, model)
    results = semantic_search(query_emb, embeddings, top_k=3)

    print(f"\nSemantic search results for '{query}':")
    for idx, score in results:
        print(f"  {score:.3f}: {texts[idx]}")

    # Clustering
    labels = cluster_embeddings(embeddings, n_clusters=3)
    print("\nClustering results:")
    for i, (text, label) in enumerate(zip(texts, labels)):
        print(f"  Cluster {label}: {text}")
