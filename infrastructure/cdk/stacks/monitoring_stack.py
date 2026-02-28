"""
Monitoring Stack - CloudWatch Logs and Metrics
"""
from aws_cdk import (
    Stack,
    aws_logs as logs,
    aws_cloudwatch as cloudwatch,
    RemovalPolicy
)
from constructs import Construct


class MonitoringStack(Stack):
    """Stack for monitoring and observability"""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # CloudWatch Log Group
        self.log_group = logs.LogGroup(
            self,
            "RetailMindLogGroup",
            log_group_name="/aws/retailmind",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.RETAIN
        )

        # CloudWatch Dashboard
        self.dashboard = cloudwatch.Dashboard(
            self,
            "RetailMindDashboard",
            dashboard_name="retailmind-system-health"
        )
