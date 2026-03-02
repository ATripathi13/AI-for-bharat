"""
Document Ingestion Pipeline for OpenSearch
Handles document processing, embedding generation, and indexing
"""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from datetime import datetime
import json
import uuid

from .opensearch_service import OpenSearchService, get_opensearch_service
from ..models.business_intelligence import BusinessIntelligence


@dataclass
class IngestionResult:
    """Result of document ingestion"""
    document_id: str
    status: str  # 'success', 'failed', 'partial'
    message: str
    indexed: bool
    embedding_generated: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'documentId': self.document_id,
            'status': self.status,
            'message': self.message,
            'indexed': self.indexed,
            'embeddingGenerated': self.embedding_generated
        }


class DocumentIngestionPipeline:
    """
    Pipeline for ingesting documents into OpenSearch
    Handles preprocessing, embedding generation, and indexing
    """
    
    def __init__(
        self,
        opensearch_service: Optional[OpenSearchService] = None,
        embedding_service: Optional[Any] = None
    ):
        """
        Initialize Document Ingestion Pipeline
        
        Args:
            opensearch_service: Optional OpenSearch service instance
            embedding_service: Optional embedding generation service
        """
        self.opensearch = opensearch_service or get_opensearch_service()
        self.embedding_service = embedding_service
        self.batch_size = 100
    
    def ingest_business_intelligence(
        self,
        intelligence: BusinessIntelligence
    ) -> IngestionResult:
        """
        Ingest business intelligence document
        
        Args:
            intelligence: BusinessIntelligence object
            
        Returns:
            IngestionResult with ingestion status
        """
        try:
            # Prepare document content
            content = self._prepare_bi_content(intelligence)
            
            # Generate embedding if service available
            embedding = None
            embedding_generated = False
            if self.embedding_service:
                embedding = self._generate_embedding(content)
                embedding_generated = True
            
            # Prepare metadata
            metadata = {
                'source': intelligence.entity_type,
                'timestamp': datetime.utcnow().isoformat(),
                'tags': [intelligence.entity_type],
                'region': intelligence.insights.get('region', 'global'),
                'category': intelligence.entity_type
            }
            
            # Index document
            result = self.opensearch.index_document(
                document_id=intelligence.entity_id,
                content=content,
                document_type=intelligence.entity_type,
                metadata=metadata,
                embedding=embedding
            )
            
            return IngestionResult(
                document_id=intelligence.entity_id,
                status='success',
                message=f'Successfully indexed {intelligence.entity_type} document',
                indexed=True,
                embedding_generated=embedding_generated
            )
            
        except Exception as e:
            return IngestionResult(
                document_id=intelligence.entity_id,
                status='failed',
                message=f'Failed to ingest document: {str(e)}',
                indexed=False,
                embedding_generated=False
            )
    
    def ingest_agent_decision(
        self,
        decision: Dict[str, Any]
    ) -> IngestionResult:
        """
        Ingest agent decision document
        
        Args:
            decision: Agent decision dictionary
            
        Returns:
            IngestionResult with ingestion status
        """
        try:
            document_id = decision.get('decisionId', str(uuid.uuid4()))
            
            # Prepare content
            content = self._prepare_decision_content(decision)
            
            # Generate embedding
            embedding = None
            embedding_generated = False
            if self.embedding_service:
                embedding = self._generate_embedding(content)
                embedding_generated = True
            
            # Prepare metadata
            metadata = {
                'source': decision.get('agentId', 'unknown'),
                'timestamp': decision.get('timestamp', datetime.utcnow().isoformat()),
                'tags': ['agent_decision', decision.get('agentId', 'unknown')],
                'confidence': decision.get('recommendation', {}).get('confidence', 0.0)
            }
            
            # Index document
            result = self.opensearch.index_document(
                document_id=document_id,
                content=content,
                document_type='agent_decision',
                metadata=metadata,
                embedding=embedding
            )
            
            return IngestionResult(
                document_id=document_id,
                status='success',
                message='Successfully indexed agent decision',
                indexed=True,
                embedding_generated=embedding_generated
            )
            
        except Exception as e:
            return IngestionResult(
                document_id=document_id,
                status='failed',
                message=f'Failed to ingest decision: {str(e)}',
                indexed=False,
                embedding_generated=False
            )
    
    def ingest_knowledge_base_entry(
        self,
        question: str,
        answer: str,
        category: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> IngestionResult:
        """
        Ingest knowledge base entry
        
        Args:
            question: Question text
            answer: Answer text
            category: Category of the Q&A
            metadata: Optional additional metadata
            
        Returns:
            IngestionResult with ingestion status
        """
        try:
            document_id = str(uuid.uuid4())
            
            # Prepare content (combine question and answer)
            content = f"Q: {question}\nA: {answer}"
            
            # Generate embedding
            embedding = None
            embedding_generated = False
            if self.embedding_service:
                embedding = self._generate_embedding(content)
                embedding_generated = True
            
            # Prepare document
            document = {
                'documentId': document_id,
                'question': question,
                'answer': answer,
                'category': category,
                'embedding': embedding,
                'metadata': {
                    'source': 'knowledge_base',
                    'timestamp': datetime.utcnow().isoformat(),
                    'usageCount': 0,
                    'averageRating': 0.0,
                    **(metadata or {})
                }
            }
            
            # Index in knowledge base index
            result = self.opensearch.index_document(
                document_id=document_id,
                content=content,
                document_type='knowledge_base',
                metadata=document['metadata'],
                embedding=embedding,
                index_name=self.opensearch.knowledge_base_index
            )
            
            return IngestionResult(
                document_id=document_id,
                status='success',
                message='Successfully indexed knowledge base entry',
                indexed=True,
                embedding_generated=embedding_generated
            )
            
        except Exception as e:
            return IngestionResult(
                document_id='',
                status='failed',
                message=f'Failed to ingest knowledge base entry: {str(e)}',
                indexed=False,
                embedding_generated=False
            )
    
    def bulk_ingest(
        self,
        documents: List[Dict[str, Any]],
        document_type: str
    ) -> Dict[str, Any]:
        """
        Bulk ingest multiple documents
        
        Args:
            documents: List of documents to ingest
            document_type: Type of documents
            
        Returns:
            Dictionary with bulk ingestion results
        """
        results = {
            'total': len(documents),
            'successful': 0,
            'failed': 0,
            'details': []
        }
        
        # Process in batches
        for i in range(0, len(documents), self.batch_size):
            batch = documents[i:i + self.batch_size]
            
            # Prepare batch documents
            prepared_docs = []
            for doc in batch:
                try:
                    # Generate embedding if service available
                    embedding = None
                    if self.embedding_service and 'content' in doc:
                        embedding = self._generate_embedding(doc['content'])
                    
                    prepared_doc = {
                        'documentId': doc.get('documentId', str(uuid.uuid4())),
                        'documentType': document_type,
                        'content': doc.get('content', ''),
                        'metadata': doc.get('metadata', {}),
                        'timestamp': datetime.utcnow().isoformat()
                    }
                    
                    if embedding:
                        prepared_doc['embedding'] = embedding
                    
                    prepared_docs.append(prepared_doc)
                    
                except Exception as e:
                    results['failed'] += 1
                    results['details'].append({
                        'documentId': doc.get('documentId', 'unknown'),
                        'status': 'failed',
                        'error': str(e)
                    })
            
            # Bulk index batch
            if prepared_docs:
                try:
                    bulk_result = self.opensearch.bulk_index_documents(prepared_docs)
                    results['successful'] += bulk_result['items']
                    
                except Exception as e:
                    results['failed'] += len(prepared_docs)
                    for doc in prepared_docs:
                        results['details'].append({
                            'documentId': doc['documentId'],
                            'status': 'failed',
                            'error': str(e)
                        })
        
        return results
    
    def _prepare_bi_content(self, intelligence: BusinessIntelligence) -> str:
        """Prepare business intelligence content for indexing"""
        parts = [
            f"Entity Type: {intelligence.entity_type}",
            f"Entity ID: {intelligence.entity_id}",
        ]
        
        # Add insights
        insights = intelligence.insights
        if insights:
            parts.append(f"Trend: {insights.get('trend', 'N/A')}")
            parts.append(f"Prediction: {insights.get('prediction', 'N/A')}")
            parts.append(f"Confidence: {insights.get('confidence', 0.0)}")
            parts.append(f"Timeframe: {insights.get('timeframe', 'N/A')}")
        
        # Add recommendations
        if intelligence.recommendations:
            parts.append("Recommendations:")
            for rec in intelligence.recommendations:
                parts.append(f"- {rec.get('action', 'N/A')}: {rec.get('description', 'N/A')}")
        
        return "\n".join(parts)
    
    def _prepare_decision_content(self, decision: Dict[str, Any]) -> str:
        """Prepare agent decision content for indexing"""
        parts = [
            f"Agent: {decision.get('agentId', 'unknown')}",
            f"Decision ID: {decision.get('decisionId', 'unknown')}",
        ]
        
        # Add recommendation
        recommendation = decision.get('recommendation', {})
        if recommendation:
            parts.append(f"Action: {recommendation.get('action', 'N/A')}")
            parts.append(f"Reasoning: {recommendation.get('reasoning', 'N/A')}")
            parts.append(f"Confidence: {recommendation.get('confidence', 0.0)}")
        
        return "\n".join(parts)
    
    def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate vector embedding for text
        
        Args:
            text: Text to embed
            
        Returns:
            Vector embedding or None if service unavailable
        """
        if not self.embedding_service:
            return None
        
        try:
            # Call embedding service (would use Bedrock or SageMaker in production)
            embedding = self.embedding_service.encode(text)
            return embedding.tolist() if hasattr(embedding, 'tolist') else embedding
        except Exception:
            return None
    
    def get_ingestion_stats(self) -> Dict[str, Any]:
        """
        Get ingestion statistics
        
        Returns:
            Dictionary with ingestion statistics
        """
        stats = {}
        
        # Get stats for each index
        for index_name in [
            self.opensearch.business_intelligence_index,
            self.opensearch.documents_index,
            self.opensearch.knowledge_base_index
        ]:
            try:
                index_stats = self.opensearch.get_index_stats(index_name)
                stats[index_name] = index_stats
            except Exception as e:
                stats[index_name] = {'error': str(e)}
        
        return stats


# Singleton instance
_ingestion_pipeline: Optional[DocumentIngestionPipeline] = None


def get_ingestion_pipeline() -> DocumentIngestionPipeline:
    """Get or create document ingestion pipeline instance"""
    global _ingestion_pipeline
    if _ingestion_pipeline is None:
        _ingestion_pipeline = DocumentIngestionPipeline()
    return _ingestion_pipeline
