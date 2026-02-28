"""
Configuration Management
Loads and manages application configuration from environment variables
"""
import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Application configuration"""
    
    # AWS Configuration
    AWS_REGION: str = os.getenv('AWS_REGION', 'us-east-1')
    AWS_ACCOUNT_ID: str = os.getenv('AWS_ACCOUNT_ID', '')
    
    # S3 Configuration
    S3_RAW_DATA_BUCKET: str = os.getenv('S3_RAW_DATA_BUCKET', 'retailmind-raw-data')
    S3_ML_ARTIFACTS_BUCKET: str = os.getenv('S3_ML_ARTIFACTS_BUCKET', 'retailmind-ml-artifacts')
    
    # DynamoDB Configuration
    DYNAMODB_TRANSACTIONS_TABLE: str = os.getenv('DYNAMODB_TRANSACTIONS_TABLE', 'retailmind-transactions')
    DYNAMODB_AGENT_STATES_TABLE: str = os.getenv('DYNAMODB_AGENT_STATES_TABLE', 'retailmind-agent-states')
    DYNAMODB_WORKFLOW_INSTANCES_TABLE: str = os.getenv('DYNAMODB_WORKFLOW_INSTANCES_TABLE', 'retailmind-workflow-instances')
    DYNAMODB_AUDIT_TRAIL_TABLE: str = os.getenv('DYNAMODB_AUDIT_TRAIL_TABLE', 'retailmind-audit-trail')
    
    # Redshift Configuration
    REDSHIFT_CLUSTER_IDENTIFIER: str = os.getenv('REDSHIFT_CLUSTER_IDENTIFIER', 'retailmind-analytics')
    REDSHIFT_DATABASE: str = os.getenv('REDSHIFT_DATABASE', 'retailmind_warehouse')
    REDSHIFT_USER: str = os.getenv('REDSHIFT_USER', 'admin')
    
    # EventBridge Configuration
    EVENTBRIDGE_BUS_NAME: str = os.getenv('EVENTBRIDGE_BUS_NAME', 'retailmind-event-bus')
    
    # API Configuration
    API_GATEWAY_STAGE: str = os.getenv('API_GATEWAY_STAGE', 'dev')
    COGNITO_USER_POOL_ID: str = os.getenv('COGNITO_USER_POOL_ID', '')
    
    # CloudWatch Configuration
    CLOUDWATCH_LOG_GROUP: str = os.getenv('CLOUDWATCH_LOG_GROUP', '/aws/retailmind')
    
    # Agent Configuration
    AGENT_CONFIDENCE_THRESHOLD: float = float(os.getenv('AGENT_CONFIDENCE_THRESHOLD', '0.8'))
    AGENT_TIMEOUT_SECONDS: int = int(os.getenv('AGENT_TIMEOUT_SECONDS', '30'))
    
    # Business Copilot Configuration
    COPILOT_RESPONSE_TIMEOUT: int = int(os.getenv('COPILOT_RESPONSE_TIMEOUT', '10'))
    
    # Forecast Configuration
    FORECAST_ACCURACY_TARGET: float = float(os.getenv('FORECAST_ACCURACY_TARGET', '0.85'))
    FORECAST_PERIOD_DAYS: int = int(os.getenv('FORECAST_PERIOD_DAYS', '30'))
    
    # Document Processing Configuration
    DOCUMENT_EXTRACTION_ACCURACY_TARGET: float = float(os.getenv('DOCUMENT_EXTRACTION_ACCURACY_TARGET', '0.95'))


config = Config()
