"""
Unit tests for ML Pipeline (SageMaker Training and Deployment)
Tests training job configuration, model deployment, and inference endpoints
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock

from src.services.sagemaker_training import (
    SageMakerTrainingPipeline,
    TrainingJobConfig,
    ModelVersion,
    RetrainingTrigger,
    TrainingStatus,
    ModelType,
    create_demand_forecast_training_config
)
from src.services.sagemaker_deployment import (
    SageMakerDeploymentService,
    ModelEndpointConfig,
    InferenceRequest,
    InferenceResponse,
    DriftMetrics,
    ABTestConfig,
    EndpointStatus,
    DriftStatus
)


class TestSageMakerTrainingPipeline:
    """Test SageMaker Training Pipeline"""
    
    @pytest.fixture
    def training_pipeline(self):
        """Create training pipeline instance"""
        with patch('src.services.sagemaker_training.boto3'):
            pipeline = SageMakerTrainingPipeline(
                region_name="us-east-1",
                s3_bucket="test-bucket",
                model_registry_table="test-registry"
            )
            # Mock AWS clients
            pipeline.sagemaker_client = Mock()
            pipeline.s3_client = Mock()
            pipeline.registry_table = Mock()
            return pipeline
    
    @pytest.fixture
    def training_config(self):
        """Create sample training configuration"""
        return TrainingJobConfig(
            job_name="test-training-job",
            model_type=ModelType.DEMAND_FORECAST,
            algorithm_specification={
                'TrainingImage': 'test-image:latest',
                'TrainingInputMode': 'File'
            },
            role_arn="arn:aws:iam::123456789012:role/SageMakerRole",
            input_data_config=[
                {
                    'ChannelName': 'train',
                    'DataSource': {
                        'S3DataSource': {
                            'S3DataType': 'S3Prefix',
                            'S3Uri': 's3://test-bucket/training-data',
                            'S3DataDistributionType': 'FullyReplicated'
                        }
                    }
                }
            ],
            output_data_config={
                'S3OutputPath': 's3://test-bucket/output'
            },
            resource_config={
                'InstanceType': 'ml.m5.xlarge',
                'InstanceCount': 1,
                'VolumeSizeInGB': 30
            },
            hyperparameters={'epochs': '100'},
            stopping_condition={'MaxRuntimeInSeconds': 3600}
        )
    
    def test_create_training_job_success(self, training_pipeline, training_config):
        """Test successful training job creation"""
        # Mock SageMaker response
        training_pipeline.sagemaker_client.create_training_job.return_value = {
            'TrainingJobArn': 'arn:aws:sagemaker:us-east-1:123456789012:training-job/test-job'
        }
        
        result = training_pipeline.create_training_job(training_config)
        
        assert result['status'] == 'success'
        assert 'training_job_arn' in result
        assert result['job_metadata']['job_name'] == 'test-training-job'
        assert result['job_metadata']['model_type'] == ModelType.DEMAND_FORECAST.value
        
        # Verify SageMaker client was called
        training_pipeline.sagemaker_client.create_training_job.assert_called_once()
    
    def test_create_training_job_with_optional_params(self, training_pipeline, training_config):
        """Test training job creation with optional parameters"""
        training_config.tags = [{'Key': 'Project', 'Value': 'RetailMind'}]
        
        training_pipeline.sagemaker_client.create_training_job.return_value = {
            'TrainingJobArn': 'arn:aws:sagemaker:us-east-1:123456789012:training-job/test-job'
        }
        
        result = training_pipeline.create_training_job(training_config)
        
        assert result['status'] == 'success'
        
        # Verify tags were included
        call_args = training_pipeline.sagemaker_client.create_training_job.call_args
        assert 'Tags' in call_args[1]
    
    def test_get_training_job_status(self, training_pipeline):
        """Test getting training job status"""
        training_pipeline.sagemaker_client.describe_training_job.return_value = {
            'TrainingJobStatus': 'Completed',
            'SecondaryStatus': 'Completed',
            'ModelArtifacts': {
                'S3ModelArtifacts': 's3://test-bucket/model.tar.gz'
            },
            'FinalMetricDataList': [
                {'MetricName': 'train:loss', 'Value': 0.15}
            ]
        }
        
        result = training_pipeline.get_training_job_status('test-job')
        
        assert result['status'] == 'success'
        assert result['training_job_status'] == 'Completed'
        assert result['model_artifacts'] == 's3://test-bucket/model.tar.gz'
    
    def test_register_model_version(self, training_pipeline):
        """Test model version registration"""
        model_version = ModelVersion(
            model_name="demand-forecast-model",
            version="v1.0.0",
            model_type=ModelType.DEMAND_FORECAST,
            training_job_name="test-job",
            model_artifact_path="s3://test-bucket/model.tar.gz",
            created_at=datetime.now(timezone.utc),
            metrics={'accuracy': 0.87},
            status='active'
        )
        
        result = training_pipeline.register_model_version(model_version)
        
        assert result['status'] == 'success'
        assert result['model_name'] == 'demand-forecast-model'
        assert result['version'] == 'v1.0.0'
        
        # Verify DynamoDB was called
        training_pipeline.registry_table.put_item.assert_called_once()
    
    def test_get_model_version_specific(self, training_pipeline):
        """Test getting specific model version"""
        training_pipeline.registry_table.get_item.return_value = {
            'Item': {
                'model_name': 'test-model',
                'version': 'v1.0.0',
                'model_type': 'demand_forecast',
                'metrics': {'accuracy': 0.87}
            }
        }
        
        result = training_pipeline.get_model_version('test-model', 'v1.0.0')
        
        assert result['status'] == 'success'
        assert result['model_version']['version'] == 'v1.0.0'
    
    def test_get_model_version_latest(self, training_pipeline):
        """Test getting latest model version"""
        training_pipeline.registry_table.query.return_value = {
            'Items': [
                {
                    'model_name': 'test-model',
                    'version': 'v2.0.0',
                    'metrics': {'accuracy': 0.90}
                }
            ]
        }
        
        result = training_pipeline.get_model_version('test-model')
        
        assert result['status'] == 'success'
        assert result['model_version']['version'] == 'v2.0.0'
    
    def test_list_model_versions(self, training_pipeline):
        """Test listing model versions"""
        training_pipeline.registry_table.query.return_value = {
            'Items': [
                {'model_name': 'test-model', 'version': 'v2.0.0'},
                {'model_name': 'test-model', 'version': 'v1.0.0'}
            ]
        }
        
        result = training_pipeline.list_model_versions('test-model', limit=10)
        
        assert result['status'] == 'success'
        assert result['count'] == 2
        assert len(result['versions']) == 2
    
    def test_create_retraining_trigger(self, training_pipeline):
        """Test creating retraining trigger"""
        trigger = RetrainingTrigger(
            trigger_id="accuracy-trigger",
            model_type=ModelType.DEMAND_FORECAST,
            trigger_type="accuracy_degradation",
            threshold=0.80,
            enabled=True
        )
        
        result = training_pipeline.create_retraining_trigger(trigger)
        
        assert result['status'] == 'success'
        assert result['trigger_id'] == 'accuracy-trigger'
        assert 'accuracy-trigger' in training_pipeline.retraining_triggers
    
    def test_check_retraining_triggers_accuracy_degradation(self, training_pipeline):
        """Test checking retraining triggers for accuracy degradation"""
        # Create trigger
        trigger = RetrainingTrigger(
            trigger_id="accuracy-trigger",
            model_type=ModelType.DEMAND_FORECAST,
            trigger_type="accuracy_degradation",
            threshold=0.85,
            enabled=True
        )
        training_pipeline.create_retraining_trigger(trigger)
        
        # Check with low accuracy
        result = training_pipeline.check_retraining_triggers(
            ModelType.DEMAND_FORECAST,
            {'accuracy': 0.75}
        )
        
        assert result['status'] == 'success'
        assert result['triggered_count'] == 1
        assert len(result['triggered']) == 1
        assert result['triggered'][0]['trigger_type'] == 'accuracy_degradation'
    
    def test_check_retraining_triggers_no_trigger(self, training_pipeline):
        """Test checking retraining triggers when threshold not met"""
        trigger = RetrainingTrigger(
            trigger_id="accuracy-trigger",
            model_type=ModelType.DEMAND_FORECAST,
            trigger_type="accuracy_degradation",
            threshold=0.80,
            enabled=True
        )
        training_pipeline.create_retraining_trigger(trigger)
        
        # Check with good accuracy
        result = training_pipeline.check_retraining_triggers(
            ModelType.DEMAND_FORECAST,
            {'accuracy': 0.90}
        )
        
        assert result['status'] == 'success'
        assert result['triggered_count'] == 0
    
    def test_trigger_retraining(self, training_pipeline, training_config):
        """Test triggering model retraining"""
        training_pipeline.sagemaker_client.create_training_job.return_value = {
            'TrainingJobArn': 'arn:aws:sagemaker:us-east-1:123456789012:training-job/retrain-job'
        }
        training_pipeline.s3_client.put_object.return_value = {}
        
        result = training_pipeline.trigger_retraining(
            ModelType.DEMAND_FORECAST,
            "accuracy_degradation",
            training_config
        )
        
        assert result['status'] == 'success'
        assert 'training_job_arn' in result
        assert result['retraining_event']['reason'] == 'accuracy_degradation'
    
    def test_create_demand_forecast_training_config(self):
        """Test creating demand forecast training configuration"""
        config = create_demand_forecast_training_config(
            job_name="test-job",
            role_arn="arn:aws:iam::123456789012:role/SageMakerRole",
            training_data_s3_path="s3://bucket/data",
            output_s3_path="s3://bucket/output"
        )
        
        assert config.job_name == "test-job"
        assert config.model_type == ModelType.DEMAND_FORECAST
        assert config.hyperparameters is not None
        assert 'epochs' in config.hyperparameters
        assert config.resource_config['InstanceType'] == 'ml.m5.xlarge'


class TestSageMakerDeploymentService:
    """Test SageMaker Deployment Service"""
    
    @pytest.fixture
    def deployment_service(self):
        """Create deployment service instance"""
        with patch('src.services.sagemaker_deployment.boto3'):
            service = SageMakerDeploymentService(
                region_name="us-east-1",
                s3_bucket="test-bucket"
            )
            # Mock AWS clients
            service.sagemaker_client = Mock()
            service.sagemaker_runtime = Mock()
            service.s3_client = Mock()
            service.cloudwatch = Mock()
            return service
    
    @pytest.fixture
    def endpoint_config(self):
        """Create sample endpoint configuration"""
        return ModelEndpointConfig(
            endpoint_name="test-endpoint",
            model_name="test-model",
            instance_type="ml.m5.xlarge",
            initial_instance_count=1,
            variant_name="AllTraffic"
        )
    
    def test_create_model(self, deployment_service):
        """Test creating a SageMaker model"""
        deployment_service.sagemaker_client.create_model.return_value = {
            'ModelArn': 'arn:aws:sagemaker:us-east-1:123456789012:model/test-model'
        }
        
        result = deployment_service.create_model(
            model_name="test-model",
            model_artifact_path="s3://bucket/model.tar.gz",
            role_arn="arn:aws:iam::123456789012:role/SageMakerRole",
            container_image="test-image:latest"
        )
        
        assert result['status'] == 'success'
        assert result['model_name'] == 'test-model'
        assert 'model_arn' in result
    
    def test_create_endpoint_config(self, deployment_service, endpoint_config):
        """Test creating endpoint configuration"""
        deployment_service.sagemaker_client.create_endpoint_config.return_value = {
            'EndpointConfigArn': 'arn:aws:sagemaker:us-east-1:123456789012:endpoint-config/test-config'
        }
        
        result = deployment_service.create_endpoint_config(endpoint_config)
        
        assert result['status'] == 'success'
        assert 'endpoint_config_name' in result
        assert 'endpoint_config_arn' in result
    
    def test_create_endpoint(self, deployment_service):
        """Test creating an endpoint"""
        deployment_service.sagemaker_client.create_endpoint.return_value = {
            'EndpointArn': 'arn:aws:sagemaker:us-east-1:123456789012:endpoint/test-endpoint'
        }
        
        result = deployment_service.create_endpoint(
            endpoint_name="test-endpoint",
            endpoint_config_name="test-config"
        )
        
        assert result['status'] == 'success'
        assert result['endpoint_name'] == 'test-endpoint'
        assert 'endpoint_arn' in result
    
    def test_deploy_model_end_to_end(self, deployment_service, endpoint_config):
        """Test end-to-end model deployment"""
        # Mock all three steps
        deployment_service.sagemaker_client.create_model.return_value = {
            'ModelArn': 'arn:aws:sagemaker:us-east-1:123456789012:model/test-model'
        }
        deployment_service.sagemaker_client.create_endpoint_config.return_value = {
            'EndpointConfigArn': 'arn:aws:sagemaker:us-east-1:123456789012:endpoint-config/test-config'
        }
        deployment_service.sagemaker_client.create_endpoint.return_value = {
            'EndpointArn': 'arn:aws:sagemaker:us-east-1:123456789012:endpoint/test-endpoint'
        }
        
        result = deployment_service.deploy_model(
            config=endpoint_config,
            model_artifact_path="s3://bucket/model.tar.gz",
            role_arn="arn:aws:iam::123456789012:role/SageMakerRole",
            container_image="test-image:latest"
        )
        
        assert result['status'] == 'success'
        assert 'model_arn' in result
        assert 'endpoint_config_arn' in result
        assert 'endpoint_arn' in result
    
    def test_get_endpoint_status(self, deployment_service):
        """Test getting endpoint status"""
        deployment_service.sagemaker_client.describe_endpoint.return_value = {
            'EndpointStatus': 'InService',
            'CreationTime': datetime.now(timezone.utc),
            'ProductionVariants': [
                {
                    'VariantName': 'AllTraffic',
                    'CurrentWeight': 1.0,
                    'DesiredWeight': 1.0
                }
            ]
        }
        
        result = deployment_service.get_endpoint_status('test-endpoint')
        
        assert result['status'] == 'success'
        assert result['endpoint_status'] == 'InService'
        assert len(result['production_variants']) == 1
    
    def test_invoke_endpoint(self, deployment_service):
        """Test invoking endpoint for inference"""
        # Mock runtime response
        mock_response = Mock()
        mock_response.__getitem__ = Mock(side_effect=lambda x: {
            'Body': Mock(read=Mock(return_value=b'{"predictions": [1.5, 2.3, 3.1]}'))
        }[x])
        mock_response.get = Mock(return_value='AllTraffic')
        
        deployment_service.sagemaker_runtime.invoke_endpoint.return_value = mock_response
        
        request = InferenceRequest(
            endpoint_name="test-endpoint",
            input_data={"instances": [[1, 2, 3]]}
        )
        
        response = deployment_service.invoke_endpoint(request)
        
        assert isinstance(response, InferenceResponse)
        assert response.endpoint_name == 'test-endpoint'
        assert response.predictions is not None
        assert response.inference_time_ms >= 0  # Can be 0 for fast mocked calls
    
    def test_monitor_model_drift_no_baseline(self, deployment_service):
        """Test drift monitoring when no baseline exists"""
        predictions = [1.0, 2.0, 3.0]
        actuals = [1.1, 2.1, 2.9]
        
        metrics = deployment_service.monitor_model_drift(
            endpoint_name="test-endpoint",
            model_version="v1.0.0",
            current_predictions=predictions,
            actual_outcomes=actuals
        )
        
        assert metrics.drift_status == DriftStatus.INSUFFICIENT_DATA
        assert metrics.drift_score == 0.0
        assert "Baseline established" in metrics.recommendation
    
    def test_monitor_model_drift_with_baseline(self, deployment_service):
        """Test drift monitoring with established baseline"""
        # Set baseline
        deployment_service.drift_baselines["test-endpoint:v1.0.0"] = {
            'accuracy': 0.90,
            'error_rate': 0.10
        }
        
        # Monitor with degraded performance
        predictions = [1.0, 2.0, 3.0, 4.0, 5.0]
        actuals = [1.5, 2.5, 3.5, 4.5, 5.5]  # Higher errors
        
        metrics = deployment_service.monitor_model_drift(
            endpoint_name="test-endpoint",
            model_version="v1.0.0",
            current_predictions=predictions,
            actual_outcomes=actuals
        )
        
        assert metrics.drift_status in [DriftStatus.DRIFT_DETECTED, DriftStatus.NO_DRIFT]
        assert metrics.drift_score >= 0.0
    
    def test_create_ab_test(self, deployment_service):
        """Test creating A/B test"""
        deployment_service.sagemaker_client.create_endpoint_config.return_value = {
            'EndpointConfigArn': 'arn:aws:sagemaker:us-east-1:123456789012:endpoint-config/ab-test'
        }
        
        config = ABTestConfig(
            test_name="model-comparison",
            endpoint_name="test-endpoint",
            variant_a={'model_name': 'model-v1'},
            variant_b={'model_name': 'model-v2'},
            traffic_split={'VariantA': 0.5, 'VariantB': 0.5},
            metrics_to_track=['latency', 'accuracy'],
            duration_hours=24
        )
        
        result = deployment_service.create_ab_test(config)
        
        assert result['status'] == 'success'
        assert result['test_name'] == 'model-comparison'
        assert 'model-comparison' in deployment_service.ab_tests
    
    def test_get_ab_test_results(self, deployment_service):
        """Test getting A/B test results"""
        # Create test first
        config = ABTestConfig(
            test_name="test-1",
            endpoint_name="test-endpoint",
            variant_a={'model_name': 'model-v1'},
            variant_b={'model_name': 'model-v2'},
            traffic_split={'VariantA': 0.5, 'VariantB': 0.5},
            metrics_to_track=['latency'],
            duration_hours=24
        )
        deployment_service.ab_tests['test-1'] = config
        
        result = deployment_service.get_ab_test_results('test-1')
        
        assert result['status'] == 'success'
        assert 'variants' in result
        assert 'VariantA' in result['variants']
        assert 'VariantB' in result['variants']
    
    def test_update_endpoint(self, deployment_service):
        """Test updating an endpoint"""
        deployment_service.sagemaker_client.update_endpoint.return_value = {
            'EndpointArn': 'arn:aws:sagemaker:us-east-1:123456789012:endpoint/test-endpoint'
        }
        
        result = deployment_service.update_endpoint(
            endpoint_name="test-endpoint",
            new_endpoint_config_name="new-config"
        )
        
        assert result['status'] == 'success'
        assert result['endpoint_name'] == 'test-endpoint'
    
    def test_delete_endpoint(self, deployment_service):
        """Test deleting an endpoint"""
        deployment_service.sagemaker_client.delete_endpoint.return_value = {}
        
        result = deployment_service.delete_endpoint('test-endpoint')
        
        assert result['status'] == 'success'
        assert result['endpoint_name'] == 'test-endpoint'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
