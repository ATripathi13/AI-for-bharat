"""
DynamoDB table schemas for RetailMind AI
"""
from aws_cdk import (
    aws_dynamodb as dynamodb,
    RemovalPolicy
)
from constructs import Construct


class DynamoDBSchemas:
    """DynamoDB table schema definitions"""

    @staticmethod
    def create_agent_decisions_table(scope: Construct, table_name: str = "AgentDecisions") -> dynamodb.Table:
        """
        Create DynamoDB table for agent decisions
        
        Primary Key: agentId (partition key) + decisionId (sort key)
        GSI: timestamp-index for time-based queries
        """
        table = dynamodb.Table(
            scope,
            "AgentDecisionsTable",
            table_name=table_name,
            partition_key=dynamodb.Attribute(
                name="agentId",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="decisionId",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.RETAIN,
            point_in_time_recovery=True,
            encryption=dynamodb.TableEncryption.AWS_MANAGED
        )

        # GSI for querying by timestamp
        table.add_global_secondary_index(
            index_name="timestamp-index",
            partition_key=dynamodb.Attribute(
                name="agentId",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL
        )

        # GSI for escalation queries
        table.add_global_secondary_index(
            index_name="escalation-index",
            partition_key=dynamodb.Attribute(
                name="escalationRequired",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL
        )

        return table

    @staticmethod
    def create_workflow_instances_table(scope: Construct, table_name: str = "WorkflowInstances") -> dynamodb.Table:
        """
        Create DynamoDB table for workflow instances
        
        Primary Key: workflowId (partition key) + instanceId (sort key)
        GSI: status-index for querying by workflow status
        """
        table = dynamodb.Table(
            scope,
            "WorkflowInstancesTable",
            table_name=table_name,
            partition_key=dynamodb.Attribute(
                name="workflowId",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="instanceId",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.RETAIN,
            point_in_time_recovery=True,
            encryption=dynamodb.TableEncryption.AWS_MANAGED
        )

        # GSI for querying by status
        table.add_global_secondary_index(
            index_name="status-index",
            partition_key=dynamodb.Attribute(
                name="status",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="instanceId",
                type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL
        )

        # GSI for querying by creator
        table.add_global_secondary_index(
            index_name="creator-index",
            partition_key=dynamodb.Attribute(
                name="createdBy",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="instanceId",
                type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL
        )

        return table

    @staticmethod
    def create_business_intelligence_table(scope: Construct, table_name: str = "BusinessIntelligence") -> dynamodb.Table:
        """
        Create DynamoDB table for business intelligence
        
        Primary Key: entityType (partition key) + entityId (sort key)
        GSI: confidence-index for querying high-confidence insights
        """
        table = dynamodb.Table(
            scope,
            "BusinessIntelligenceTable",
            table_name=table_name,
            partition_key=dynamodb.Attribute(
                name="entityType",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="entityId",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.RETAIN,
            point_in_time_recovery=True,
            encryption=dynamodb.TableEncryption.AWS_MANAGED
        )

        # GSI for querying by confidence level
        table.add_global_secondary_index(
            index_name="confidence-index",
            partition_key=dynamodb.Attribute(
                name="entityType",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="confidence",
                type=dynamodb.AttributeType.NUMBER
            ),
            projection_type=dynamodb.ProjectionType.ALL
        )

        return table

    @staticmethod
    def create_agent_states_table(scope: Construct, table_name: str = "AgentStates") -> dynamodb.Table:
        """
        Create DynamoDB table for agent states
        
        Primary Key: agentId (partition key) + timestamp (sort key)
        Stores current state and configuration of each agent
        """
        table = dynamodb.Table(
            scope,
            "AgentStatesTable",
            table_name=table_name,
            partition_key=dynamodb.Attribute(
                name="agentId",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.RETAIN,
            point_in_time_recovery=True,
            encryption=dynamodb.TableEncryption.AWS_MANAGED,
            time_to_live_attribute="ttl"
        )

        return table

    @staticmethod
    def create_transactions_table(scope: Construct, table_name: str = "Transactions") -> dynamodb.Table:
        """
        Create DynamoDB table for transactions
        
        Primary Key: transactionId (partition key) + timestamp (sort key)
        GSI: userId-index for user transaction history
        """
        table = dynamodb.Table(
            scope,
            "TransactionsTable",
            table_name=table_name,
            partition_key=dynamodb.Attribute(
                name="transactionId",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.RETAIN,
            point_in_time_recovery=True,
            encryption=dynamodb.TableEncryption.AWS_MANAGED
        )

        # GSI for querying by user
        table.add_global_secondary_index(
            index_name="userId-index",
            partition_key=dynamodb.Attribute(
                name="userId",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL
        )

        # GSI for querying by transaction type
        table.add_global_secondary_index(
            index_name="type-index",
            partition_key=dynamodb.Attribute(
                name="transactionType",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL
        )

        return table
