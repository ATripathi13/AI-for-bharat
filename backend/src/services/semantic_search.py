"""
Semantic Search Service
Provides intelligent search capabilities for Business Copilot
"""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from datetime import datetime

from .opensearch_service import OpenSearchService, SearchResult, get_opensearch_service
from .embedding_service import EmbeddingService, get_embedding_service


@dataclass
class SemanticSearchQuery:
    """Semantic search query"""
    query_text: str
    document_type: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    max_results: int = 10
    search_mode: str = 'hybrid'  # 'text', 'semantic', 'hybrid'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'queryText': self.query_text,
            'documentType': self.document_type,
            'filters': self.filters,
            'maxResults': self.max_results,
            'searchMode': self.search_mode
        }


@dataclass
class KnowledgeRetrievalResult:
    """Result from knowledge retrieval"""
    query: str
    results: List[SearchResult]
    total_found: int
    search_time_ms: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'query': self.query,
            'results': [r.to_dict() for r in self.results],
            'totalFound': self.total_found,
            'searchTimeMs': self.search_time_ms
        }


class SemanticSearchService:
    """
    Service for semantic search and knowledge retrieval
    Integrates with Business Copilot for intelligent query answering
    """
    
    def __init__(
        self,
        opensearch_service: Optional[OpenSearchService] = None,
        embedding_service: Optional[EmbeddingService] = None
    ):
        """
        Initialize Semantic Search Service
        
        Args:
            opensearch_service: Optional OpenSearch service instance
            embedding_service: Optional embedding service instance
        """
        self.opensearch = opensearch_service or get_opensearch_service()
        self.embedding_service = embedding_service or get_embedding_service()
    
    def search(
        self,
        query: SemanticSearchQuery
    ) -> KnowledgeRetrievalResult:
        """
        Perform semantic search
        
        Args:
            query: Search query
            
        Returns:
            KnowledgeRetrievalResult with search results
        """
        start_time = datetime.utcnow()
        
        # Generate query embedding
        query_embedding = self.embedding_service.encode(query.query_text)
        
        # Perform search based on mode
        if query.search_mode == 'text':
            results = self.opensearch.search_documents(
                query=query.query_text,
                document_type=query.document_type,
                filters=query.filters,
                size=query.max_results
            )
        elif query.search_mode == 'semantic':
            results = self.opensearch.semantic_search(
                query_embedding=query_embedding,
                document_type=query.document_type,
                filters=query.filters,
                size=query.max_results
            )
        else:  # hybrid
            results = self.opensearch.hybrid_search(
                text_query=query.query_text,
                query_embedding=query_embedding,
                document_type=query.document_type,
                filters=query.filters,
                size=query.max_results,
                text_weight=0.4,
                semantic_weight=0.6
            )
        
        # Calculate search time
        end_time = datetime.utcnow()
        search_time_ms = (end_time - start_time).total_seconds() * 1000
        
        return KnowledgeRetrievalResult(
            query=query.query_text,
            results=results,
            total_found=len(results),
            search_time_ms=search_time_ms
        )
    
    def retrieve_relevant_context(
        self,
        query: str,
        context_type: Optional[str] = None,
        max_contexts: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant context for a query
        Used by Business Copilot to augment responses
        
        Args:
            query: User query
            context_type: Optional type of context to retrieve
            max_contexts: Maximum number of contexts to return
            
        Returns:
            List of relevant context documents
        """
        search_query = SemanticSearchQuery(
            query_text=query,
            document_type=context_type,
            max_results=max_contexts,
            search_mode='hybrid'
        )
        
        result = self.search(search_query)
        
        # Format contexts for copilot
        contexts = []
        for search_result in result.results:
            context = {
                'content': search_result.content,
                'source': search_result.metadata.source,
                'relevance_score': search_result.score,
                'document_type': search_result.metadata.document_type,
                'timestamp': search_result.metadata.timestamp.isoformat()
            }
            contexts.append(context)
        
        return contexts
    
    def find_similar_documents(
        self,
        document_id: str,
        document_type: Optional[str] = None,
        max_results: int = 10
    ) -> List[SearchResult]:
        """
        Find documents similar to a given document
        
        Args:
            document_id: ID of the reference document
            document_type: Optional document type filter
            max_results: Maximum number of results
            
        Returns:
            List of similar documents
        """
        # Get the reference document
        # In production, would retrieve from OpenSearch
        # For now, return empty list
        return []
    
    def search_by_category(
        self,
        category: str,
        query: Optional[str] = None,
        max_results: int = 10
    ) -> List[SearchResult]:
        """
        Search documents by category
        
        Args:
            category: Category to search
            query: Optional text query
            max_results: Maximum number of results
            
        Returns:
            List of search results
        """
        filters = {'metadata.category': category}
        
        if query:
            search_query = SemanticSearchQuery(
                query_text=query,
                filters=filters,
                max_results=max_results,
                search_mode='hybrid'
            )
            result = self.search(search_query)
            return result.results
        else:
            # Return all documents in category
            return self.opensearch.search_documents(
                query='*',
                filters=filters,
                size=max_results
            )
    
    def get_trending_topics(
        self,
        timeframe_days: int = 7,
        max_topics: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get trending topics from indexed documents
        
        Args:
            timeframe_days: Number of days to look back
            max_topics: Maximum number of topics to return
            
        Returns:
            List of trending topics with counts
        """
        # In production, would use aggregations
        # For now, return placeholder
        return []
    
    def answer_question(
        self,
        question: str,
        context_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Answer a question using knowledge base
        
        Args:
            question: Question to answer
            context_type: Optional context type filter
            
        Returns:
            Dictionary with answer and supporting documents
        """
        # Search knowledge base
        search_query = SemanticSearchQuery(
            query_text=question,
            document_type='knowledge_base',
            max_results=3,
            search_mode='semantic'
        )
        
        kb_result = self.search(search_query)
        
        # Search business intelligence for additional context
        bi_query = SemanticSearchQuery(
            query_text=question,
            document_type=context_type,
            max_results=5,
            search_mode='hybrid'
        )
        
        bi_result = self.search(bi_query)
        
        # Combine results
        answer = {
            'question': question,
            'knowledgeBaseResults': [r.to_dict() for r in kb_result.results],
            'contextResults': [r.to_dict() for r in bi_result.results],
            'confidence': self._calculate_answer_confidence(kb_result, bi_result),
            'sources': self._extract_sources(kb_result.results + bi_result.results)
        }
        
        return answer
    
    def _calculate_answer_confidence(
        self,
        kb_result: KnowledgeRetrievalResult,
        bi_result: KnowledgeRetrievalResult
    ) -> float:
        """Calculate confidence score for answer"""
        if not kb_result.results and not bi_result.results:
            return 0.0
        
        # Use top result scores
        kb_score = kb_result.results[0].score if kb_result.results else 0.0
        bi_score = bi_result.results[0].score if bi_result.results else 0.0
        
        # Weighted average (knowledge base weighted higher)
        confidence = (kb_score * 0.7 + bi_score * 0.3)
        
        # Normalize to 0-1 range
        return min(confidence / 10.0, 1.0)
    
    def _extract_sources(self, results: List[SearchResult]) -> List[str]:
        """Extract unique sources from results"""
        sources = set()
        for result in results:
            sources.add(result.metadata.source)
        return list(sources)
    
    def index_copilot_interaction(
        self,
        query: str,
        response: str,
        category: str,
        rating: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Index a copilot interaction for future learning
        
        Args:
            query: User query
            response: Copilot response
            category: Category of interaction
            rating: Optional user rating
            
        Returns:
            Dictionary with indexing result
        """
        from .document_ingestion import get_ingestion_pipeline
        
        pipeline = get_ingestion_pipeline()
        
        metadata = {
            'category': category,
            'timestamp': datetime.utcnow().isoformat(),
            'usageCount': 1,
            'averageRating': rating if rating else 0.0
        }
        
        result = pipeline.ingest_knowledge_base_entry(
            question=query,
            answer=response,
            category=category,
            metadata=metadata
        )
        
        return result.to_dict()
    
    def get_search_suggestions(
        self,
        partial_query: str,
        max_suggestions: int = 5
    ) -> List[str]:
        """
        Get search suggestions based on partial query
        
        Args:
            partial_query: Partial query text
            max_suggestions: Maximum number of suggestions
            
        Returns:
            List of suggested queries
        """
        # In production, would use completion suggester
        # For now, return empty list
        return []


# Singleton instance
_semantic_search_service: Optional[SemanticSearchService] = None


def get_semantic_search_service() -> SemanticSearchService:
    """Get or create semantic search service instance"""
    global _semantic_search_service
    if _semantic_search_service is None:
        _semantic_search_service = SemanticSearchService()
    return _semantic_search_service
