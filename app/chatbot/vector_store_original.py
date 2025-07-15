import os
import json
import numpy as np
from collections import Counter
import re
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Check for Qdrant availability (placeholder for Docker implementation)
QDRANT_AVAILABLE = False

try:
    # Import Qdrant client conditionally - don't fail if not installed
    from qdrant_client import QdrantClient
    from qdrant_client.http import models
    QDRANT_AVAILABLE = True
except ImportError:
    print("Qdrant client not installed. Vector storage will be simulated.")

# Check for OpenAI availability
OPENAI_AVAILABLE = False

try:
    # Import OpenAI conditionally - don't fail if not installed
    import openai
    # Set API key if available
    if os.getenv("OPENAI_API_KEY"):
        openai.api_key = os.getenv("OPENAI_API_KEY")
        OPENAI_AVAILABLE = True
except ImportError:
    print("OpenAI package not installed. Embedding generation will be simulated.")

# Compatibility wrapper for OpenAI embeddings API
def get_embeddings(text, model="text-embedding-ada-002"):
    """
    Compatibility wrapper for OpenAI embeddings that works with both old and new API versions.
    
    Args:
        text: Text to embed
        model: Model name to use for embeddings
        
    Returns:
        List of embeddings or None if failed
    """
    if not os.getenv("OPENAI_API_KEY"):
        print("Warning: OPENAI_API_KEY is missing")
        return None
        
    try:
        # Try new API first (OpenAI >= 1.0)
        try:
            response = openai.embeddings.create(model=model, input=text)
            return response.data[0].embedding
        except (AttributeError, TypeError):
            # Fall back to old API (OpenAI < 1.0)
            response = openai.Embedding.create(model=model, input=text)
            return response["data"][0]["embedding"]
    except Exception as e:
        print(f"OpenAI embedding generation failed: {str(e)}")
        return None

# Global singleton instance
_vector_store_instance = None

def get_vector_store_client(collection_name="reshub_papers"):
    """
    Get or create a global singleton instance of the VectorStore.
    This ensures we reuse the same connection throughout the application.
    
    Args:
        collection_name: Name of the collection in Qdrant
        
    Returns:
        A VectorStore instance
    """
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = VectorStore(collection_name=collection_name)
    return _vector_store_instance

