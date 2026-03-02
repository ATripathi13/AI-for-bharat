"""
SageMaker Training Pipeline for RetailMind AI
Handles model training, versioning, and automated retraining triggers
"""
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from dataclasses import dataclass
from enum import Enum
import json

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    boto3 = None
    ClientError = Exception


class TrainingStatus(Enum):
    """Training job status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


class ModelType(Enum):
    """Types of ML models"""
    DEMAND_FORECAST = "demand_forecast"
    PRICE_OPTIMIZATION = "price_optimization"
    FRAUD_DETECTION = "fraud_detection"


@dataclass
class TrainingJobConfig:
    """Configuration for a SageMaker training job"""
    job_name: str
    model_type: ModelType
    algorithm_specification: Dict[str, Any]
    role_arn: str
    input_data_config: List[Dict[str, Any]]
    output_data_config: Dict[str, Any]
    resource_config: Dict[str, Any]
    hyperparameters: Optional[Dict[str, str]] = None
    stopping_condition: Optional[Dict[str, int]] = None
    tags: Optional[List[Dict[str, str]]] = None


@dataclass
class ModelVersion:
    """Model version metadata"""
    model_name: str
    version: str
    model_type: ModelType
    training_job_name: str
    model_artifact_path: str
    created_at: datetime
    metrics: Dict[str, float]
    status: str
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class RetrainingTrigger:
    """Trigger for automated model retraining"""
    trigger_id: str
    model_type: ModelType
    trigger_type: str  # 'accuracy_degradation', 'scheduled', 'manual'
    threshold: Optional[float] = None
    schedule: Optional[str] = None
    enabled: bool = True


class SageMakerTrainingPipeline:
    """
    SageMaker Training Pipeline
    Manages ML model training, versioning, and automated retraining
    """
    
    def __init__(
        self,
        region_name: str = "us-east-1",
        s3_bucket: str = "retailmind-ml-artifacts",
        model_registry_table: str = "retailmind-model-registry"
    ):
        """
        Initialize SageMaker Training Pipeline
        
        Args:
            region_name: AWS region
            s3_bucket: S3 bucket for ML artifacts
            model_registry_table: DynamoDB table for model registry
        """
        self.region_name = region_name
        self.s3_bucket = s3_bucket
        self.model_registry_table = model_registry_table
        
        # Initialize AWS clients
        if boto3:
            self.sagemaker_client = boto3.client('sagemaker', region_name=region_name)
            self.s3_client = boto3.client('s3', region_name=region_name)
            self.dynamodb = boto3.resource('dynamodb', region_name=region_name)
            self.registry_table = self.dynamodb.Table(model_registry_table)
        else:
            self.sagemaker_client = None
            self.s3_client = None
            self.dynamodb = None
            self.registry_table = None
        
        # Active retraining triggers
        self.retraining_triggers: Dict[str, RetrainingTrigger] = {}
    
    def create_training_job(
        self,
        config: TrainingJobConfig
    ) -> Dict[str, Any]:
        """
        Create a SageMaker training job
        
        Args:
            config: TrainingJobConfig with job configuration
            
        Returns:
            Dictionary with training job details
        """
        if not self.sagemaker_client:
            raise RuntimeError("boto3 not available - cannot create training job")
        
        # Prepare training job parameters
        training_params = {
            'TrainingJobName': config.job_name,
            'AlgorithmSpecification': config.algorithm_specification,
            'RoleArn': config.role_arn,
            'InputDataConfig': config.input_data_config,
            'OutputDataConfig': config.output_data_config,
            'ResourceConfig': config.resource_config
        }
        
        # Add optional parameters
        if config.hyperparameters:
            training_params['HyperParameters'] = config.hyperparameters
        
        if config.stopping_condition:
            training_params['StoppingCondition'] = config.stopping_condition
        else:
            training_params['StoppingCondition'] = {'MaxRuntimeInSeconds': 86400}  # 24 hours
        
        if config.tags:
            training_params['Tags'] = config.tags
        
        try:
            # Create training job
            response = self.sagemaker_client.create_training_job(**training_params)
            
            # Store job metadata
            job_metadata = {
                'job_name': config.job_name,
                'model_type': config.model_type.value,
                'training_job_arn': response['TrainingJobArn'],
                'status': TrainingStatus.IN_PROGRESS.value,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'config': {
                    'algorithm': config.algorithm_specification,
                    'hyperparameters': config.hyperparameters,
                    'resource_config': config.resource_config
                }
            }
            
            return {
                'status': 'success',
                'training_job_arn': response['TrainingJobArn'],
                'job_metadata': job_metadata
            }
            
        except ClientError as e:
            return {
                'status': 'error',
                'error': str(e),
                'error_code': e.response['Error']['Code']
            }
    
    def get_training_job_status(self, job_name: str) -> Dict[str, Any]:
        """
        Get status of a training job
        
        Args:
            job_name: Name of the training job
            
        Returns:
            Dictionary with job status and details
        """
        if not self.sagemaker_client:
            raise RuntimeError("boto3 not available - cannot get training job status")
        
        try:
            response = self.sagemaker_client.describe_training_job(
                TrainingJobName=job_name
            )
            
            return {
                'status': 'success',
                'job_name': job_name,
                'training_job_status': response['TrainingJobStatus'],
                'secondary_status': response.get('SecondaryStatus'),
                'failure_reason': response.get('FailureReason'),
                'model_artifacts': response.get('ModelArtifacts', {}).get('S3ModelArtifacts'),
                'training_start_time': response.get('TrainingStartTime'),
                'training_end_time': response.get('TrainingEndTime'),
                'billable_time_in_seconds': response.get('BillableTimeInSeconds'),
                'final_metric_data_list': response.get('FinalMetricDataList', [])
            }
            
        except ClientError as e:
            return {
                'status': 'error',
                'error': str(e),
                'error_code': e.response['Error']['Code']
            }
    
    def register_model_version(
        self,
        model_version: ModelVersion
    ) -> Dict[str, Any]:
        """
        Register a new model version in the model registry
        
        Args:
            model_version: ModelVersion object with version details
            
        Returns:
            Dictionary with registration result
        """
        if not self.registry_table:
            raise RuntimeError("DynamoDB not available - cannot register model version")
        
        try:
            # Create registry entry
            item = {
                'model_name': model_version.model_name,
                'version': model_version.version,
                'model_type': model_version.model_type.value,
                'training_job_name': model_version.training_job_name,
                'model_artifact_path': model_version.model_artifact_path,
                'created_at': model_version.created_at.isoformat(),
                'metrics': model_version.metrics,
                'status': model_version.status,
                'metadata': model_version.metadata or {}
            }
            
            # Store in DynamoDB
            self.registry_table.put_item(Item=item)
            
            return {
                'status': 'success',
                'model_name': model_version.model_name,
                'version': model_version.version,
                'message': 'Model version registered successfully'
            }
            
        except ClientError as e:
            return {
                'status': 'error',
                'error': str(e),
                'error_code': e.response['Error']['Code']
            }
    
    def get_model_version(
        self,
        model_name: str,
        version: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get model version from registry
        
        Args:
            model_name: Name of the model
            version: Specific version (if None, returns latest)
            
        Returns:
            Dictionary with model version details
        """
        if not self.registry_table:
            raise RuntimeError("DynamoDB not available - cannot get model version")
        
        try:
            if version:
                # Get specific version
                response = self.registry_table.get_item(
                    Key={
                        'model_name': model_name,
                        'version': version
                    }
                )
                
                if 'Item' in response:
                    return {
                        'status': 'success',
                        'model_version': response['Item']
                    }
                else:
                    return {
                        'status': 'not_found',
                        'message': f'Model version {version} not found'
                    }
            else:
                # Get latest version
                response = self.registry_table.query(
                    KeyConditionExpression='model_name = :model_name',
                    ExpressionAttributeValues={
                        ':model_name': model_name
                    },
                    ScanIndexForward=False,  # Sort descending
                    Limit=1
                )
                
                if response['Items']:
                    return {
                        'status': 'success',
                        'model_version': response['Items'][0]
                    }
                else:
                    return {
                        'status': 'not_found',
                        'message': f'No versions found for model {model_name}'
                    }
                    
        except ClientError as e:
            return {
                'status': 'error',
                'error': str(e),
                'error_code': e.response['Error']['Code']
            }
    
    def list_model_versions(
        self,
        model_name: str,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        List all versions of a model
        
        Args:
            model_name: Name of the model
            limit: Maximum number of versions to return
            
        Returns:
            Dictionary with list of model versions
        """
        if not self.registry_table:
            raise RuntimeError("DynamoDB not available - cannot list model versions")
        
        try:
            response = self.registry_table.query(
                KeyConditionExpression='model_name = :model_name',
                ExpressionAttributeValues={
                    ':model_name': model_name
                },
                ScanIndexForward=False,  # Sort descending
                Limit=limit
            )
            
            return {
                'status': 'success',
                'model_name': model_name,
                'versions': response['Items'],
                'count': len(response['Items'])
            }
            
        except ClientError as e:
            return {
                'status': 'error',
                'error': str(e),
                'error_code': e.response['Error']['Code']
            }
    
    def create_retraining_trigger(
        self,
        trigger: RetrainingTrigger
    ) -> Dict[str, Any]:
        """
        Create an automated retraining trigger
        
        Args:
            trigger: RetrainingTrigger configuration
            
        Returns:
            Dictionary with trigger creation result
        """
        # Store trigger
        self.retraining_triggers[trigger.trigger_id] = trigger
        
        return {
            'status': 'success',
            'trigger_id': trigger.trigger_id,
            'message': 'Retraining trigger created successfully'
        }
    
    def check_retraining_triggers(
        self,
        model_type: ModelType,
        current_metrics: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Check if any retraining triggers should fire
        
        Args:
            model_type: Type of model to check
            current_metrics: Current model performance metrics
            
        Returns:
            Dictionary with trigger check results
        """
        triggered = []
        
        for trigger_id, trigger in self.retraining_triggers.items():
            if not trigger.enabled or trigger.model_type != model_type:
                continue
            
            if trigger.trigger_type == 'accuracy_degradation':
                # Check if accuracy has fallen below threshold
                accuracy = current_metrics.get('accuracy', 1.0)
                if trigger.threshold and accuracy < trigger.threshold:
                    triggered.append({
                        'trigger_id': trigger_id,
                        'trigger_type': trigger.trigger_type,
                        'reason': f'Accuracy {accuracy:.2f} below threshold {trigger.threshold:.2f}',
                        'current_metrics': current_metrics
                    })
        
        return {
            'status': 'success',
            'model_type': model_type.value,
            'triggered_count': len(triggered),
            'triggered': triggered
        }
    
    def trigger_retraining(
        self,
        model_type: ModelType,
        reason: str,
        training_config: TrainingJobConfig
    ) -> Dict[str, Any]:
        """
        Trigger model retraining
        
        Args:
            model_type: Type of model to retrain
            reason: Reason for retraining
            training_config: Training job configuration
            
        Returns:
            Dictionary with retraining job details
        """
        # Create training job
        result = self.create_training_job(training_config)
        
        if result['status'] == 'success':
            # Log retraining event
            retraining_event = {
                'model_type': model_type.value,
                'reason': reason,
                'training_job_name': training_config.job_name,
                'training_job_arn': result['training_job_arn'],
                'triggered_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Store retraining event in S3
            self._store_retraining_event(retraining_event)
            
            return {
                'status': 'success',
                'message': 'Retraining triggered successfully',
                'training_job_arn': result['training_job_arn'],
                'retraining_event': retraining_event
            }
        else:
            return result
    
    def _store_retraining_event(self, event: Dict[str, Any]):
        """
        Store retraining event in S3
        
        Args:
            event: Retraining event data
        """
        if not self.s3_client:
            return
        
        try:
            timestamp = datetime.now(timezone.utc)
            s3_key = f"retraining-events/{timestamp.strftime('%Y/%m/%d')}/{timestamp.strftime('%H%M%S')}-event.json"
            
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=s3_key,
                Body=json.dumps(event, indent=2),
                ContentType='application/json'
            )
        except ClientError as e:
            print(f"Failed to store retraining event: {str(e)}")


def create_demand_forecast_training_config(
    job_name: str,
    role_arn: str,
    training_data_s3_path: str,
    output_s3_path: str,
    instance_type: str = "ml.m5.xlarge",
    instance_count: int = 1
) -> TrainingJobConfig:
    """
    Create training configuration for demand forecast model
    
    Args:
        job_name: Name for the training job
        role_arn: IAM role ARN for SageMaker
        training_data_s3_path: S3 path to training data
        output_s3_path: S3 path for model output
        instance_type: EC2 instance type for training
        instance_count: Number of instances
        
    Returns:
        TrainingJobConfig object
    """
    return TrainingJobConfig(
        job_name=job_name,
        model_type=ModelType.DEMAND_FORECAST,
        algorithm_specification={
            'TrainingImage': 'forecasting-deepar:1',  # DeepAR algorithm
            'TrainingInputMode': 'File'
        },
        role_arn=role_arn,
        input_data_config=[
            {
                'ChannelName': 'train',
                'DataSource': {
                    'S3DataSource': {
                        'S3DataType': 'S3Prefix',
                        'S3Uri': training_data_s3_path,
                        'S3DataDistributionType': 'FullyReplicated'
                    }
                },
                'ContentType': 'application/json',
                'CompressionType': 'None'
            }
        ],
        output_data_config={
            'S3OutputPath': output_s3_path
        },
        resource_config={
            'InstanceType': instance_type,
            'InstanceCount': instance_count,
            'VolumeSizeInGB': 30
        },
        hyperparameters={
            'time_freq': '1D',
            'epochs': '100',
            'early_stopping_patience': '10',
            'mini_batch_size': '128',
            'learning_rate': '0.001',
            'context_length': '30',
            'prediction_length': '30'
        },
        stopping_condition={
            'MaxRuntimeInSeconds': 86400  # 24 hours
        },
        tags=[
            {'Key': 'Project', 'Value': 'RetailMind-AI'},
            {'Key': 'ModelType', 'Value': 'DemandForecast'}
        ]
    )
