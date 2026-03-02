"""
SageMaker Model Deployment and Serving for RetailMind AI
Handles model deployment, inference endpoints, drift detection, and A/B testing
"""
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from dataclasses import dataclass
from enum import Enum
import json
import statistics

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    boto3 = None
    ClientError = Exception


class EndpointStatus(Enum):
    """Endpoint status"""
    CREATING = "Creating"
    IN_SERVICE = "InService"
    UPDATING = "Updating"
    ROLLING_BACK = "RollingBack"
    DELETING = "Deleting"
    FAILED = "Failed"


class DriftStatus(Enum):
    """Model drift detection status"""
    NO_DRIFT = "no_drift"
    DRIFT_DETECTED = "drift_detected"
    INSUFFICIENT_DATA = "insufficient_data"


@dataclass
class ModelEndpointConfig:
    """Configuration for a SageMaker endpoint"""
    endpoint_name: str
    model_name: str
    instance_type: str
    initial_instance_count: int
    variant_name: str = "AllTraffic"
    initial_variant_weight: float = 1.0
    accelerator_type: Optional[str] = None
    tags: Optional[List[Dict[str, str]]] = None


@dataclass
class InferenceRequest:
    """Request for model inference"""
    endpoint_name: str
    input_data: Any
    content_type: str = "application/json"
    accept: str = "application/json"


@dataclass
class InferenceResponse:
    """Response from model inference"""
    predictions: Any
    model_version: str
    inference_time_ms: float
    endpoint_name: str
    timestamp: datetime


@dataclass
class DriftMetrics:
    """Model drift detection metrics"""
    endpoint_name: str
    model_version: str
    drift_status: DriftStatus
    drift_score: float
    baseline_metrics: Dict[str, float]
    current_metrics: Dict[str, float]
    detected_at: datetime
    recommendation: str


@dataclass
class ABTestConfig:
    """Configuration for A/B testing"""
    test_name: str
    endpoint_name: str
    variant_a: Dict[str, Any]  # model_name, weight
    variant_b: Dict[str, Any]  # model_name, weight
    traffic_split: Dict[str, float]  # variant_name -> weight
    metrics_to_track: List[str]
    duration_hours: int


