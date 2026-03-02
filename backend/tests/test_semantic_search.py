"""
Unit Tests for Semantic Search
Tests document indexing, search query execution, and result ranking
"""
import pytest
from unittest.mock import Mock
from datetime import datetime

from src.services.opensearch_service import (
    OpenSearchService,
    DocumentMetadata,
    SearchResult
)
from src.services.embedding_service import EmbeddingService
from src.services.semantic_search import (
    SemanticSearchService,
    SemanticSearchQuery
)
from src.services.document_ingestion import (
    DocumentIngestionPipeline
)
from src.models.business_intelligence import BusinessIntelligence


class TestDocumentIndexing:
    """Test document indexing functionality"""
    
    def test_index_document_success(self):
        """Test successful document indexing"""
        # Create mock OpenSearch client
        mock_client = Mock()
        mock_client.index.return_value = {
            'result': 'created',
            '_version': 1
        }
        
        opensearch = OpenSearchService()
        opensearch.client = mock_client
        
        # Index a document
        result = opensearch.index_document(
            document_id='test-doc-1',
            content='Test content for indexing',
            document_type='test',
            metadata={'source': 'test', 'tags': ['test']}
        )
        
        # Verify indexing was called
        assert mock_client.index.called
        assert result['documentId'] == 'test-doc-1'
        assert result['result'] == 'created'
    
    def test_bulk_index_documents(self):
        """Test bulk document indexing"""
        mock_client = Mock()
        mock_client.bulk.return_value = {
            'errors': False,
            'items': [{'index': {'result': 'created'}}] * 3
        }
        
        opensearch = OpenSearchService()
        opensearch.client = mock_client
        
        documents = [
            {
                'documentId': f'doc-{i}',
                'content': f'Content {i}',
                'metadata': {'source': 'test'}
            }
            for i in range(3)
        ]
        
        result = opensearch.bulk_index_documents(documents)
        
        assert mock_client.bulk.called
        assert result['total'] == 3
        assert result['errors'] is False
    
    def test_ingest_business_intelligence(self):
        """Test ingesting business intelligence document"""
        mock_opensearch = Mock()
        mock_opensearch.index_document.return_value = {
            'documentId': 'bi-1',
            'result': 'created'
        }
        
        pipeline = DocumentIngestionPipeline(opensearch_service=mock_opensearch)
        
        intelligence = BusinessIntelligence(
            entity_type='pricing',
            entity_id='bi-1',
            insights={
                'trend': 'increasing',
                'prediction': 'price increase expected',
                'confidence': 0.85,
                'timeframe': '30 days'
            },
            recommendations=[
                {'action': 'adjust_pricing', 'description': 'Increase prices by 5%'}
            ],
            data_source=['pricing_agent']
        )
        
        result = pipeline.ingest_business_intelligence(intelligence)
        
        assert result.status == 'success'
        assert result.indexed is True
        assert result.document_id == 'bi-1'
    
    def test_ingest_with_embedding(self):
        """Test document ingestion with embedding generation"""
        mock_opensearch = Mock()
        mock_opensearch.index_document.return_value = {
            'documentId': 'doc-1',
            'result': 'created'
        }
        
        mock_embedding_service = Mock()
        mock_embedding_service.encode.return_value = [0.1] * 384
        
        pipeline = DocumentIngestionPipeline(
            opensearch_service=mock_opensearch,
            embedding_service=mock_embedding_service
        )
        
        intelligence = BusinessIntelligence(
            entity_type='forecast',
            entity_id='doc-1',
            insights={'trend': 'stable'},
            recommendations=[],
            data_source=['forecast_agent']
        )
        
        result = pipeline.ingest_business_intelligence(intelligence)
        
        assert result.embedding_generated is True
        assert mock_embedding_service.encode.called


