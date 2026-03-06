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

        # Cognito Authorizer (attached to the REST API)
        self.authorizer = apigw.CognitoUserPoolsAuthorizer(
            self,
            "ApiAuthorizer",
            cognito_user_pools=[self.user_pool]
        )
        
        # Create a sample health check endpoint
        health_resource = self.api.root.add_resource("health")
        health_resource.add_method(
            "GET",
            apigw.MockIntegration(
                integration_responses=[
                    apigw.IntegrationResponse(
                        status_code="200",
                        response_templates={
                            "application/json": '{"status": "healthy", "timestamp": "$context.requestTime"}'
                        }
                    )
                ],
                request_templates={
                    "application/json": '{"statusCode": 200}'
                }
            ),
            method_responses=[
                apigw.MethodResponse(status_code="200")
            ]
        )
        
        # Create agents resource (protected by Cognito)
        agents_resource = self.api.root.add_resource("agents")
        agents_resource.add_method(
            "GET",
            apigw.MockIntegration(
                integration_responses=[
                    apigw.IntegrationResponse(
                        status_code="200",
                        response_templates={
                            "application/json": '{"message": "Agents endpoint - requires authentication"}'
                        }
                    )
                ],
                request_templates={
                    "application/json": '{"statusCode": 200}'
                }
            ),
            method_responses=[
                apigw.MethodResponse(status_code="200")
            ],
            authorizer=self.authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO
        )

        # Stack Outputs
        from aws_cdk import CfnOutput
        
        CfnOutput(
            self,
            "ApiEndpoint",
            value=self.api.url,
            description="API Gateway endpoint URL",
            export_name="RetailMindApiEndpoint"
        )
        
        CfnOutput(
            self,
            "UserPoolId",
            value=self.user_pool.user_pool_id,
            description="Cognito User Pool ID",
            export_name="RetailMindUserPoolId"
        )
        
        CfnOutput(
            self,
            "UserPoolClientId",
            value=self.user_pool_client.user_pool_client_id,
            description="Cognito User Pool Client ID",
            export_name="RetailMindUserPoolClientId"
        )
        
        CfnOutput(
            self,
            "ApiId",
            value=self.api.rest_api_id,
            description="API Gateway REST API ID",
            export_name="RetailMindApiId"
        )