class SageMakerDeploymentService:
    """
    SageMaker Model Deployment and Serving Service
    Manages model deployment, inference, monitoring, and A/B testing
    """
    
    def __init__(
        self,
        region_name: str = "us-east-1",
        s3_bucket: str = "retailmind-ml-artifacts"
    ):
        """
        Initialize SageMaker Deployment Service
        
        Args:
            region_name: AWS region
            s3_bucket: S3 bucket for ML artifacts
        """
        self.region_name = region_name
        self.s3_bucket = s3_bucket
        
        # Initialize AWS clients
        if boto3:
            self.sagemaker_client = boto3.client('sagemaker', region_name=region_name)
            self.sagemaker_runtime = boto3.client('sagemaker-runtime', region_name=region_name)
            self.s3_client = boto3.client('s3', region_name=region_name)
            self.cloudwatch = boto3.client('cloudwatch', region_name=region_name)
        else:
            self.sagemaker_client = None
            self.sagemaker_runtime = None
            self.s3_client = None
            self.cloudwatch = None
        
        # Drift detection baselines
        self.drift_baselines: Dict[str, Dict[str, float]] = {}
        
        # A/B test configurations
        self.ab_tests: Dict[str, ABTestConfig] = {}
    
    def create_model(
        self,
        model_name: str,
        model_artifact_path: str,
        role_arn: str,
        container_image: str,
        environment: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Create a SageMaker model
        
        Args:
            model_name: Name for the model
            model_artifact_path: S3 path to model artifacts
            role_arn: IAM role ARN for SageMaker
            container_image: Docker image for inference
            environment: Environment variables for the container
            
        Returns:
            Dictionary with model creation result
        """
        if not self.sagemaker_client:
            raise RuntimeError("boto3 not available - cannot create model")
        
        try:
            model_params = {
                'ModelName': model_name,
                'PrimaryContainer': {
                    'Image': container_image,
                    'ModelDataUrl': model_artifact_path
                },
                'ExecutionRoleArn': role_arn
            }
            
            if environment:
                model_params['PrimaryContainer']['Environment'] = environment
            
            response = self.sagemaker_client.create_model(**model_params)
            
            return {
                'status': 'success',
                'model_name': model_name,
                'model_arn': response['ModelArn']
            }
            
        except ClientError as e:
            return {
                'status': 'error',
                'error': str(e),
                'error_code': e.response['Error']['Code']
            }
    
    def create_endpoint_config(
        self,
        config: ModelEndpointConfig
    ) -> Dict[str, Any]:
        """
        Create endpoint configuration
        
        Args:
            config: ModelEndpointConfig with endpoint settings
            
        Returns:
            Dictionary with endpoint config creation result
        """
        if not self.sagemaker_client:
            raise RuntimeError("boto3 not available - cannot create endpoint config")
        
        try:
            endpoint_config_name = f"{config.endpoint_name}-config"
            
            production_variants = [{
                'VariantName': config.variant_name,
                'ModelName': config.model_name,
                'InstanceType': config.instance_type,
                'InitialInstanceCount': config.initial_instance_count,
                'InitialVariantWeight': config.initial_variant_weight
            }]
            
            if config.accelerator_type:
                production_variants[0]['AcceleratorType'] = config.accelerator_type
            
            params = {
                'EndpointConfigName': endpoint_config_name,
                'ProductionVariants': production_variants
            }
            
            if config.tags:
                params['Tags'] = config.tags
            
            response = self.sagemaker_client.create_endpoint_config(**params)
            
            return {
                'status': 'success',
                'endpoint_config_name': endpoint_config_name,
                'endpoint_config_arn': response['EndpointConfigArn']
            }
            
        except ClientError as e:
            return {
                'status': 'error',
                'error': str(e),
                'error_code': e.response['Error']['Code']
            }
    
    def create_endpoint(
        self,
        endpoint_name: str,
        endpoint_config_name: str,
        tags: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Create a SageMaker endpoint
        
        Args:
            endpoint_name: Name for the endpoint
            endpoint_config_name: Name of the endpoint configuration
            tags: Optional tags for the endpoint
            
        Returns:
            Dictionary with endpoint creation result
        """
        if not self.sagemaker_client:
            raise RuntimeError("boto3 not available - cannot create endpoint")
        
        try:
            params = {
                'EndpointName': endpoint_name,
                'EndpointConfigName': endpoint_config_name
            }
            
            if tags:
                params['Tags'] = tags
            
            response = self.sagemaker_client.create_endpoint(**params)
            
            return {
                'status': 'success',
                'endpoint_name': endpoint_name,
                'endpoint_arn': response['EndpointArn']
            }
            
        except ClientError as e:
            return {
                'status': 'error',
                'error': str(e),
                'error_code': e.response['Error']['Code']
            }
    
    def deploy_model(
        self,
        config: ModelEndpointConfig,
        model_artifact_path: str,
        role_arn: str,
        container_image: str
    ) -> Dict[str, Any]:
        """
        Deploy a model end-to-end (create model, config, and endpoint)
        
        Args:
            config: ModelEndpointConfig with deployment settings
            model_artifact_path: S3 path to model artifacts
            role_arn: IAM role ARN for SageMaker
            container_image: Docker image for inference
            
        Returns:
            Dictionary with deployment result
        """
        # Step 1: Create model
        model_result = self.create_model(
            model_name=config.model_name,
            model_artifact_path=model_artifact_path,
            role_arn=role_arn,
            container_image=container_image
        )
        
        if model_result['status'] != 'success':
            return model_result
        
        # Step 2: Create endpoint configuration
        config_result = self.create_endpoint_config(config)
        
        if config_result['status'] != 'success':
            return config_result
        
        # Step 3: Create endpoint
        endpoint_result = self.create_endpoint(
            endpoint_name=config.endpoint_name,
            endpoint_config_name=config_result['endpoint_config_name'],
            tags=config.tags
        )
        
        return {
            'status': 'success',
            'message': 'Model deployed successfully',
            'model_arn': model_result['model_arn'],
            'endpoint_config_arn': config_result['endpoint_config_arn'],
            'endpoint_arn': endpoint_result['endpoint_arn'],
            'endpoint_name': config.endpoint_name
        }
    
    def get_endpoint_status(self, endpoint_name: str) -> Dict[str, Any]:
        """
        Get status of an endpoint
        
        Args:
            endpoint_name: Name of the endpoint
            
        Returns:
            Dictionary with endpoint status
        """
        if not self.sagemaker_client:
            raise RuntimeError("boto3 not available - cannot get endpoint status")
        
        try:
            response = self.sagemaker_client.describe_endpoint(
                EndpointName=endpoint_name
            )
            
            return {
                'status': 'success',
                'endpoint_name': endpoint_name,
                'endpoint_status': response['EndpointStatus'],
                'creation_time': response.get('CreationTime'),
                'last_modified_time': response.get('LastModifiedTime'),
                'production_variants': response.get('ProductionVariants', [])
            }
            
        except ClientError as e:
            return {
                'status': 'error',
                'error': str(e),
                'error_code': e.response['Error']['Code']
            }
    
    def invoke_endpoint(
        self,
        request: InferenceRequest
    ) -> InferenceResponse:
        """
        Invoke endpoint for inference
        
        Args:
            request: InferenceRequest with input data
            
        Returns:
            InferenceResponse with predictions
        """
        if not self.sagemaker_runtime:
            raise RuntimeError("boto3 not available - cannot invoke endpoint")
        
        start_time = datetime.now(timezone.utc)
        
        try:
            # Prepare input data
            if isinstance(request.input_data, (dict, list)):
                body = json.dumps(request.input_data)
            else:
                body = request.input_data
            
            # Invoke endpoint
            response = self.sagemaker_runtime.invoke_endpoint(
                EndpointName=request.endpoint_name,
                Body=body,
                ContentType=request.content_type,
                Accept=request.accept
            )
            
            # Parse response
            result = json.loads(response['Body'].read().decode())
            
            end_time = datetime.now(timezone.utc)
            inference_time_ms = (end_time - start_time).total_seconds() * 1000
            
            return InferenceResponse(
                predictions=result,
                model_version=response.get('InvokedProductionVariant', 'unknown'),
                inference_time_ms=inference_time_ms,
                endpoint_name=request.endpoint_name,
                timestamp=end_time
            )
            
        except ClientError as e:
            raise RuntimeError(f"Inference failed: {str(e)}")
    
    def monitor_model_drift(
        self,
        endpoint_name: str,
        model_version: str,
        current_predictions: List[Any],
        actual_outcomes: List[Any]
    ) -> DriftMetrics:
        """
        Monitor model for drift
        
        Args:
            endpoint_name: Name of the endpoint
            model_version: Version of the model
            current_predictions: Recent predictions
            actual_outcomes: Actual outcomes for those predictions
            
        Returns:
            DriftMetrics with drift detection results
        """
        # Calculate current metrics
        current_metrics = self._calculate_performance_metrics(
            current_predictions,
            actual_outcomes
        )
        
        # Get baseline metrics
        baseline_key = f"{endpoint_name}:{model_version}"
        
        if baseline_key not in self.drift_baselines:
            # First time monitoring - set baseline
            self.drift_baselines[baseline_key] = current_metrics
            
            return DriftMetrics(
                endpoint_name=endpoint_name,
                model_version=model_version,
                drift_status=DriftStatus.INSUFFICIENT_DATA,
                drift_score=0.0,
                baseline_metrics=current_metrics,
                current_metrics=current_metrics,
                detected_at=datetime.now(timezone.utc),
                recommendation="Baseline established - continue monitoring"
            )
        
        baseline_metrics = self.drift_baselines[baseline_key]
        
        # Calculate drift score
        drift_score = self._calculate_drift_score(baseline_metrics, current_metrics)
        
        # Determine drift status
        if drift_score > 0.15:  # 15% degradation threshold
            drift_status = DriftStatus.DRIFT_DETECTED
            recommendation = "Model drift detected - consider retraining"
        else:
            drift_status = DriftStatus.NO_DRIFT
            recommendation = "No significant drift detected"
        
        return DriftMetrics(
            endpoint_name=endpoint_name,
            model_version=model_version,
            drift_status=drift_status,
            drift_score=drift_score,
            baseline_metrics=baseline_metrics,
            current_metrics=current_metrics,
            detected_at=datetime.now(timezone.utc),
            recommendation=recommendation
        )
    
    def _calculate_performance_metrics(
        self,
        predictions: List[Any],
        actuals: List[Any]
    ) -> Dict[str, float]:
        """
        Calculate performance metrics
        
        Args:
            predictions: Model predictions
            actuals: Actual outcomes
            
        Returns:
            Dictionary with performance metrics
        """
        if not predictions or not actuals or len(predictions) != len(actuals):
            return {'accuracy': 0.0, 'error_rate': 1.0}
        
        # Calculate accuracy (for classification) or error (for regression)
        errors = []
        for pred, actual in zip(predictions, actuals):
            if isinstance(pred, (int, float)) and isinstance(actual, (int, float)):
                # Regression - calculate absolute percentage error
                if actual != 0:
                    error = abs(pred - actual) / abs(actual)
                else:
                    error = abs(pred - actual)
                errors.append(error)
        
        if errors:
            mean_error = statistics.mean(errors)
            accuracy = max(0.0, 1.0 - mean_error)
        else:
            accuracy = 0.0
        
        return {
            'accuracy': accuracy,
            'error_rate': 1.0 - accuracy,
            'sample_size': len(predictions)
        }
    
    def _calculate_drift_score(
        self,
        baseline_metrics: Dict[str, float],
        current_metrics: Dict[str, float]
    ) -> float:
        """
        Calculate drift score
        
        Args:
            baseline_metrics: Baseline performance metrics
            current_metrics: Current performance metrics
            
        Returns:
            Drift score (0.0 = no drift, 1.0 = complete drift)
        """
        baseline_accuracy = baseline_metrics.get('accuracy', 0.0)
        current_accuracy = current_metrics.get('accuracy', 0.0)
        
        if baseline_accuracy == 0:
            return 0.0
        
        # Calculate relative degradation
        degradation = (baseline_accuracy - current_accuracy) / baseline_accuracy
        
        return max(0.0, degradation)
    
    def create_ab_test(
        self,
        config: ABTestConfig
    ) -> Dict[str, Any]:
        """
        Create A/B test for model comparison
        
        Args:
            config: ABTestConfig with test configuration
            
        Returns:
            Dictionary with A/B test creation result
        """
        if not self.sagemaker_client:
            raise RuntimeError("boto3 not available - cannot create A/B test")
        
        try:
            # Create endpoint config with multiple variants
            endpoint_config_name = f"{config.endpoint_name}-ab-test"
            
            production_variants = [
                {
                    'VariantName': 'VariantA',
                    'ModelName': config.variant_a['model_name'],
                    'InstanceType': config.variant_a.get('instance_type', 'ml.m5.xlarge'),
                    'InitialInstanceCount': config.variant_a.get('instance_count', 1),
                    'InitialVariantWeight': config.traffic_split.get('VariantA', 0.5)
                },
                {
                    'VariantName': 'VariantB',
                    'ModelName': config.variant_b['model_name'],
                    'InstanceType': config.variant_b.get('instance_type', 'ml.m5.xlarge'),
                    'InitialInstanceCount': config.variant_b.get('instance_count', 1),
                    'InitialVariantWeight': config.traffic_split.get('VariantB', 0.5)
                }
            ]
            
            self.sagemaker_client.create_endpoint_config(
                EndpointConfigName=endpoint_config_name,
                ProductionVariants=production_variants
            )
            
            # Store A/B test configuration
            self.ab_tests[config.test_name] = config
            
            return {
                'status': 'success',
                'test_name': config.test_name,
                'endpoint_config_name': endpoint_config_name,
                'message': 'A/B test created successfully'
            }
            
        except ClientError as e:
            return {
                'status': 'error',
                'error': str(e),
                'error_code': e.response['Error']['Code']
            }
    
    def get_ab_test_results(
        self,
        test_name: str
    ) -> Dict[str, Any]:
        """
        Get A/B test results
        
        Args:
            test_name: Name of the A/B test
            
        Returns:
            Dictionary with test results
        """
        if test_name not in self.ab_tests:
            return {
                'status': 'error',
                'message': f'A/B test {test_name} not found'
            }
        
        config = self.ab_tests[test_name]
        
        # In a real implementation, this would query CloudWatch metrics
        # For now, return placeholder results
        return {
            'status': 'success',
            'test_name': test_name,
            'endpoint_name': config.endpoint_name,
            'variants': {
                'VariantA': {
                    'model_name': config.variant_a['model_name'],
                    'traffic_percentage': config.traffic_split.get('VariantA', 0.5) * 100,
                    'metrics': {
                        'invocations': 0,
                        'latency_ms': 0.0,
                        'error_rate': 0.0
                    }
                },
                'VariantB': {
                    'model_name': config.variant_b['model_name'],
                    'traffic_percentage': config.traffic_split.get('VariantB', 0.5) * 100,
                    'metrics': {
                        'invocations': 0,
                        'latency_ms': 0.0,
                        'error_rate': 0.0
                    }
                }
            },
            'recommendation': 'Continue monitoring - insufficient data for recommendation'
        }
    
    def update_endpoint(
        self,
        endpoint_name: str,
        new_endpoint_config_name: str
    ) -> Dict[str, Any]:
        """
        Update an existing endpoint with new configuration
        
        Args:
            endpoint_name: Name of the endpoint to update
            new_endpoint_config_name: Name of the new endpoint configuration
            
        Returns:
            Dictionary with update result
        """
        if not self.sagemaker_client:
            raise RuntimeError("boto3 not available - cannot update endpoint")
        
        try:
            response = self.sagemaker_client.update_endpoint(
                EndpointName=endpoint_name,
                EndpointConfigName=new_endpoint_config_name
            )
            
            return {
                'status': 'success',
                'endpoint_name': endpoint_name,
                'endpoint_arn': response['EndpointArn'],
                'message': 'Endpoint update initiated'
            }
            
        except ClientError as e:
            return {
                'status': 'error',
                'error': str(e),
                'error_code': e.response['Error']['Code']
            }
    
    def delete_endpoint(self, endpoint_name: str) -> Dict[str, Any]:
        """
        Delete an endpoint
        
        Args:
            endpoint_name: Name of the endpoint to delete
            
        Returns:
            Dictionary with deletion result
        """
        if not self.sagemaker_client:
            raise RuntimeError("boto3 not available - cannot delete endpoint")
        
        try:
            self.sagemaker_client.delete_endpoint(
                EndpointName=endpoint_name
            )
            
            return {
                'status': 'success',
                'endpoint_name': endpoint_name,
                'message': 'Endpoint deletion initiated'
            }
            
        except ClientError as e:
            return {
                'status': 'error',
                'error': str(e),
                'error_code': e.response['Error']['Code']
            }
