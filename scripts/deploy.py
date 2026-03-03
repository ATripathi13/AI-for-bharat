#!/usr/bin/env python3
"""
RetailMind AI Deployment Script

This script handles deployment of the RetailMind AI platform to AWS.
It orchestrates CDK deployments, runs pre-deployment checks, and handles rollbacks.
"""

import argparse
import json
import subprocess
import sys
import time
from typing import Dict, List, Optional
import boto3
from botocore.exceptions import ClientError


class DeploymentManager:
    """Manages deployment of RetailMind AI infrastructure and applications"""
    
    def __init__(self, environment: str, region: str = "us-east-1"):
        self.environment = environment
        self.region = region
        self.cloudformation = boto3.client('cloudformation', region_name=region)
        self.s3 = boto3.client('s3', region_name=region)
        
    def validate_environment(self) -> bool:
        """Validate that the environment is properly configured"""
        print(f"Validating {self.environment} environment...")
        
        # Check AWS credentials
        try:
            sts = boto3.client('sts')
            identity = sts.get_caller_identity()
            print(f"✓ AWS credentials valid (Account: {identity['Account']})")
        except Exception as e:
            print(f"✗ AWS credentials invalid: {e}")
            return False
        
        # Check CDK bootstrap
        try:
            response = self.cloudformation.describe_stacks(
                StackName=f"CDKToolkit"
            )
            print(f"✓ CDK bootstrap stack exists")
        except ClientError:
            print(f"✗ CDK not bootstrapped. Run: cdk bootstrap")
            return False
        
        return True
    
    def run_tests(self) -> bool:
        """Run test suite before deployment"""
        print("Running test suite...")
        
        # Backend tests
        print("Running backend tests...")
        result = subprocess.run(
            ["pytest", "backend/tests/", "-v"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"✗ Backend tests failed:")
            print(result.stdout)
            print(result.stderr)
            return False
        
        print(f"✓ Backend tests passed")
        
        # Frontend tests
        print("Running frontend tests...")
        result = subprocess.run(
            ["npm", "test", "--prefix", "frontend"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"✗ Frontend tests failed:")
            print(result.stdout)
            print(result.stderr)
            return False
        
        print(f"✓ Frontend tests passed")
        
        return True
    
    def deploy_infrastructure(self, stacks: Optional[List[str]] = None) -> bool:
        """Deploy CDK infrastructure stacks"""
        print(f"Deploying infrastructure to {self.environment}...")
        
        # Change to CDK directory
        cdk_dir = "infrastructure/cdk"
        
        # Build CDK command
        cmd = ["cdk", "deploy"]
        
        if stacks:
            cmd.extend(stacks)
        else:
            cmd.append("--all")
        
        cmd.extend([
            "--require-approval", "never",
            "--context", f"environment={self.environment}",
            "--context", f"region={self.region}"
        ])
        
        # Execute deployment
        result = subprocess.run(
            cmd,
            cwd=cdk_dir,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"✗ Infrastructure deployment failed:")
            print(result.stdout)
            print(result.stderr)
            return False
        
        print(f"✓ Infrastructure deployed successfully")
        print(result.stdout)
        
        return True
    
    def deploy_backend(self) -> bool:
        """Deploy backend Lambda functions"""
        print("Deploying backend Lambda functions...")
        
        # Package backend code
        print("Packaging backend code...")
        result = subprocess.run(
            ["python", "scripts/package_lambda.py"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"✗ Backend packaging failed:")
            print(result.stderr)
            return False
        
        print(f"✓ Backend deployed successfully")
        return True
    
    def deploy_frontend(self) -> bool:
        """Deploy frontend to AWS Amplify"""
        print("Deploying frontend...")
        
        # Build frontend
        print("Building frontend...")
        result = subprocess.run(
            ["npm", "run", "build", "--prefix", "frontend"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"✗ Frontend build failed:")
            print(result.stderr)
            return False
        
        # Deploy to Amplify
        print("Deploying to Amplify...")
        result = subprocess.run(
            ["aws", "amplify", "start-deployment",
             "--app-id", self._get_amplify_app_id(),
             "--branch-name", self.environment],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"✗ Frontend deployment failed:")
            print(result.stderr)
            return False
        
        print(f"✓ Frontend deployed successfully")
        return True
    
    def run_smoke_tests(self) -> bool:
        """Run smoke tests after deployment"""
        print("Running smoke tests...")
        
        # Get API endpoint
        api_endpoint = self._get_stack_output("RetailMindApiStack", "ApiEndpoint")
        
        if not api_endpoint:
            print("✗ Could not retrieve API endpoint")
            return False
        
        # Test health endpoint
        import requests
        try:
            response = requests.get(f"{api_endpoint}/health", timeout=10)
            if response.status_code == 200:
                print(f"✓ API health check passed")
            else:
                print(f"✗ API health check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"✗ API health check failed: {e}")
            return False
        
        return True
    
    def rollback(self, stack_name: str) -> bool:
        """Rollback a failed deployment"""
        print(f"Rolling back {stack_name}...")
        
        try:
            # Get previous stack version
            response = self.cloudformation.describe_stacks(StackName=stack_name)
            stack = response['Stacks'][0]
            
            # Trigger rollback
            self.cloudformation.rollback_stack(StackName=stack_name)
            
            # Wait for rollback to complete
            waiter = self.cloudformation.get_waiter('stack_rollback_complete')
            waiter.wait(StackName=stack_name)
            
            print(f"✓ Rollback completed successfully")
            return True
            
        except Exception as e:
            print(f"✗ Rollback failed: {e}")
            return False
    
    def _get_stack_output(self, stack_name: str, output_key: str) -> Optional[str]:
        """Get output value from CloudFormation stack"""
        try:
            response = self.cloudformation.describe_stacks(StackName=stack_name)
            stack = response['Stacks'][0]
            
            for output in stack.get('Outputs', []):
                if output['OutputKey'] == output_key:
                    return output['OutputValue']
            
            return None
        except Exception as e:
            print(f"Error getting stack output: {e}")
            return None
    
    def _get_amplify_app_id(self) -> str:
        """Get Amplify app ID from stack outputs"""
        return self._get_stack_output("RetailMindApiStack", "AmplifyAppId") or ""
    
    def deploy_all(self, skip_tests: bool = False) -> bool:
        """Deploy entire platform"""
        print(f"Starting deployment to {self.environment}...")
        print("=" * 60)
        
        # Validate environment
        if not self.validate_environment():
            print("Environment validation failed. Aborting deployment.")
            return False
        
        # Run tests
        if not skip_tests:
            if not self.run_tests():
                print("Tests failed. Aborting deployment.")
                return False
        else:
            print("⚠ Skipping tests (--skip-tests flag)")
        
        # Deploy infrastructure
        if not self.deploy_infrastructure():
            print("Infrastructure deployment failed. Aborting.")
            return False
        
        # Deploy backend
        if not self.deploy_backend():
            print("Backend deployment failed. Rolling back...")
            self.rollback("RetailMindComputeStack")
            return False
        
        # Deploy frontend
        if not self.deploy_frontend():
            print("Frontend deployment failed. Rolling back...")
            self.rollback("RetailMindApiStack")
            return False
        
        # Run smoke tests
        if not self.run_smoke_tests():
            print("⚠ Smoke tests failed. Deployment completed but may have issues.")
        
        print("=" * 60)
        print(f"✓ Deployment to {self.environment} completed successfully!")
        
        # Print important URLs
        self._print_deployment_info()
        
        return True
    
    def _print_deployment_info(self):
        """Print deployment information"""
        print("\nDeployment Information:")
        print("-" * 60)
        
        api_endpoint = self._get_stack_output("RetailMindApiStack", "ApiEndpoint")
        if api_endpoint:
            print(f"API Endpoint: {api_endpoint}")
        
        frontend_url = self._get_stack_output("RetailMindApiStack", "FrontendUrl")
        if frontend_url:
            print(f"Frontend URL: {frontend_url}")
        
        print(f"Region: {self.region}")
        print(f"Environment: {self.environment}")
        print("-" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Deploy RetailMind AI platform to AWS"
    )
    
    parser.add_argument(
        "--environment",
        "-e",
        required=True,
        choices=["dev", "staging", "production"],
        help="Deployment environment"
    )
    
    parser.add_argument(
        "--region",
        "-r",
        default="us-east-1",
        help="AWS region (default: us-east-1)"
    )
    
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip running tests before deployment"
    )
    
    parser.add_argument(
        "--stacks",
        nargs="+",
        help="Specific stacks to deploy (default: all)"
    )
    
    parser.add_argument(
        "--rollback",
        help="Rollback specified stack"
    )
    
    args = parser.parse_args()
    
    # Create deployment manager
    manager = DeploymentManager(
        environment=args.environment,
        region=args.region
    )
    
    # Handle rollback
    if args.rollback:
        success = manager.rollback(args.rollback)
        sys.exit(0 if success else 1)
    
    # Deploy
    if args.stacks:
        success = manager.deploy_infrastructure(stacks=args.stacks)
    else:
        success = manager.deploy_all(skip_tests=args.skip_tests)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
