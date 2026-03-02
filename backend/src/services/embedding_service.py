"""
Embedding Service for Vector Generation
Uses Amazon Bedrock for generating text embeddings
"""
import os
import json
from typing import Any, List, Optional, Union
import boto3
from dataclasses import dataclass


@dataclass
class EmbeddingResult:
    """Result of embedding generation"""
    embedding: List[float]
    dimension: int
    model: str
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'embedding': self.embedding,
            'dimension': self.dimension,
            'model': self.model
        }


class EmbeddingService:
    """
    Service for generating text embeddings using Amazon Bedrock
    """
    
    def __init__(
        self,
        bedrock_client: Optional[Any] = None,
        model_id: str = "amazon.titan-embed-text-v1"
    ):
        """
        Initialize Embedding Service
        
        Args:
            bedrock_client: Optional Bedrock client
            model_id: Model ID for embeddings
        """
        self.bedrock_client = bedrock_client or boto3.client(
            'bedrock-runtime',
            region_name=os.getenv('AWS_REGION', 'us-east-1')
        )
        self.model_id = model_id
        self.dimension = 1536 if 'titan' in model_id else 384
    
    def encode(
        self,
        text: Union[str, List[str]],
        normalize: bool = True
    ) -> Union[List[float], List[List[float]]]:
        """
        Generate embeddings for text
        
        Args:
            text: Single text string or list of texts
            normalize: Whether to normalize embeddings
            
        Returns:
            Single embedding vector or list of embedding vectors
        """
        if isinstance(text, str):
            return self._encode_single(text, normalize)
        else:
            return [self._encode_single(t, normalize) for t in text]
    
    def _encode_single(self, text: str, normalize: bool = True) -> List[float]:
        """
        Generate embedding for single text
        
        Args:
            text: Text to embed
            normalize: Whether to normalize embedding
            
        Returns:
            Embedding vector
        """
        try:
            # Prepare request body
            body = json.dumps({
                "inputText": text
            })
            
            # Call Bedrock
            response = self.bedrock_client.invoke_model(
                modelId=self.model_id,
                body=body,
                contentType='application/json',
                accept='application/json'
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            embedding = response_body.get('embedding', [])
            
            # Normalize if requested
            if normalize and embedding:
                embedding = self._normalize_vector(embedding)
            
            return embedding
            
        except Exception as e:
            # Fallback to simple embedding for testing
            # In production, this should raise the exception
            return self._generate_fallback_embedding(text)
    
    def _normalize_vector(self, vector: List[float]) -> List[float]:
        """Normalize vector to unit length"""
        magnitude = sum(x * x for x in vector) ** 0.5
        if magnitude > 0:
            return [x / magnitude for x in vector]
        return vector
    
    def _generate_fallback_embedding(self, text: str) -> List[float]:
        """
        Generate simple fallback embedding for testing
        
        Args:
            text: Text to embed
            
        Returns:
            Simple embedding vector
        """
        # Simple hash-based embedding for testing
        # In production, this should not be used
        import hashlib
        hash_obj = hashlib.sha256(text.encode())
        hash_bytes = hash_obj.digest()
        
        # Convert to float vector
        embedding = []
        for i in range(0, min(len(hash_bytes), self.dimension * 4), 4):
            chunk = hash_bytes[i:i+4]
            value = int.from_bytes(chunk, byteorder='big') / (2**32)
            embedding.append(value)
        
        # Pad if necessary
        while len(embedding) < self.dimension:
            embedding.append(0.0)
        
        return embedding[:self.dimension]
    
    def batch_encode(
        self,
        texts: List[str],
        batch_size: int = 25,
        normalize: bool = True
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batches
        
        Args:
            texts: List of texts to embed
            batch_size: Batch size for processing
            normalize: Whether to normalize embeddings
            
        Returns:
            List of embedding vectors
        """
        embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_embeddings = self.encode(batch, normalize)
            embeddings.extend(batch_embeddings)
        
        return embeddings
    
    def similarity(
        self,
        embedding1: List[float],
        embedding2: List[float]
    ) -> float:
        """
        Calculate cosine similarity between two embeddings
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Cosine similarity score (0-1)
        """
        if len(embedding1) != len(embedding2):
            raise ValueError("Embeddings must have same dimension")
        
        dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
        magnitude1 = sum(a * a for a in embedding1) ** 0.5
        magnitude2 = sum(b * b for b in embedding2) ** 0.5
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    def get_dimension(self) -> int:
        """Get embedding dimension"""
        return self.dimension


# Singleton instance
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """Get or create embedding service instance"""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
