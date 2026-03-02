"""
Amazon OpenSearch Service for Semantic Search
Provides document indexing, vector embeddings, and similarity search
"""
import os
import json
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional
from datetime import datetime
import uuid
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import boto3


@dataclass
class DocumentMetadata:
    """Metadata for indexed documents"""
    document_id: str
    document_type: str  # 'market_intelligence', 'forecast', 'pricing', 'inventory', 'risk'
    source: str
    timestamp: datetime
    tags: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'documentId': self.document_id,
            'documentType': self.document_type,
            'source': self.source,
            'timestamp': self.timestamp.isoformat(),
            'tags': self.tags
        }


@dataclass
class SearchResult:
    """Search result from OpenSearch"""
    document_id: str
    score: float
    content: str
    metadata: DocumentMetadata
    highlights: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'documentId': self.document_id,
            'score': self.score,
            'content': self.content,
            'metadata': self.metadata.to_dict(),
            'highlights': self.highlights
        }


class OpenSearchService:
    """
    Service for managing Amazon OpenSearch cluster and semantic search
    """
    
    def __init__(
        self,
        domain_endpoint: Optional[str] = None,
        region: Optional[str] = None
    ):
        """
        Initialize OpenSearch Service
        
        Args:
            domain_endpoint: OpenSearch domain endpoint (without https://)
            region: AWS region
        """
        self.region = region or os.getenv('AWS_REGION', 'us-east-1')
        self.domain_endpoint = domain_endpoint or os.getenv(
            'OPENSEARCH_ENDPOINT',
            'search-retailmind-ai.us-east-1.es.amazonaws.com'
        )
        
        # Initialize AWS authentication
        credentials = boto3.Session().get_credentials()
        if credentials:
            self.awsauth = AWS4Auth(
                credentials.access_key,
                credentials.secret_key,
                self.region,
                'es',
                session_token=credentials.token
            )
        else:
            # For testing without AWS credentials
            self.awsauth = None
        
        # Initialize OpenSearch client
        if self.awsauth:
            self.client = OpenSearch(
                hosts=[{'host': self.domain_endpoint, 'port': 443}],
                http_auth=self.awsauth,
                use_ssl=True,
                verify_certs=True,
                connection_class=RequestsHttpConnection,
                timeout=30
            )
        else:
            # For testing, create a mock client
            self.client = None
        
        # Index names
        self.business_intelligence_index = 'business-intelligence'
        self.documents_index = 'documents'
        self.knowledge_base_index = 'knowledge-base'
    
    def create_index_mappings(self) -> Dict[str, bool]:
        """
        Create index mappings for business intelligence documents
        
        Returns:
            Dictionary with index creation status
        """
        results = {}
        
        # Business Intelligence Index Mapping
        bi_mapping = {
            'settings': {
                'number_of_shards': 2,
                'number_of_replicas': 1,
                'analysis': {
                    'analyzer': {
                        'default': {
                            'type': 'standard',
                            'stopwords': '_english_'
                        }
                    }
                }
            },
            'mappings': {
                'properties': {
                    'documentId': {'type': 'keyword'},
                    'documentType': {'type': 'keyword'},
                    'title': {
                        'type': 'text',
                        'analyzer': 'standard',
                        'fields': {
                            'keyword': {'type': 'keyword'}
                        }
                    },
                    'content': {
                        'type': 'text',
                        'analyzer': 'standard'
                    },
                    'summary': {'type': 'text'},
                    'embedding': {
                        'type': 'knn_vector',
                        'dimension': 384,  # Sentence transformer dimension
                        'method': {
                            'name': 'hnsw',
                            'space_type': 'cosinesimil',
                            'engine': 'nmslib'
                        }
                    },
                    'metadata': {
                        'properties': {
                            'source': {'type': 'keyword'},
                            'timestamp': {'type': 'date'},
                            'tags': {'type': 'keyword'},
                            'region': {'type': 'keyword'},
                            'category': {'type': 'keyword'}
                        }
                    },
                    'insights': {
                        'properties': {
                            'trend': {'type': 'text'},
                            'prediction': {'type': 'text'},
                            'confidence': {'type': 'float'},
                            'timeframe': {'type': 'keyword'}
                        }
                    },
                    'recommendations': {
                        'type': 'nested',
                        'properties': {
                            'action': {'type': 'keyword'},
                            'description': {'type': 'text'},
                            'priority': {'type': 'keyword'},
                            'impact': {'type': 'float'}
                        }
                    }
                }
            }
        }
        
        # Create business intelligence index
        if not self.client.indices.exists(index=self.business_intelligence_index):
            self.client.indices.create(
                index=self.business_intelligence_index,
                body=bi_mapping
            )
            results[self.business_intelligence_index] = True
        else:
            results[self.business_intelligence_index] = False  # Already exists
        
        # Documents Index Mapping (for general documents)
        doc_mapping = {
            'settings': {
                'number_of_shards': 2,
                'number_of_replicas': 1
            },
            'mappings': {
                'properties': {
                    'documentId': {'type': 'keyword'},
                    'documentType': {'type': 'keyword'},
                    'title': {'type': 'text'},
                    'content': {'type': 'text'},
                    'embedding': {
                        'type': 'knn_vector',
                        'dimension': 384
                    },
                    'metadata': {
                        'properties': {
                            'source': {'type': 'keyword'},
                            'timestamp': {'type': 'date'},
                            'tags': {'type': 'keyword'}
                        }
                    }
                }
            }
        }
        
        # Create documents index
        if not self.client.indices.exists(index=self.documents_index):
            self.client.indices.create(
                index=self.documents_index,
                body=doc_mapping
            )
            results[self.documents_index] = True
        else:
            results[self.documents_index] = False
        
        # Knowledge Base Index Mapping
        kb_mapping = {
            'settings': {
                'number_of_shards': 1,
                'number_of_replicas': 1
            },
            'mappings': {
                'properties': {
                    'documentId': {'type': 'keyword'},
                    'question': {'type': 'text'},
                    'answer': {'type': 'text'},
                    'category': {'type': 'keyword'},
                    'embedding': {
                        'type': 'knn_vector',
                        'dimension': 384
                    },
                    'metadata': {
                        'properties': {
                            'source': {'type': 'keyword'},
                            'timestamp': {'type': 'date'},
                            'usageCount': {'type': 'integer'},
                            'averageRating': {'type': 'float'}
                        }
                    }
                }
            }
        }
        
        # Create knowledge base index
        if not self.client.indices.exists(index=self.knowledge_base_index):
            self.client.indices.create(
                index=self.knowledge_base_index,
                body=kb_mapping
            )
            results[self.knowledge_base_index] = True
        else:
            results[self.knowledge_base_index] = False
        
        return results
    
    def index_document(
        self,
        document_id: str,
        content: str,
        document_type: str,
        metadata: Dict[str, Any],
        embedding: Optional[List[float]] = None,
        index_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Index a document in OpenSearch
        
        Args:
            document_id: Unique document identifier
            content: Document content
            document_type: Type of document
            metadata: Document metadata
            embedding: Optional vector embedding
            index_name: Optional index name (defaults to business_intelligence_index)
            
        Returns:
            Dictionary with indexing result
        """
        index = index_name or self.business_intelligence_index
        
        document = {
            'documentId': document_id,
            'documentType': document_type,
            'content': content,
            'metadata': metadata,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if embedding:
            document['embedding'] = embedding
        
        response = self.client.index(
            index=index,
            id=document_id,
            body=document,
            refresh=True
        )
        
        return {
            'documentId': document_id,
            'index': index,
            'result': response['result'],
            'version': response['_version']
        }
    
    def bulk_index_documents(
        self,
        documents: List[Dict[str, Any]],
        index_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Bulk index multiple documents
        
        Args:
            documents: List of documents to index
            index_name: Optional index name
            
        Returns:
            Dictionary with bulk indexing results
        """
        index = index_name or self.business_intelligence_index
        
        bulk_body = []
        for doc in documents:
            bulk_body.append({
                'index': {
                    '_index': index,
                    '_id': doc.get('documentId', str(uuid.uuid4()))
                }
            })
            bulk_body.append(doc)
        
        response = self.client.bulk(body=bulk_body, refresh=True)
        
        return {
            'total': len(documents),
            'errors': response.get('errors', False),
            'items': len(response.get('items', []))
        }
    
    def search_documents(
        self,
        query: str,
        document_type: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        size: int = 10,
        index_name: Optional[str] = None
    ) -> List[SearchResult]:
        """
        Search documents using text query
        
        Args:
            query: Search query
            document_type: Optional document type filter
            filters: Optional additional filters
            size: Number of results to return
            index_name: Optional index name
            
        Returns:
            List of search results
        """
        index = index_name or self.business_intelligence_index
        
        # Build query
        must_clauses = [
            {
                'multi_match': {
                    'query': query,
                    'fields': ['title^2', 'content', 'summary'],
                    'type': 'best_fields'
                }
            }
        ]
        
        if document_type:
            must_clauses.append({
                'term': {'documentType': document_type}
            })
        
        if filters:
            for field, value in filters.items():
                must_clauses.append({
                    'term': {field: value}
                })
        
        search_body = {
            'query': {
                'bool': {
                    'must': must_clauses
                }
            },
            'size': size,
            'highlight': {
                'fields': {
                    'content': {},
                    'summary': {}
                }
            }
        }
        
        response = self.client.search(
            index=index,
            body=search_body
        )
        
        return self._parse_search_results(response)
    
    def semantic_search(
        self,
        query_embedding: List[float],
        document_type: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        size: int = 10,
        index_name: Optional[str] = None
    ) -> List[SearchResult]:
        """
        Perform semantic search using vector embeddings
        
        Args:
            query_embedding: Query vector embedding
            document_type: Optional document type filter
            filters: Optional additional filters
            size: Number of results to return
            index_name: Optional index name
            
        Returns:
            List of search results
        """
        index = index_name or self.business_intelligence_index
        
        # Build KNN query
        knn_query = {
            'knn': {
                'embedding': {
                    'vector': query_embedding,
                    'k': size
                }
            }
        }
        
        # Add filters if provided
        if document_type or filters:
            filter_clauses = []
            
            if document_type:
                filter_clauses.append({
                    'term': {'documentType': document_type}
                })
            
            if filters:
                for field, value in filters.items():
                    filter_clauses.append({
                        'term': {field: value}
                    })
            
            knn_query['knn']['embedding']['filter'] = {
                'bool': {
                    'must': filter_clauses
                }
            }
        
        search_body = {
            'query': knn_query,
            'size': size
        }
        
        response = self.client.search(
            index=index,
            body=search_body
        )
        
        return self._parse_search_results(response)
    
    def hybrid_search(
        self,
        text_query: str,
        query_embedding: List[float],
        document_type: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        size: int = 10,
        text_weight: float = 0.5,
        semantic_weight: float = 0.5,
        index_name: Optional[str] = None
    ) -> List[SearchResult]:
        """
        Perform hybrid search combining text and semantic search
        
        Args:
            text_query: Text search query
            query_embedding: Query vector embedding
            document_type: Optional document type filter
            filters: Optional additional filters
            size: Number of results to return
            text_weight: Weight for text search (0-1)
            semantic_weight: Weight for semantic search (0-1)
            index_name: Optional index name
            
        Returns:
            List of search results
        """
        index = index_name or self.business_intelligence_index
        
        # Build hybrid query
        should_clauses = [
            {
                'multi_match': {
                    'query': text_query,
                    'fields': ['title^2', 'content', 'summary'],
                    'boost': text_weight
                }
            }
        ]
        
        filter_clauses = []
        if document_type:
            filter_clauses.append({
                'term': {'documentType': document_type}
            })
        
        if filters:
            for field, value in filters.items():
                filter_clauses.append({
                    'term': {field: value}
                })
        
        search_body = {
            'query': {
                'bool': {
                    'should': should_clauses,
                    'filter': filter_clauses if filter_clauses else []
                }
            },
            'knn': {
                'embedding': {
                    'vector': query_embedding,
                    'k': size,
                    'boost': semantic_weight
                }
            },
            'size': size,
            'highlight': {
                'fields': {
                    'content': {},
                    'summary': {}
                }
            }
        }
        
        response = self.client.search(
            index=index,
            body=search_body
        )
        
        return self._parse_search_results(response)
    
    def _parse_search_results(self, response: Dict[str, Any]) -> List[SearchResult]:
        """Parse OpenSearch response into SearchResult objects"""
        results = []
        
        for hit in response['hits']['hits']:
            source = hit['_source']
            
            # Extract metadata
            metadata_dict = source.get('metadata', {})
            metadata = DocumentMetadata(
                document_id=source.get('documentId', hit['_id']),
                document_type=source.get('documentType', 'unknown'),
                source=metadata_dict.get('source', 'unknown'),
                timestamp=datetime.fromisoformat(
                    metadata_dict.get('timestamp', datetime.utcnow().isoformat())
                ),
                tags=metadata_dict.get('tags', [])
            )
            
            # Extract highlights
            highlights = []
            if 'highlight' in hit:
                for field, snippets in hit['highlight'].items():
                    highlights.extend(snippets)
            
            result = SearchResult(
                document_id=source.get('documentId', hit['_id']),
                score=hit['_score'],
                content=source.get('content', ''),
                metadata=metadata,
                highlights=highlights
            )
            
            results.append(result)
        
        return results
    
    def delete_document(
        self,
        document_id: str,
        index_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Delete a document from the index
        
        Args:
            document_id: Document ID to delete
            index_name: Optional index name
            
        Returns:
            Dictionary with deletion result
        """
        index = index_name or self.business_intelligence_index
        
        response = self.client.delete(
            index=index,
            id=document_id,
            refresh=True
        )
        
        return {
            'documentId': document_id,
            'result': response['result']
        }
    
    def get_index_stats(self, index_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get statistics for an index
        
        Args:
            index_name: Optional index name
            
        Returns:
            Dictionary with index statistics
        """
        index = index_name or self.business_intelligence_index
        
        stats = self.client.indices.stats(index=index)
        count = self.client.count(index=index)
        
        return {
            'index': index,
            'documentCount': count['count'],
            'sizeInBytes': stats['_all']['total']['store']['size_in_bytes'],
            'shards': stats['_shards']
        }
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check OpenSearch cluster health
        
        Returns:
            Dictionary with cluster health information
        """
        health = self.client.cluster.health()
        
        return {
            'status': health['status'],
            'clusterName': health['cluster_name'],
            'numberOfNodes': health['number_of_nodes'],
            'activeShards': health['active_shards'],
            'relocatingShards': health['relocating_shards'],
            'initializingShards': health['initializing_shards'],
            'unassignedShards': health['unassigned_shards']
        }


# Singleton instance
_opensearch_service: Optional[OpenSearchService] = None


def get_opensearch_service() -> OpenSearchService:
    """Get or create OpenSearch service instance"""
    global _opensearch_service
    if _opensearch_service is None:
        _opensearch_service = OpenSearchService()
    return _opensearch_service
