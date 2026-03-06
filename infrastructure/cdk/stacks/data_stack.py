"""
Data Stack - S3, DynamoDB, and Redshift configuration
"""
from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_dynamodb as dynamodb,
    RemovalPolicy,
    Duration
)
from constructs import Construct


class DataStack(Stack):
    """Stack for data storage layer"""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Get account ID from stack
        account_id = Stack.of(self).account
        
        # S3 Buckets (with account ID for global uniqueness)
        self.raw_data_bucket = s3.Bucket(
            self,
            "RawDataBucket",
            bucket_name=f"retailmind-raw-data-{account_id}",
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            removal_policy=RemovalPolicy.RETAIN,
            lifecycle_rules=[
                s3.LifecycleRule(
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.INTELLIGENT_TIERING,
                            transition_after=Duration.days(30)
                        )
                    ]
                )
            ]
        )

        self.ml_artifacts_bucket = s3.Bucket(
            self,
            "MLArtifactsBucket",
            bucket_name=f"retailmind-ml-artifacts-{account_id}",
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            removal_policy=RemovalPolicy.RETAIN
        )

        # DynamoDB Tables
        self.transactions_table = dynamodb.Table(
            self,
            "TransactionsTable",
            table_name="retailmind-transactions",
            partition_key=dynamodb.Attribute(
                name="transactionId",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            point_in_time_recovery=True,
            removal_policy=RemovalPolicy.RETAIN
        )

        self.agent_states_table = dynamodb.Table(
            self,
            "AgentStatesTable",
            table_name="retailmind-agent-states",
            partition_key=dynamodb.Attribute(
                name="agentId",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="stateTimestamp",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            point_in_time_recovery=True,
            removal_policy=RemovalPolicy.RETAIN
        )

        self.workflow_instances_table = dynamodb.Table(
            self,
            "WorkflowInstancesTable",
            table_name="retailmind-workflow-instances",
            partition_key=dynamodb.Attribute(
                name="workflowId",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="instanceId",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            point_in_time_recovery=True,
            removal_policy=RemovalPolicy.RETAIN
        )

        self.audit_trail_table = dynamodb.Table(
            self,
            "AuditTrailTable",
            table_name="retailmind-audit-trail",
            partition_key=dynamodb.Attribute(
                name="eventId",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            point_in_time_recovery=True,
            removal_policy=RemovalPolicy.RETAIN
        )

        # Stack Outputs
        from aws_cdk import CfnOutput
        
        CfnOutput(
            self,
            "RawDataBucketName",
            value=self.raw_data_bucket.bucket_name,
            description="S3 bucket for raw data",
            export_name="RetailMindRawDataBucket"
        )
        
        CfnOutput(
            self,
            "MLArtifactsBucketName",
            value=self.ml_artifacts_bucket.bucket_name,
            description="S3 bucket for ML artifacts",
            export_name="RetailMindMLArtifactsBucket"
        )
        
        CfnOutput(
            self,
            "TransactionsTableName",
            value=self.transactions_table.table_name,
            description="DynamoDB transactions table",
            export_name="RetailMindTransactionsTable"
        )
        
        CfnOutput(
            self,
            "AgentStatesTableName",
            value=self.agent_states_table.table_name,
            description="DynamoDB agent states table",
            export_name="RetailMindAgentStatesTable"
        )
