#!/usr/bin/env python3
"""
Rollback Script for RetailMind AI

Handles rollback of failed deployments to previous stable versions.
"""

import argparse
import json
import sys
from datetime import datetime
from typing import Dict, List, Optional
import boto3
from botocore.exceptions import ClientError


class RollbackManager:
    """Manages rollback of deployments"""
    
    def __init__(self, environment: str, region: str = "us-east-1"):
        self.environment = environment
        self.region = region
        self.cloudformation = boto3.client('cloudformation', region_name=region)
        self.s3 = boto3.client('s3', region_name=region)
        self.dynamodb = boto3.client('dynamodb', region_name=region)
    
    def list_deployments(self, stack_name: str, limit: int = 10) -> List[Dict]:
        """List recent deployments for a stack"""
        print(f"Listing recent deployments for {stack_name}...")
        
        try:
            response = self.cloudformation.describe_stack_events(
                StackName=stack_name
            )
            
            deployments = []
            for event in response['StackEvents'][:limit]:
                if event['ResourceType'] == 'AWS::CloudFormation::Stack':
                    if event['ResourceStatus'] in ['UPDATE_COMPLETE', 'CREATE_COMPLETE']:
                        deployments.append({
                            'timestamp': event['Timestamp'],
                            'status': event['ResourceStatus'],
                            'eventId': event['EventId']
                        })
            
            return deployments
            
        except ClientError as e:
            print(f"Error listing deployments: {e}")
            return []
    
    def get_stack_template(self, stack_name: str) -> Optional[str]:
        """Get current stack template"""
        try:
            response = self.cloudformation.get_template(
                StackName=stack_name,
                TemplateStage='Original'
            )
            return response['TemplateBody']
        except ClientError as e:
            print(f"Error getting stack template: {e}")
            return None
    
    def backup_current_state(self, stack_name: str) -> bool:
        """Backup current stack state before rollback"""
        print(f"Backing up current state of {stack_name}...")
        
        try:
            # Get stack details
            response = self.cloudformation.describe_stacks(StackName=stack_name)
            stack = response['Stacks'][0]
            
            # Get template
            template = self.get_stack_template(stack_name)
            
            # Create backup
            backup = {
                'timestamp': datetime.now().isoformat(),
                'stack_name': stack_name,
                'stack_id': stack['StackId'],
                'status': stack['StackStatus'],
                'template': template,
                'parameters': stack.get('Parameters', []),
                'outputs': stack.get('Outputs', [])
            }
            
            # Save to S3
            backup_bucket = f"retailmind-backups-{self.environment}"
            backup_key = f"rollback-backups/{stack_name}/{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
            
            self.s3.put_object(
                Bucket=backup_bucket,
                Key=backup_key,
                Body=json.dumps(backup, indent=2, default=str)
            )
            
            print(f"✓ Backup saved to s3://{backup_bucket}/{backup_key}")
            return True
            
        except Exception as e:
            print(f"✗ Backup failed: {e}")
            return False
    
    def rollback_stack(self, stack_name: str, to_version: Optional[str] = None) -> bool:
        """Rollback a CloudFormation stack"""
        print(f"Rolling back {stack_name}...")
        
        # Backup current state
        if not self.backup_current_state(stack_name):
            print("⚠ Backup failed, but continuing with rollback...")
        
        try:
            # Check if stack is in a rollback-able state
            response = self.cloudformation.describe_stacks(StackName=stack_name)
            stack = response['Stacks'][0]
            status = stack['StackStatus']
            
            if status not in ['UPDATE_FAILED', 'UPDATE_ROLLBACK_FAILED', 'CREATE_FAILED']:
                print(f"Stack is in {status} state. Initiating rollback...")
            
            # Initiate rollback
            if to_version:
                # Rollback to specific version (requires template)
                print(f"Rolling back to version: {to_version}")
                # This would require storing versioned templates
                # For now, we'll use CloudFormation's built-in rollback
            
            # Use CloudFormation's rollback capability
            self.cloudformation.rollback_stack(StackName=stack_name)
            
            # Wait for rollback to complete
            print("Waiting for rollback to complete...")
            waiter = self.cloudformation.get_waiter('stack_rollback_complete')
            waiter.wait(
                StackName=stack_name,
                WaiterConfig={'Delay': 30, 'MaxAttempts': 60}
            )
            
            print(f"✓ Rollback completed successfully")
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            
            if error_code == 'ValidationError':
                print(f"✗ Cannot rollback: {e.response['Error']['Message']}")
                print("Stack may need manual intervention")
            else:
                print(f"✗ Rollback failed: {e}")
            
            return False
    
    def rollback_lambda_function(self, function_name: str, version: str) -> bool:
        """Rollback a Lambda function to a previous version"""
        print(f"Rolling back Lambda function {function_name} to version {version}...")
        
        try:
            lambda_client = boto3.client('lambda', region_name=self.region)
            
            # Update function to use previous version
            response = lambda_client.update_function_configuration(
                FunctionName=function_name,
                Publish=True
            )
            
            # Update alias to point to previous version
            lambda_client.update_alias(
                FunctionName=function_name,
                Name=self.environment,
                FunctionVersion=version
            )
            
            print(f"✓ Lambda function rolled back to version {version}")
            return True
            
        except ClientError as e:
            print(f"✗ Lambda rollback failed: {e}")
            return False
    
    def rollback_all(self) -> bool:
        """Rollback all stacks in the environment"""
        print(f"Rolling back all stacks in {self.environment}...")
        
        stacks = [
            "RetailMindDataStack",
            "RetailMindComputeStack",
            "RetailMindApiStack",
            "RetailMindMonitoringStack"
        ]
        
        success = True
        for stack in stacks:
            if not self.rollback_stack(stack):
                print(f"✗ Failed to rollback {stack}")
                success = False
            else:
                print(f"✓ Successfully rolled back {stack}")
        
        return success
    
    def verify_rollback(self, stack_name: str) -> bool:
        """Verify that rollback was successful"""
        print(f"Verifying rollback of {stack_name}...")
        
        try:
            response = self.cloudformation.describe_stacks(StackName=stack_name)
            stack = response['Stacks'][0]
            status = stack['StackStatus']
            
            if status in ['ROLLBACK_COMPLETE', 'UPDATE_ROLLBACK_COMPLETE']:
                print(f"✓ Rollback verified: {status}")
                return True
            else:
                print(f"✗ Unexpected status: {status}")
                return False
                
        except ClientError as e:
            print(f"✗ Verification failed: {e}")
            return False
    
    def restore_from_backup(self, backup_path: str) -> bool:
        """Restore stack from a backup"""
        print(f"Restoring from backup: {backup_path}")
        
        try:
            # Parse S3 path
            if backup_path.startswith('s3://'):
                parts = backup_path[5:].split('/', 1)
                bucket = parts[0]
                key = parts[1]
            else:
                print("Invalid backup path. Must be S3 URI (s3://bucket/key)")
                return False
            
            # Get backup
            response = self.s3.get_object(Bucket=bucket, Key=key)
            backup = json.loads(response['Body'].read())
            
            # Restore stack
            stack_name = backup['stack_name']
            template = backup['template']
            parameters = backup['parameters']
            
            print(f"Restoring {stack_name}...")
            
            self.cloudformation.update_stack(
                StackName=stack_name,
                TemplateBody=json.dumps(template) if isinstance(template, dict) else template,
                Parameters=parameters,
                Capabilities=['CAPABILITY_IAM', 'CAPABILITY_NAMED_IAM']
            )
            
            # Wait for update to complete
            waiter = self.cloudformation.get_waiter('stack_update_complete')
            waiter.wait(StackName=stack_name)
            
            print(f"✓ Restored from backup successfully")
            return True
            
        except Exception as e:
            print(f"✗ Restore failed: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(
        description="Rollback RetailMind AI deployments"
    )
    
    parser.add_argument(
        "--environment",
        "-e",
        required=True,
        choices=["dev", "staging", "production"],
        help="Environment to rollback"
    )
    
    parser.add_argument(
        "--region",
        "-r",
        default="us-east-1",
        help="AWS region"
    )
    
    parser.add_argument(
        "--stack",
        "-s",
        help="Specific stack to rollback"
    )
    
    parser.add_argument(
        "--all",
        action="store_true",
        help="Rollback all stacks"
    )
    
    parser.add_argument(
        "--list",
        action="store_true",
        help="List recent deployments"
    )
    
    parser.add_argument(
        "--restore",
        help="Restore from backup (S3 URI)"
    )
    
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify rollback status"
    )
    
    args = parser.parse_args()
    
    # Create rollback manager
    manager = RollbackManager(
        environment=args.environment,
        region=args.region
    )
    
    # Handle different operations
    if args.list:
        if not args.stack:
            print("Error: --stack required with --list")
            sys.exit(1)
        deployments = manager.list_deployments(args.stack)
        print(json.dumps(deployments, indent=2, default=str))
        sys.exit(0)
    
    if args.restore:
        success = manager.restore_from_backup(args.restore)
        sys.exit(0 if success else 1)
    
    if args.verify:
        if not args.stack:
            print("Error: --stack required with --verify")
            sys.exit(1)
        success = manager.verify_rollback(args.stack)
        sys.exit(0 if success else 1)
    
    # Perform rollback
    if args.all:
        success = manager.rollback_all()
    elif args.stack:
        success = manager.rollback_stack(args.stack)
    else:
        print("Error: Either --stack or --all required")
        sys.exit(1)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