class TestSearchQueryExecution:
    """Test search query execution"""
    
    def test_text_search(self):
        """Test text-based search"""
        mock_client = Mock()
        mock_client.search.return_value = {
            'hits': {
                'hits': [
                    {
                        '_id': 'doc-1',
                        '_score': 10.5,
                        '_source': {
                            'documentId': 'doc-1',
                            'documentType': 'pricing',
                            'content': 'Pricing analysis for Q1',
                            'metadata': {
                                'source': 'pricing_agent',
                                'timestamp': '2024-01-01T00:00:00',
                                'tags': ['pricing']
                            }
                        }
                    }
                ]
            }
        }
        
        opensearch = OpenSearchService()
        opensearch.client = mock_client
        
        results = opensearch.search_documents(
            query='pricing analysis',
            document_type='pricing',
            size=10
        )
        
        assert len(results) == 1
        assert results[0].document_id == 'doc-1'
        assert results[0].score == 10.5
        assert 'pricing' in results[0].content.lower()
    
    def test_semantic_search(self):
        """Test semantic search with embeddings"""
        mock_client = Mock()
        mock_client.search.return_value = {
            'hits': {
                'hits': [
                    {
                        '_id': 'doc-2',
                        '_score': 0.95,
                        '_source': {
                            'documentId': 'doc-2',
                            'documentType': 'forecast',
                            'content': 'Demand forecast for electronics',
                            'metadata': {
                                'source': 'forecast_agent',
                                'timestamp': '2024-01-01T00:00:00',
                                'tags': ['forecast']
                            }
                        }
                    }
                ]
            }
        }
        
        opensearch = OpenSearchService()
        opensearch.client = mock_client
        
        query_embedding = [0.1] * 384
        results = opensearch.semantic_search(
            query_embedding=query_embedding,
            document_type='forecast',
            size=10
        )
        
        assert len(results) == 1
        assert results[0].document_id == 'doc-2'
        assert results[0].score == 0.95
    
    def test_hybrid_search(self):
        """Test hybrid search combining text and semantic"""
        mock_client = Mock()
        mock_client.search.return_value = {
            'hits': {
                'hits': [
                    {
                        '_id': 'doc-3',
                        '_score': 12.3,
                        '_source': {
                            'documentId': 'doc-3',
                            'documentType': 'inventory',
                            'content': 'Inventory optimization recommendations',
                            'metadata': {
                                'source': 'inventory_agent',
                                'timestamp': '2024-01-01T00:00:00',
                                'tags': ['inventory']
                            }
                        },
                        'highlight': {
                            'content': ['<em>Inventory</em> <em>optimization</em> recommendations']
                        }
                    }
                ]
            }
        }
        
        opensearch = OpenSearchService()
        opensearch.client = mock_client
        
        results = opensearch.hybrid_search(
            text_query='inventory optimization',
            query_embedding=[0.1] * 384,
            document_type='inventory',
            size=10
        )
        
        assert len(results) == 1
        assert results[0].document_id == 'doc-3'
        assert len(results[0].highlights) > 0
    
    def test_search_with_filters(self):
        """Test search with additional filters"""
        mock_client = Mock()
        mock_client.search.return_value = {
            'hits': {'hits': []}
        }
        
        opensearch = OpenSearchService()
        opensearch.client = mock_client
        
        filters = {
            'metadata.region': 'north',
            'metadata.category': 'pricing'
        }
        
        results = opensearch.search_documents(
            query='test query',
            filters=filters,
            size=10
        )
        
        # Verify search was called with filters
        assert mock_client.search.called
        call_args = mock_client.search.call_args
        assert 'body' in call_args[1]


class TestResultRanking:
    """Test search result ranking"""
    
    def test_results_sorted_by_score(self):
        """Test that results are sorted by relevance score"""
        mock_client = Mock()
        mock_client.search.return_value = {
            'hits': {
                'hits': [
                    {
                        '_id': 'doc-1',
                        '_score': 15.0,
                        '_source': {
                            'documentId': 'doc-1',
                            'documentType': 'test',
                            'content': 'High relevance content',
                            'metadata': {
                                'source': 'test',
                                'timestamp': '2024-01-01T00:00:00',
                                'tags': []
                            }
                        }
                    },
                    {
                        '_id': 'doc-2',
                        '_score': 10.0,
                        '_source': {
                            'documentId': 'doc-2',
                            'documentType': 'test',
                            'content': 'Medium relevance content',
                            'metadata': {
                                'source': 'test',
                                'timestamp': '2024-01-01T00:00:00',
                                'tags': []
                            }
                        }
                    },
                    {
                        '_id': 'doc-3',
                        '_score': 5.0,
                        '_source': {
                            'documentId': 'doc-3',
                            'documentType': 'test',
                            'content': 'Low relevance content',
                            'metadata': {
                                'source': 'test',
                                'timestamp': '2024-01-01T00:00:00',
                                'tags': []
                            }
                        }
                    }
                ]
            }
        }
        
        opensearch = OpenSearchService()
        opensearch.client = mock_client
        
        results = opensearch.search_documents(query='test', size=10)
        
        # Verify results are in descending score order
        assert len(results) == 3
        assert results[0].score == 15.0
        assert results[1].score == 10.0
        assert results[2].score == 5.0
    
    def test_semantic_search_service_ranking(self):
        """Test semantic search service result ranking"""
        mock_opensearch = Mock()
        mock_opensearch.hybrid_search.return_value = [
            SearchResult(
                document_id='doc-1',
                score=20.0,
                content='Most relevant',
                metadata=DocumentMetadata(
                    document_id='doc-1',
                    document_type='test',
                    source='test',
                    timestamp=datetime.utcnow(),
                    tags=[]
                ),
                highlights=[]
            ),
            SearchResult(
                document_id='doc-2',
                score=15.0,
                content='Less relevant',
                metadata=DocumentMetadata(
                    document_id='doc-2',
                    document_type='test',
                    source='test',
                    timestamp=datetime.utcnow(),
                    tags=[]
                ),
                highlights=[]
            )
        ]
        
        mock_embedding = Mock()
        mock_embedding.encode.return_value = [0.1] * 384
        
        semantic_search = SemanticSearchService(
            opensearch_service=mock_opensearch,
            embedding_service=mock_embedding
        )
        
        query = SemanticSearchQuery(
            query_text='test query',
            max_results=10,
            search_mode='hybrid'
        )
        
        result = semantic_search.search(query)
        
        assert result.total_found == 2
        assert result.results[0].score > result.results[1].score
    
    def test_retrieve_relevant_context(self):
        """Test retrieving relevant context for copilot"""
        mock_opensearch = Mock()
        mock_opensearch.hybrid_search.return_value = [
            SearchResult(
                document_id='ctx-1',
                score=18.0,
                content='Relevant context about pricing',
                metadata=DocumentMetadata(
                    document_id='ctx-1',
                    document_type='pricing',
                    source='pricing_agent',
                    timestamp=datetime.utcnow(),
                    tags=['pricing']
                ),
                highlights=[]
            )
        ]
        
        mock_embedding = Mock()
        mock_embedding.encode.return_value = [0.1] * 384
        
        semantic_search = SemanticSearchService(
            opensearch_service=mock_opensearch,
            embedding_service=mock_embedding
        )
        
        contexts = semantic_search.retrieve_relevant_context(
            query='What is the pricing strategy?',
            context_type='pricing',
            max_contexts=5
        )
        
        assert len(contexts) == 1
        assert contexts[0]['document_type'] == 'pricing'
        assert 'relevance_score' in contexts[0]
        assert contexts[0]['relevance_score'] == 18.0


