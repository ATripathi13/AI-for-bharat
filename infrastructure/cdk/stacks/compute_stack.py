"""
Compute Stack - Lambda, Step Functions, EventBridge, SageMaker
"""
from aws_cdk import (
    Stack,
    aws_lambda as lambda_,
    aws_stepfunctions as sfn,
    aws_events as events,
    aws_iam as iam,
    Duration
)
from constructs import Construct


class ComputeStack(Stack):
    """Stack for compute and orchestration layer"""

    def __init__(self, scope: Construct, construct_id: str, data_stack, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.data_stack = data_stack

        # EventBridge Event Bus for Agent Communication
        self.event_bus = events.EventBus(
            self,
            "AgentEventBus",
            event_bus_name="retailmind-event-bus"
        )

        # Lambda Execution Role
        self.lambda_role = iam.Role(
            self,
            "LambdaExecutionRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                )
            ]
        )

        # Grant permissions to access data layer
        data_stack.transactions_table.grant_read_write_data(self.lambda_role)
        data_stack.agent_states_table.grant_read_write_data(self.lambda_role)
        data_stack.workflow_instances_table.grant_read_write_data(self.lambda_role)
        data_stack.audit_trail_table.grant_read_write_data(self.lambda_role)
        data_stack.raw_data_bucket.grant_read_write(self.lambda_role)
        data_stack.ml_artifacts_bucket.grant_read_write(self.lambda_role)

        # Grant EventBridge permissions
        self.event_bus.grant_put_events_to(self.lambda_role)

        # Step Functions State Machine Role
        self.sfn_role = iam.Role(
            self,
            "StepFunctionsRole",
            assumed_by=iam.ServicePrincipal("states.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaRole"
                )
            ]
        )

        # Grant Step Functions access to invoke Lambda
        self.lambda_role.grant_pass_role(self.sfn_role)

        # Stack Outputs
        from aws_cdk import CfnOutput
        
        CfnOutput(
            self,
            "EventBusName",
            value=self.event_bus.event_bus_name,
            description="EventBridge event bus for agent communication",
            export_name="RetailMindEventBus"
        )
        
        CfnOutput(
            self,
            "LambdaRoleArn",
            value=self.lambda_role.role_arn,
            description="Lambda execution role ARN",
            export_name="RetailMindLambdaRoleArn"
        )
