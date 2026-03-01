"""
Unit tests for repository operations
Tests DynamoDB, S3, and Redshift repository CRUD operations
"""
import pytest
import json
import sys
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError

# Mock psycopg2 before importing repositories
sys.modules['psycopg2'] = MagicMock()
sys.modules['psycopg2.extras'] = MagicMock()

from src.models.agent_decision import AgentDecision, Recommendation
from src.models.workflow_instance import (
    WorkflowInstance, WorkflowStep, WorkflowPerformance,
    WorkflowStatus, WorkflowStepType
)
from src.models.business_intelligence import (
    BusinessIntelligence, Insights, ActionRecommendation,
    EntityType, Priority
)
from src.repositories.dynamodb_repository import (
    AgentDecisionRepository,
    WorkflowInstanceRepository,
    BusinessIntelligenceRepository
)
from src.repositories.s3_repository import S3Repository
from src.repositories.redshift_repository import RedshiftRepository


# DynamoDB Repository Tests

class TestAgentDecisionRepository:
    """Test AgentDecisionRepository CRUD operations"""

    @pytest.fixture
    def mock_table(self):
        """Create a mock DynamoDB table"""
        return Mock()

    @pytest.fixture
    def repository(self, mock_table):
        """Create repository with mocked table"""
        with patch('src.repositories.dynamodb_repository.aws_clients') as mock_clients:
            mock_clients.get_dynamodb_table.return_value = mock_table
            return AgentDecisionRepository()

    @pytest.fixture
    def sample_decision(self):
        """Create a sample AgentDecision for testing"""
        return AgentDecision(
            agent_id="market-intelligence-001",
            decision_id="decision-123",
            timestamp=datetime(2024, 1, 15, 10, 30, 0),
            input_data={"market": "electronics", "region": "north"},
            recommendation=Recommendation(
                action="adjust_pricing",
                confidence=0.85,
                reasoning="Competitor prices decreased by 5%",
                supporting_data=[{"competitor": "CompA", "price": 99.99}]
            ),
            escalation_required=False
        )

    def test_create_decision(self, repository, mock_table, sample_decision):
        """Test creating a new agent decision"""
        mock_table.put_item.return_value = {}
        
        result = repository.create(sample_decision)
        
        assert result == sample_decision
        mock_table.put_item.assert_called_once()

    def test_get_decision(self, repository, mock_table, sample_decision):
        """Test retrieving an agent decision"""
        mock_table.get_item.return_value = {'Item': sample_decision.to_dict()}
        
        result = repository.get("market-intelligence-001", "decision-123")
        
        assert result is not None
        assert result.agent_id == "market-intelligence-001"
        assert result.decision_id == "decision-123"

    def test_get_decision_not_found(self, repository, mock_table):
        """Test retrieving a non-existent decision"""
        mock_table.get_item.return_value = {}
        
        result = repository.get("nonexistent", "decision-999")
        
        assert result is None

    def test_update_decision(self, repository, mock_table, sample_decision):
        """Test updating an agent decision"""
        mock_table.put_item.return_value = {}
        
        result = repository.update(sample_decision)
        
        assert result == sample_decision
        mock_table.put_item.assert_called_once()

    def test_delete_decision(self, repository, mock_table):
        """Test deleting an agent decision"""
        mock_table.delete_item.return_value = {}
        
        result = repository.delete("market-intelligence-001", "decision-123")
        
        assert result is True
        mock_table.delete_item.assert_called_once()

    def test_list_decisions(self, repository, mock_table, sample_decision):
        """Test listing agent decisions"""
        mock_table.scan.return_value = {'Items': [sample_decision.to_dict()]}
        
        result = repository.list(limit=10)
        
        assert len(result) == 1
        assert result[0].agent_id == "market-intelligence-001"