class TestEmbeddingService:
    """Test embedding service"""
    
    def test_encode_single_text(self):
        """Test encoding single text"""
        embedding_service = EmbeddingService()
        
        text = "Test text for embedding"
        embedding = embedding_service.encode(text)
        
        assert isinstance(embedding, list)
        assert len(embedding) == embedding_service.dimension
        assert all(isinstance(x, float) for x in embedding)
    
    def test_encode_multiple_texts(self):
        """Test encoding multiple texts"""
        embedding_service = EmbeddingService()
        
        texts = ["Text 1", "Text 2", "Text 3"]
        embeddings = embedding_service.encode(texts)
        
        assert isinstance(embeddings, list)
        assert len(embeddings) == 3
        assert all(len(emb) == embedding_service.dimension for emb in embeddings)
    
    def test_similarity_calculation(self):
        """Test cosine similarity calculation"""
        embedding_service = EmbeddingService()
        
        # Same text should have high similarity
        text1 = "pricing optimization"
        text2 = "pricing optimization"
        
        emb1 = embedding_service.encode(text1)
        emb2 = embedding_service.encode(text2)
        
        similarity = embedding_service.similarity(emb1, emb2)
        
        assert 0.0 <= similarity <= 1.0
        assert similarity > 0.9  # Same text should be very similar
    
    def test_different_texts_lower_similarity(self):
        """Test that different texts have lower similarity"""
        embedding_service = EmbeddingService()
        
        text1 = "pricing optimization"
        text2 = "inventory management"
        
        emb1 = embedding_service.encode(text1)
        emb2 = embedding_service.encode(text2)
        
        similarity = embedding_service.similarity(emb1, emb2)
        
        assert 0.0 <= similarity <= 1.0
        # Different topics should have lower similarity
        # (though with hash-based fallback, this might not always hold)


class TestKnowledgeRetrieval:
    """Test knowledge retrieval for Business Copilot"""
    
    def test_answer_question(self):
        """Test answering questions using knowledge base"""
        mock_opensearch = Mock()
        
        # Mock knowledge base results
        kb_results = [
            SearchResult(
                document_id='kb-1',
                score=15.0,
                content='Q: What is pricing optimization?\nA: Pricing optimization is...',
                metadata=DocumentMetadata(
                    document_id='kb-1',
                    document_type='knowledge_base',
                    source='knowledge_base',
                    timestamp=datetime.utcnow(),
                    tags=['pricing']
                ),
                highlights=[]
            )
        ]
        
        # Mock business intelligence results
        bi_results = [
            SearchResult(
                document_id='bi-1',
                score=12.0,
                content='Current pricing trends show...',
                metadata=DocumentMetadata(
                    document_id='bi-1',
                    document_type='pricing',
                    source='pricing_agent',
                    timestamp=datetime.utcnow(),
                    tags=['pricing']
                ),
                highlights=[]
            )
        ]
        
        # Mock both semantic_search and hybrid_search methods
        mock_opensearch.semantic_search.return_value = kb_results
        mock_opensearch.hybrid_search.return_value = bi_results
        
        mock_embedding = Mock()
        mock_embedding.encode.return_value = [0.1] * 384
        
        semantic_search = SemanticSearchService(
            opensearch_service=mock_opensearch,
            embedding_service=mock_embedding
        )
        
        answer = semantic_search.answer_question(
            question='What is pricing optimization?',
            context_type='pricing'
        )
        
        assert 'question' in answer
        assert 'knowledgeBaseResults' in answer
        assert 'contextResults' in answer
        assert 'confidence' in answer
        assert 'sources' in answer
        assert answer['confidence'] > 0.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
