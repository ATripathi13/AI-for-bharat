"""
AWS Service Client Configuration
Provides centralized AWS service client initialization
"""
import os
import boto3
from typing import Optional


class AWSClients:
    """Singleton class for AWS service clients"""
    
    _instance: Optional['AWSClients'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize_clients()
        return cls._instance
    
    def _initialize_clients(self):
        """Initialize all AWS service clients"""
        self.region = os.getenv('AWS_REGION', 'us-east-1')
        
        # S3 Client
        self.s3 = boto3.client('s3', region_name=self.region)
        
        # DynamoDB Client and Resource
        self.dynamodb_client = boto3.client('dynamodb', region_name=self.region)
        self.dynamodb_resource = boto3.resource('dynamodb', region_name=self.region)
        
        # Lambda Client
        self.lambda_client = boto3.client('lambda', region_name=self.region)
        
        # Step Functions Client
        self.stepfunctions = boto3.client('stepfunctions', region_name=self.region)
        
        # EventBridge Client
        self.events = boto3.client('events', region_name=self.region)
        
        # SageMaker Client
        self.sagemaker = boto3.client('sagemaker', region_name=self.region)
        self.sagemaker_runtime = boto3.client('sagemaker-runtime', region_name=self.region)
        
        # Bedrock Client
        self.bedrock = boto3.client('bedrock-runtime', region_name=self.region)
        
        # Textract Client
        self.textract = boto3.client('textract', region_name=self.region)
        
        # OpenSearch Client
        self.opensearch = boto3.client('opensearch', region_name=self.region)
        
        # CloudWatch Client
        self.cloudwatch = boto3.client('cloudwatch', region_name=self.region)
        self.logs = boto3.client('logs', region_name=self.region)
        
        # Cognito Client
        self.cognito = boto3.client('cognito-idp', region_name=self.region)
        
        # API Gateway Client
        self.apigateway = boto3.client('apigateway', region_name=self.region)
    
    def get_dynamodb_table(self, table_name: str):
        """Get DynamoDB table resource"""
        return self.dynamodb_resource.Table(table_name)


# Global instance
aws_clients = AWSClients()
