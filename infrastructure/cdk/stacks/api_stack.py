"""
API Stack - API Gateway and Cognito
"""
from aws_cdk import (
    Stack,
    aws_apigateway as apigw,
    aws_cognito as cognito,
    RemovalPolicy
)
from constructs import Construct


class ApiStack(Stack):
    """Stack for API Gateway and authentication"""

    def __init__(self, scope: Construct, construct_id: str, compute_stack, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.compute_stack = compute_stack

        # Cognito User Pool
        self.user_pool = cognito.UserPool(
            self,
            "RetailMindUserPool",
            user_pool_name="retailmind-users",
            self_sign_up_enabled=True,
            sign_in_aliases=cognito.SignInAliases(
                email=True,
                username=True
            ),
            auto_verify=cognito.AutoVerifiedAttrs(email=True),
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=True
            ),
            removal_policy=RemovalPolicy.RETAIN
        )

        # Cognito User Pool Client
        self.user_pool_client = self.user_pool.add_client(
            "RetailMindUserPoolClient",
            auth_flows=cognito.AuthFlow(
                user_password=True,
                user_srp=True
            )
        )

        # API Gateway REST API
        self.api = apigw.RestApi(
            self,
            "RetailMindApi",
            rest_api_name="retailmind-api",
            description="RetailMind AI REST API",
            deploy_options=apigw.StageOptions(
                stage_name="dev",
                throttling_rate_limit=1000,
                throttling_burst_limit=2000
            )
        )

        # Cognito Authorizer
        self.authorizer = apigw.CognitoUserPoolsAuthorizer(
            self,
            "ApiAuthorizer",
            cognito_user_pools=[self.user_pool]
        )
