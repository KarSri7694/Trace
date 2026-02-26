from typing import Dict, Any
import chromadb
from chromadb import Documents, EmbeddingFunction, Embeddings
from chromadb.utils.embedding_functions import register_embedding_function
import os

# Global variables for lazy loading
_model = None
_token = os.environ.get("HF_TOKEN")


def get_embedding_model():
    """
    Lazy load the SentenceTransformer model
    Only loads on first call and caches for subsequent calls
    
    Returns:
        SentenceTransformer model
    """
    global _model
    
    if _model is None:
        # Import only when needed
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("google/embeddinggemma-300m", token=_token)
    
    return _model


@register_embedding_function
class MyEmbeddingFunction(EmbeddingFunction):

    def __init__(self, model=None):
        # Allow model to be passed or use lazy loading
        self._custom_model = model
        self._model = None

    @property
    def model(self):
        """Lazy load model if not provided"""
        if self._model is None:
            if self._custom_model is not None:
                self._model = self._custom_model
            else:
                self._model = get_embedding_model()
        return self._model

    def __call__(self, input: Documents) -> Embeddings:
        # Encode the documents using the SentenceTransformer model
        embeddings = self.model.encode(input, convert_to_numpy=True).tolist()
        return embeddings

    @staticmethod
    def name() -> str:
        return "my-ef"

    def get_config(self) -> Dict[str, Any]:
        # Return serializable config (model name instead of model object)
        return {
            "model_name": "google/embeddinggemma-300m",
            "token": _token
        }

    @staticmethod
    def build_from_config(config: Dict[str, Any]) -> "EmbeddingFunction":
        # Create new instance with lazy loading (don't pass model object)
        return MyEmbeddingFunction()


def get_or_create_collection(client, collection_name: str = "document_collection", reset: bool = False):
    """
    Get or create a ChromaDB collection with the custom embedding function
    
    Args:
        client: ChromaDB client
        collection_name: Name of the collection
        reset: If True, delete existing collection and create new one
    
    Returns:
        ChromaDB collection
    """
    # Embedding function will lazy-load the model when needed
    embedding_fn = MyEmbeddingFunction()
    
    try:
        # If reset is requested, delete existing collection
        if reset:
            try:
                client.delete_collection(name=collection_name)
                print(f"Deleted existing collection: {collection_name}")
            except Exception:
                pass  # Collection doesn't exist, that's fine
        
        # Try to get existing collection first
        try:
            collection = client.get_collection(
                name=collection_name,
                embedding_function=embedding_fn
            )
            print(f"Using existing collection: {collection_name}")
            return collection
        except Exception:
            # Collection doesn't exist or has incompatible config, create new one
            pass
        
        # Create new collection
        collection = client.create_collection(
            name=collection_name,
            embedding_function=embedding_fn,
            metadata={"hnsw:space": "cosine"}  # Use cosine similarity
        )
        print(f"Created new collection: {collection_name}")
        return collection
        
    except Exception as e:
        print(f"Error with collection '{collection_name}': {e}")
        print("Attempting to reset collection...")
        
        # Try to delete and recreate
        try:
            client.delete_collection(name=collection_name)
            collection = client.create_collection(
                name=collection_name,
                embedding_function=embedding_fn,
                metadata={"hnsw:space": "cosine"}
            )
            print(f"Successfully reset and recreated collection: {collection_name}")
            return collection
        except Exception as e2:
            print(f"Failed to reset collection: {e2}")
            return None


def create_chroma_client(persist_directory: str = "./chroma_db"):
    """
    Create a persistent ChromaDB client
    
    Args:
        persist_directory: Directory to persist the database
    
    Returns:
        ChromaDB client
    """
    import os
    os.makedirs(persist_directory, exist_ok=True)
    client = chromadb.PersistentClient(path=persist_directory)
    return client


def reset_collection(client, collection_name: str = "document_collection"):
    """
    Delete and recreate a collection (useful for fixing corrupted collections)
    
    Args:
        client: ChromaDB client
        collection_name: Name of the collection to reset
    
    Returns:
        New ChromaDB collection
    """
    return get_or_create_collection(client, collection_name, reset=True)
    