class TestWorkflowInstanceRepository:
    """Test WorkflowInstanceRepository CRUD operations"""

    @pytest.fixture
    def mock_table(self):
        """Create a mock DynamoDB table"""
        return Mock()

    @pytest.fixture
    def repository(self, mock_table):
        """Create repository with mocked table"""
        with patch('src.repositories.dynamodb_repository.aws_clients') as mock_clients:
            mock_clients.get_dynamodb_table.return_value = mock_table
            return WorkflowInstanceRepository()

    @pytest.fixture
    def sample_workflow(self):
        """Create a sample WorkflowInstance for testing"""
        return WorkflowInstance(
            workflow_id="pricing-optimization-v1",
            instance_id="instance-456",
            status=WorkflowStatus.RUNNING,
            steps=[
                WorkflowStep(
                    step_id="step-1",
                    type=WorkflowStepType.LAMBDA,
                    configuration={"function": "analyze_pricing"},
                    conditions={}
                )
            ],
            created_by="system",
            generated_by="workflow-regeneration-agent-001",
            performance=WorkflowPerformance(
                execution_time=120.5,
                success_rate=0.95,
                business_impact=1500.0
            )
        )

    def test_create_workflow(self, repository, mock_table, sample_workflow):
        """Test creating a new workflow instance"""
        mock_table.put_item.return_value = {}
        
        result = repository.create(sample_workflow)
        
        assert result == sample_workflow
        mock_table.put_item.assert_called_once()

    def test_get_workflow(self, repository, mock_table, sample_workflow):
        """Test retrieving a workflow instance"""
        mock_table.get_item.return_value = {'Item': sample_workflow.to_dict()}
        
        result = repository.get("pricing-optimization-v1", "instance-456")
        
        assert result is not None
        assert result.workflow_id == "pricing-optimization-v1"
        assert result.status == WorkflowStatus.RUNNING

    def test_update_workflow(self, repository, mock_table, sample_workflow):
        """Test updating a workflow instance"""
        mock_table.put_item.return_value = {}
        
        result = repository.update(sample_workflow)
        
        assert result == sample_workflow
        mock_table.put_item.assert_called_once()

    def test_delete_workflow(self, repository, mock_table):
        """Test deleting a workflow instance"""
        mock_table.delete_item.return_value = {}
        
        result = repository.delete("pricing-optimization-v1", "instance-456")
        
        assert result is True
        mock_table.delete_item.assert_called_once()


class TestBusinessIntelligenceRepository:
    """Test BusinessIntelligenceRepository CRUD operations"""

    @pytest.fixture
    def mock_table(self):
        """Create a mock DynamoDB table"""
        return Mock()

    @pytest.fixture
    def repository(self, mock_table):
        """Create repository with mocked table"""
        with patch('src.repositories.dynamodb_repository.aws_clients') as mock_clients:
            mock_clients.get_dynamodb_table.return_value = mock_table
            return BusinessIntelligenceRepository()

    @pytest.fixture
    def sample_intelligence(self):
        """Create a sample BusinessIntelligence for testing"""
        return BusinessIntelligence(
            entity_type=EntityType.PRICING,
            entity_id="product-12345",
            insights=Insights(
                trend="increasing",
                prediction={"next_month_price": 105.99},
                confidence=0.88,
                timeframe="30-days"
            ),
            recommendations=[
                ActionRecommendation(
                    action="increase_price",
                    priority=Priority.HIGH,
                    expected_impact="Revenue increase of $5000"
                )
            ],
            data_source=["market-intelligence", "competitor-analysis"]
        )

    def test_create_intelligence(self, repository, mock_table, sample_intelligence):
        """Test creating a new business intelligence entity"""
        mock_table.put_item.return_value = {}
        
        result = repository.create(sample_intelligence)
        
        assert result == sample_intelligence
        mock_table.put_item.assert_called_once()

    def test_get_intelligence(self, repository, mock_table, sample_intelligence):
        """Test retrieving a business intelligence entity"""
        mock_table.get_item.return_value = {'Item': sample_intelligence.to_dict()}
        
        result = repository.get("pricing", "product-12345")
        
        assert result is not None
        assert result.entity_type == EntityType.PRICING
        assert result.entity_id == "product-12345"

    def test_update_intelligence(self, repository, mock_table, sample_intelligence):
        """Test updating a business intelligence entity"""
        mock_table.put_item.return_value = {}
        
        result = repository.update(sample_intelligence)
        
        assert result == sample_intelligence
        mock_table.put_item.assert_called_once()

    def test_delete_intelligence(self, repository, mock_table):
        """Test deleting a business intelligence entity"""
        mock_table.delete_item.return_value = {}
        
        result = repository.delete("pricing", "product-12345")
        
        assert result is True
        mock_table.delete_item.assert_called_once()



# S3 Repository Tests

