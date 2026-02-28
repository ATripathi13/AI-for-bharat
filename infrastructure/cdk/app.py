#!/usr/bin/env python3
"""
RetailMind AI - AWS CDK Application Entry Point
"""
import os
from aws_cdk import App, Environment
from stacks.data_stack import DataStack
from stacks.compute_stack import ComputeStack
from stacks.api_stack import ApiStack
from stacks.monitoring_stack import MonitoringStack

app = App()

# Environment configuration
env = Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
    region=os.environ.get("CDK_DEFAULT_REGION", "us-east-1")
)

# Data Layer Stack
data_stack = DataStack(
    app,
    "RetailMindDataStack",
    env=env,
    description="Data storage layer with S3, DynamoDB, and Redshift"
)

# Compute Layer Stack
compute_stack = ComputeStack(
    app,
    "RetailMindComputeStack",
    env=env,
    data_stack=data_stack,
    description="Compute layer with Lambda, Step Functions, and SageMaker"
)

# API Layer Stack
api_stack = ApiStack(
    app,
    "RetailMindApiStack",
    env=env,
    compute_stack=compute_stack,
    description="API Gateway and Cognito authentication"
)

# Monitoring Layer Stack
monitoring_stack = MonitoringStack(
    app,
    "RetailMindMonitoringStack",
    env=env,
    description="CloudWatch monitoring and audit trails"
)

app.synth()
