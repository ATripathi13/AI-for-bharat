"""
S3 bucket structure definitions for RetailMind AI
"""
from aws_cdk import (
    aws_s3 as s3,
    RemovalPolicy,
    Duration
)
from constructs import Construct


class S3BucketStructure:
    """S3 bucket structure definitions"""

    @staticmethod
    def create_raw_data_bucket(scope: Construct, bucket_name: str = "retailmind-raw-data") -> s3.Bucket:
        """
        Create S3 bucket for raw data ingestion
        
        Structure:
        /market-intelligence/
            /pricing/YYYY/MM/DD/
            /competitor-data/YYYY/MM/DD/
            /demand-patterns/YYYY/MM/DD/
        /sales-data/
            /transactions/YYYY/MM/DD/
            /inventory/YYYY/MM/DD/
        /documents/
            /invoices/YYYY/MM/DD/
            /contracts/YYYY/MM/DD/
            /gst-documents/YYYY/MM/DD/
        """
        bucket = s3.Bucket(
            scope,
            "RawDataBucket",
            bucket_name=bucket_name,
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.RETAIN,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="TransitionToIA",
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.INFREQUENT_ACCESS,
                            transition_after=Duration.days(90)
                        ),
                        s3.Transition(
                            storage_class=s3.StorageClass.GLACIER,
                            transition_after=Duration.days(365)
                        )
                    ]
                )
            ]
        )
        return bucket

    @staticmethod
    def create_ml_artifacts_bucket(scope: Construct, bucket_name: str = "retailmind-ml-artifacts") -> s3.Bucket:
        """
        Create S3 bucket for ML model artifacts
        
        Structure:
        /models/
            /demand-forecast/
                /versions/v1/model.tar.gz
                /versions/v2/model.tar.gz
            /pricing-optimization/
                /versions/v1/model.tar.gz
            /fraud-detection/
                /versions/v1/model.tar.gz
        /training-data/
            /demand-forecast/
            /pricing-optimization/
            /fraud-detection/
        /evaluation-results/
            /demand-forecast/YYYY/MM/DD/
            /pricing-optimization/YYYY/MM/DD/
        /feature-store/
            /market-features/
            /inventory-features/
            /pricing-features/
        """
        bucket = s3.Bucket(
            scope,
            "MLArtifactsBucket",
            bucket_name=bucket_name,
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.RETAIN,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="CleanupOldVersions",
                    noncurrent_version_expiration=Duration.days(90)
                )
            ]
        )
        return bucket

    @staticmethod
    def create_processed_data_bucket(scope: Construct, bucket_name: str = "retailmind-processed-data") -> s3.Bucket:
        """
        Create S3 bucket for processed and transformed data
        
        Structure:
        /analytics/
            /market-intelligence/YYYY/MM/DD/
            /demand-forecasts/YYYY/MM/DD/
            /pricing-recommendations/YYYY/MM/DD/
            /inventory-insights/YYYY/MM/DD/
        /reports/
            /daily/YYYY/MM/DD/
            /weekly/YYYY/WW/
            /monthly/YYYY/MM/
        /exports/
            /business-intelligence/
            /audit-trails/
        """
        bucket = s3.Bucket(
            scope,
            "ProcessedDataBucket",
            bucket_name=bucket_name,
            versioned=False,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.RETAIN,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="ExpireOldReports",
                    expiration=Duration.days(730),  # 2 years
                    prefix="reports/"
                )
            ]
        )
        return bucket

    @staticmethod
    def create_workflow_definitions_bucket(scope: Construct, bucket_name: str = "retailmind-workflows") -> s3.Bucket:
        """
        Create S3 bucket for workflow definitions and templates
        
        Structure:
        /templates/
            /pricing-workflows/
            /inventory-workflows/
            /compliance-workflows/
        /generated/
            /YYYY/MM/DD/workflow-{id}.json
        /archived/
            /YYYY/MM/DD/
        """
        bucket = s3.Bucket(
            scope,
            "WorkflowDefinitionsBucket",
            bucket_name=bucket_name,
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.RETAIN
        )
        return bucket

    @staticmethod
    def get_bucket_structure_documentation() -> dict:
        """
        Returns documentation of the S3 bucket structure
        """
        return {
            "raw_data_bucket": {
                "purpose": "Store raw ingested data from various sources",
                "prefixes": {
                    "market-intelligence/pricing/": "Pricing trend data",
                    "market-intelligence/competitor-data/": "Competitor analysis data",
                    "market-intelligence/demand-patterns/": "Demand pattern data",
                    "sales-data/transactions/": "Transaction records",
                    "sales-data/inventory/": "Inventory snapshots",
                    "documents/invoices/": "Invoice documents",
                    "documents/contracts/": "Contract documents",
                    "documents/gst-documents/": "GST compliance documents"
                },
                "lifecycle": "90 days -> IA, 365 days -> Glacier"
            },
            "ml_artifacts_bucket": {
                "purpose": "Store ML models, training data, and evaluation results",
                "prefixes": {
                    "models/demand-forecast/versions/": "Demand forecast model versions",
                    "models/pricing-optimization/versions/": "Pricing optimization model versions",
                    "models/fraud-detection/versions/": "Fraud detection model versions",
                    "training-data/": "Training datasets for ML models",
                    "evaluation-results/": "Model evaluation metrics and results",
                    "feature-store/": "Feature engineering outputs"
                },
                "lifecycle": "Old versions expire after 90 days"
            },
            "processed_data_bucket": {
                "purpose": "Store processed analytics and reports",
                "prefixes": {
                    "analytics/market-intelligence/": "Processed market intelligence",
                    "analytics/demand-forecasts/": "Generated demand forecasts",
                    "analytics/pricing-recommendations/": "Pricing recommendations",
                    "analytics/inventory-insights/": "Inventory optimization insights",
                    "reports/daily/": "Daily reports",
                    "reports/weekly/": "Weekly reports",
                    "reports/monthly/": "Monthly reports",
                    "exports/": "Data exports for external systems"
                },
                "lifecycle": "Reports expire after 730 days"
            },
            "workflow_definitions_bucket": {
                "purpose": "Store workflow templates and generated workflows",
                "prefixes": {
                    "templates/": "Reusable workflow templates",
                    "generated/": "Dynamically generated workflows",
                    "archived/": "Archived workflow definitions"
                },
                "lifecycle": "Versioned, no expiration"
            }
        }