class TestS3Repository:
    """Test S3Repository upload/download operations"""

    @pytest.fixture
    def mock_s3_client(self):
        """Create a mock S3 client"""
        return Mock()

    @pytest.fixture
    def repository(self, mock_s3_client):
        """Create repository with mocked S3 client"""
        with patch('src.repositories.s3_repository.aws_clients') as mock_clients:
            mock_clients.s3 = mock_s3_client
            return S3Repository(bucket_name="test-bucket")

    def test_upload_file(self, repository, mock_s3_client):
        """Test uploading a file to S3"""
        mock_s3_client.upload_file.return_value = None
        
        result = repository.upload_file("/path/to/file.txt", "data/file.txt")
        
        assert result is True
        mock_s3_client.upload_file.assert_called_once()

    def test_upload_data(self, repository, mock_s3_client):
        """Test uploading binary data to S3"""
        mock_s3_client.put_object.return_value = {}
        test_data = b"test binary data"
        
        result = repository.upload_data(test_data, "data/binary.bin")
        
        assert result is True
        mock_s3_client.put_object.assert_called_once()

    def test_upload_json(self, repository, mock_s3_client):
        """Test uploading JSON data to S3"""
        mock_s3_client.put_object.return_value = {}
        test_data = {"key": "value", "number": 42}
        
        result = repository.upload_json(test_data, "data/test.json")
        
        assert result is True
        mock_s3_client.put_object.assert_called_once()

    def test_download_file(self, repository, mock_s3_client):
        """Test downloading a file from S3"""
        mock_s3_client.download_file.return_value = None
        
        result = repository.download_file("data/file.txt", "/local/path/file.txt")
        
        assert result is True
        mock_s3_client.download_file.assert_called_once()

    def test_download_data(self, repository, mock_s3_client):
        """Test downloading binary data from S3"""
        test_data = b"downloaded data"
        mock_response = {'Body': Mock()}
        mock_response['Body'].read.return_value = test_data
        mock_s3_client.get_object.return_value = mock_response
        
        result = repository.download_data("data/binary.bin")
        
        assert result == test_data
        mock_s3_client.get_object.assert_called_once()

    def test_download_json(self, repository, mock_s3_client):
        """Test downloading and parsing JSON from S3"""
        test_data = {"key": "value", "number": 42}
        json_bytes = json.dumps(test_data).encode('utf-8')
        mock_response = {'Body': Mock()}
        mock_response['Body'].read.return_value = json_bytes
        mock_s3_client.get_object.return_value = mock_response
        
        result = repository.download_json("data/test.json")
        
        assert result == test_data
        mock_s3_client.get_object.assert_called_once()

    def test_delete(self, repository, mock_s3_client):
        """Test deleting an object from S3"""
        mock_s3_client.delete_object.return_value = {}
        
        result = repository.delete("data/file.txt")
        
        assert result is True
        mock_s3_client.delete_object.assert_called_once()

    def test_exists_true(self, repository, mock_s3_client):
        """Test checking if an object exists in S3"""
        mock_s3_client.head_object.return_value = {}
        
        result = repository.exists("data/file.txt")
        
        assert result is True
        mock_s3_client.head_object.assert_called_once()

    def test_exists_false(self, repository, mock_s3_client):
        """Test checking if a non-existent object exists in S3"""
        error_response = {'Error': {'Code': '404'}}
        mock_s3_client.head_object.side_effect = ClientError(error_response, 'head_object')
        
        result = repository.exists("data/nonexistent.txt")
        
        assert result is False

    def test_list_objects(self, repository, mock_s3_client):
        """Test listing objects in S3"""
        mock_response = {
            'Contents': [
                {
                    'Key': 'data/file1.txt',
                    'Size': 1024,
                    'LastModified': datetime(2024, 1, 15),
                    'ETag': '"abc123"'
                },
                {
                    'Key': 'data/file2.txt',
                    'Size': 2048,
                    'LastModified': datetime(2024, 1, 16),
                    'ETag': '"def456"'
                }
            ]
        }
        mock_s3_client.list_objects_v2.return_value = mock_response
        
        result = repository.list_objects(prefix="data/")
        
        assert len(result) == 2
        assert result[0]['key'] == 'data/file1.txt'
        assert result[1]['size'] == 2048



# Redshift Repository Tests