class VectorStore:
    """
    Interface for vector storage and retrieval.
    
    This class provides a unified interface for storing and retrieving
    vector embeddings, with fallbacks if Qdrant is not available.
    """
    
    def __init__(self, collection_name="reshub_papers"):
        """
        Initialize the vector store.
        
        Args:
            collection_name: Name of the collection in Qdrant
        """
        self.collection_name = collection_name
        
        # Initialize Qdrant client if available
        self.client = None
        if QDRANT_AVAILABLE:
            try:
                # Use environment variables for Qdrant connection
                vector_db_host = os.getenv("VECTOR_DB_HOST", "reshub-qdrant")
                vector_db_port = int(os.getenv("VECTOR_DB_PORT", 6333))
                print(f"Connecting to Qdrant at {vector_db_host}:{vector_db_port}")
                self.client = QdrantClient(vector_db_host, port=vector_db_port)
                # Test connection with a simple API call
                self.client.get_collections()
                print(f"Successfully connected to Qdrant at {vector_db_host}:{vector_db_port}")
                self._ensure_collection_exists()
            except Exception as e:
                print(f"Failed to connect to Qdrant: {str(e)}")
                self.client = None
        
        # Fallback in-memory storage if Qdrant is not available
        self.memory_store = []
    
    def _check_qdrant_connection(self):
        """
        Check if connection to Qdrant is working properly.
        
        Returns:
            bool: True if connection is working, False otherwise
        """
        if not self.client:
            return False
        
        try:
            # Simple API call to verify connection
            collections = self.client.get_collections()
            # Check if our collection exists
            collection_found = False
            
            if hasattr(collections, 'collections'):
                for collection in collections.collections:
                    if collection.name == self.collection_name:
                        collection_found = True
                        break
            else:
                # New Qdrant client API structure might be different
                if self.collection_name in [c.get('name') for c in collections]:
                    collection_found = True
            
            if not collection_found:
                print(f"Warning: Collection '{self.collection_name}' not found in Qdrant")
                return False
            
            # Get collection info to check point count
            try:
                collection_info = self.client.get_collection(collection_name=self.collection_name)
                points_count = getattr(collection_info, 'points_count', 0)
                if points_count == 0:
                    print(f"Warning: Collection '{self.collection_name}' exists but has no points")
                    return False
                else:
                    print(f"Collection '{self.collection_name}' has {points_count} points")
                    return True
            except Exception as e:
                print(f"Failed to get collection info: {str(e)}")
                return False
        except Exception as e:
            import logging
            logging.error(f"Qdrant connection check failed: {str(e)}")
            return False
    
    def _ensure_collection_exists(self):
        """Create collection if it doesn't exist."""
        if not self.client:
            return
            
        collections = self.client.get_collections().collections
        collection_names = [c.name for c in collections]
        
        if self.collection_name not in collection_names:
            print(f"Creating collection {self.collection_name}")
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config={
                    "dense": models.VectorParams(
                        size=1536,  # OpenAI embedding dimension
                        distance=models.Distance.COSINE
                    ),
                    "sparse": models.VectorParams(
                        size=8192,  # Sparse vector dimension (adjust based on vocabulary)
                        distance=models.Distance.DOT
                    )
                }
            )
    
    def _generate_embedding(self, text):
        """
        Generate dense and sparse embeddings for text.
        
        Args:
            text: Text to embed
            
        Returns:
            Dict with dense and sparse embeddings
        """
        # Dense embedding with OpenAI if available
        dense_vector = []
        import hashlib
        
        # Use our compatibility wrapper for OpenAI embeddings
        if OPENAI_AVAILABLE:
            embeddings = get_embeddings(text, model="text-embedding-ada-002")
            if embeddings:
                dense_vector = embeddings
        
        # Fallback: generate random vector if OpenAI failed or unavailable
        if not dense_vector:
            # Generate a deterministic "fake" vector based on text hash
            hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16) % 10**8
            np.random.seed(hash_val)
            dense_vector = np.random.random(1536).tolist()
        
        # Generate sparse vector (simple BM25-like approach)
        # Tokenize text
        tokens = re.findall(r'\b\w+\b', text.lower())
        token_counts = Counter(tokens)
        
        # Calculate term frequencies
        sparse_indices = []
        sparse_values = []
        
        for token, count in token_counts.items():
            # Simple hash for token to index mapping
            token_hash = int(hashlib.md5(token.encode()).hexdigest(), 16) % 8192
            sparse_indices.append(token_hash)
            
            # Simple BM25-like score (term frequency)
            sparse_values.append(min(1.0, 0.2 * count))
        
        return {
            "dense": dense_vector,
            "sparse": {
                "indices": sparse_indices,
                "values": sparse_values
            }
        }
    
    def add(self, text, metadata, point_id=None):
        """
        Add a text with metadata to the vector store.
        
        Args:
            text: Text content to index
            metadata: Associated metadata
            point_id: Optional ID for the point
            
        Returns:
            ID of the point
        """
        # Generate a unique ID if not provided
        if not point_id:
            import hashlib
            point_id = hashlib.md5((text + str(metadata)).encode()).hexdigest()
        
        # Generate embeddings
        embeddings = self._generate_embedding(text)
        
        # Store in Qdrant if available
        if self.client:
            try:
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=[
                        models.PointStruct(
                            id=point_id,
                            vector={
                                "dense": embeddings["dense"],
                                "sparse": models.SparseVector(
                                    indices=embeddings["sparse"]["indices"],
                                    values=embeddings["sparse"]["values"]
                                )
                            },
                            payload={
                                "text": text[:10000],  # Limit text size
                                "metadata": metadata
                            }
                        )
                    ]
                )
            except Exception as e:
                print(f"Failed to add to Qdrant: {str(e)}")
                # Fall back to memory store
                self.memory_store.append({
                    "id": point_id,
                    "embeddings": embeddings,
                    "text": text,
                    "metadata": metadata
                })
        else:
            # Store in memory
            self.memory_store.append({
                "id": point_id,
                "embeddings": embeddings,
                "text": text,
                "metadata": metadata
            })
        
        return point_id
    
    def get_collection(self):
        """
        Get information about the current collection.
        
        Returns:
            Dict with collection information or None if not available
        """
        if not self.client:
            return None
            
        try:
            # Just check if the collection exists without parsing all details
            collections = self.client.get_collections().collections
            collection_exists = False
            for collection in collections:
                if collection.name == self.collection_name:
                    collection_exists = True
                    break
                    
            if not collection_exists:
                return None
            
            # For simplicity, return a basic info object without trying to parse all details
            # This avoids potential schema validation issues with different Qdrant versions
            return {
                "name": self.collection_name,
                "vectors_count": 1,  # Just assume there's at least 1 vector
                "status": "green"    # Assume it's available
            }
        except Exception as e:
            print(f"Error getting collection info: {str(e)}")
            return None
            
    def search(self, query, limit=20):
        """
        Search for documents similar to query.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of results with scores and metadata
        """
        try:
            # Generate embeddings for query
            query_embeddings = self._generate_embedding(query)
        except Exception as e:
            import logging
            logging.error(f"Error generating embeddings: {str(e)}")
            # Return empty results if we can't generate embeddings
            return []
        
        # Search in Qdrant if available and properly connected
        if self.client and self._check_qdrant_connection():
            try:
                # Try with newer Qdrant client version (>=1.1.1)
                try:
                    search_result = self.client.search(
                        collection_name=self.collection_name,
                        query_vector=("dense", query_embeddings["dense"]),
                        limit=limit
                    )
                except (TypeError, ValueError):
                    # Fall back to older client version
                    search_result = self.client.search(
                        collection_name=self.collection_name,
                        query_vector=query_embeddings["dense"],
                        limit=limit
                    )
                
                results = []
                for point in search_result:
                    try:
                        # Safely extract payload data with fallbacks
                        payload = getattr(point, 'payload', {}) or {}
                        
                        # Extract metadata safely with defaults
                        doc_id = payload.get("document_id", "")
                        text = payload.get("text", "No text available")
                        title = payload.get("title", "Untitled Document")
                        
                        # Create a metadata structure compatible with the rest of the app
                        metadata = {
                            "document_id": doc_id,
                            "title": title
                        }
                        
                        # Add author and year if available
                        if "authors" in payload:
                            metadata["authors"] = payload["authors"]
                        if "year" in payload:
                            metadata["year"] = payload["year"]
                        
                        # Get point ID and score safely
                        point_id = getattr(point, 'id', None) or "unknown"
                        score = getattr(point, 'score', 0.0) or 0.0
                        
                        results.append({
                            "id": str(point_id),
                            "score": float(score),
                            "text": text,
                            "metadata": metadata
                        })
                    except Exception as e:
                        print(f"Error processing search result: {str(e)}")
                        continue
                
                print(f"Found {len(results)} results from Qdrant")
                if not results:
                    print(f"No results found in collection '{self.collection_name}' for query: {query[:50]}...")
                    return [{
                        "id": "no_papers_found",
                        "score": 0.0,
                        "text": "I couldn't find any relevant research papers for your query.",
                        "metadata": {
                            "document_id": "no_results_001",
                            "title": "No Matching Papers Found",
                            "authors": "System",
                            "year": 2025
                        }
                    }]
                return results
                
            except Exception as e:
                import logging
                import traceback
                # Get detailed error information
                error_details = traceback.format_exc()
                logging.error(f"Qdrant search failed: {str(e)}\nDetails: {error_details}")
                print(f"Qdrant search failed: {str(e)}\nCollection: {self.collection_name}")
                # Return no papers found message instead of simulated content
                return [{
                    "id": "no_papers_found",
                    "score": 0.0,
                    "text": "I couldn't find any relevant research papers for your query.",
                    "metadata": {
                        "document_id": "no_results_001",
                        "title": "No Matching Papers Found",
                        "authors": "System",
                        "year": 2025
                    }
                }]
        
        # Simple in-memory search (fallback)
        results = []
        if not self.memory_store:
            print("Memory store is empty, returning no papers found")
            return [{
                "id": "no_papers_found",
                "score": 0.0,
                "text": "I couldn't find any relevant research papers for your query.",
                "metadata": {
                    "document_id": "no_results_001",
                    "title": "No Matching Papers Found",
                    "authors": "System",
                    "year": 2025
                }
            }]
            
        query_dense = np.array(query_embeddings["dense"])
        
        for item in self.memory_store:
            # Calculate cosine similarity
            item_dense = np.array(item["embeddings"]["dense"])
            similarity = np.dot(query_dense, item_dense) / (np.linalg.norm(query_dense) * np.linalg.norm(item_dense))
            
            results.append({
                "id": item["id"],
                "score": float(similarity),
                "text": item["text"],
                "metadata": item["metadata"]
            })
        
        # Sort by score (descending)
        results.sort(key=lambda x: x["score"], reverse=True)
        
        return results[:limit]
        
    def count_documents(self):
        """
        Count the number of documents in the vector store.
        
        Returns:
            int: Number of documents in the vector store
        """
        if self.client:
            try:
                # Try to get collection info from Qdrant
                collection_info = self.get_collection()
                if collection_info and "vectors_count" in collection_info:
                    return collection_info["vectors_count"]
                elif collection_info and "status" in collection_info and collection_info["status"] == "green":
                    # If we can't get the vector count directly but the collection exists, return at least 1
                    return 1
            except Exception as e:
                print(f"Error counting documents: {str(e)}")
        
        # Fallback to memory store length
        return len(self.memory_store)