class TestRedshiftRepository:
    """Test RedshiftRepository query execution"""

    @pytest.fixture
    def repository(self):
        """Create repository"""
        return RedshiftRepository(
            host="test-cluster.redshift.amazonaws.com",
            port=5439,
            database="test_db",
            user="test_user",
            password="test_password"
        )

    def test_execute_query(self, repository):
        """Test executing a SELECT query"""
        mock_results = [
            {'product_id': 'P001', 'quantity': 100},
            {'product_id': 'P002', 'quantity': 200}
        ]
        
        with patch.object(repository, 'get_connection') as mock_get_conn:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_cursor.fetchall.return_value = mock_results
            mock_cursor.__enter__ = Mock(return_value=mock_cursor)
            mock_cursor.__exit__ = Mock(return_value=False)
            mock_conn.cursor.return_value = mock_cursor
            mock_conn.__enter__ = Mock(return_value=mock_conn)
            mock_conn.__exit__ = Mock(return_value=False)
            mock_get_conn.return_value = mock_conn
            
            result = repository.execute_query("SELECT * FROM products")
            
            assert len(result) == 2
            assert result[0]['product_id'] == 'P001'

    def test_execute_update(self, repository):
        """Test executing an UPDATE query"""
        with patch.object(repository, 'get_connection') as mock_get_conn:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_cursor.rowcount = 5
            mock_cursor.__enter__ = Mock(return_value=mock_cursor)
            mock_cursor.__exit__ = Mock(return_value=False)
            mock_conn.cursor.return_value = mock_cursor
            mock_conn.__enter__ = Mock(return_value=mock_conn)
            mock_conn.__exit__ = Mock(return_value=False)
            mock_get_conn.return_value = mock_conn
            
            result = repository.execute_update("UPDATE products SET price = 100")
            
            assert result == 5

    def test_get_sales_data(self, repository):
        """Test retrieving sales data"""
        mock_results = [
            {
                'transaction_id': 'T001',
                'date': '2024-01-15',
                'product_name': 'Product A',
                'quantity': 10,
                'total_amount': 1000.0
            }
        ]
        
        with patch.object(repository, 'get_connection') as mock_get_conn:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_cursor.fetchall.return_value = mock_results
            mock_cursor.__enter__ = Mock(return_value=mock_cursor)
            mock_cursor.__exit__ = Mock(return_value=False)
            mock_conn.cursor.return_value = mock_cursor
            mock_conn.__enter__ = Mock(return_value=mock_conn)
            mock_conn.__exit__ = Mock(return_value=False)
            mock_get_conn.return_value = mock_conn
            
            result = repository.get_sales_data('2024-01-01', '2024-01-31')
            
            assert len(result) == 1
            assert result[0]['transaction_id'] == 'T001'

    def test_get_inventory_status(self, repository):
        """Test retrieving inventory status"""
        mock_results = [
            {
                'product_id': 'P001',
                'product_name': 'Product A',
                'quantity_on_hand': 500,
                'quantity_available': 450
            }
        ]
        
        with patch.object(repository, 'get_connection') as mock_get_conn:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_cursor.fetchall.return_value = mock_results
            mock_cursor.__enter__ = Mock(return_value=mock_cursor)
            mock_cursor.__exit__ = Mock(return_value=False)
            mock_conn.cursor.return_value = mock_cursor
            mock_conn.__enter__ = Mock(return_value=mock_conn)
            mock_conn.__exit__ = Mock(return_value=False)
            mock_get_conn.return_value = mock_conn
            
            result = repository.get_inventory_status()
            
            assert len(result) == 1
            assert result[0]['product_id'] == 'P001'

    def test_get_demand_forecast_accuracy(self, repository):
        """Test retrieving demand forecast accuracy"""
        mock_results = [
            {
                'date': '2024-01-15',
                'product_name': 'Product A',
                'forecast_quantity': 100,
                'actual_quantity': 95,
                'forecast_accuracy': 0.95
            }
        ]
        
        with patch.object(repository, 'get_connection') as mock_get_conn:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_cursor.fetchall.return_value = mock_results
            mock_cursor.__enter__ = Mock(return_value=mock_cursor)
            mock_cursor.__exit__ = Mock(return_value=False)
            mock_conn.cursor.return_value = mock_cursor
            mock_conn.__enter__ = Mock(return_value=mock_conn)
            mock_conn.__exit__ = Mock(return_value=False)
            mock_get_conn.return_value = mock_conn
            
            result = repository.get_demand_forecast_accuracy('2024-01-01', '2024-01-31')
            
            assert len(result) == 1
            assert result[0]['forecast_accuracy'] == 0.95

    def test_get_agent_performance(self, repository):
        """Test retrieving agent performance metrics"""
        mock_results = [
            {
                'agent_id': 'market-intelligence-001',
                'agent_name': 'Market Intelligence Agent',
                'total_decisions': 150,
                'avg_confidence': 0.87
            }
        ]
        
        with patch.object(repository, 'get_connection') as mock_get_conn:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_cursor.fetchall.return_value = mock_results
            mock_cursor.__enter__ = Mock(return_value=mock_cursor)
            mock_cursor.__exit__ = Mock(return_value=False)
            mock_conn.cursor.return_value = mock_cursor
            mock_conn.__enter__ = Mock(return_value=mock_conn)
            mock_conn.__exit__ = Mock(return_value=False)
            mock_get_conn.return_value = mock_conn
            
            result = repository.get_agent_performance('2024-01-01', '2024-01-31')
            
            assert len(result) == 1
            assert result[0]['agent_id'] == 'market-intelligence-001'
