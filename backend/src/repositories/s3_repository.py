"""
S3 repository for data storage and retrieval
"""
import json
import io
from typing import Optional, List, Dict, Any, BinaryIO
from datetime import datetime
from botocore.exceptions import ClientError

from ..utils.aws_clients import aws_clients


class S3Repository:
    """Repository for S3 data access operations"""

    def __init__(self, bucket_name: str):
        """
        Initialize S3 repository
        
        Args:
            bucket_name: Name of the S3 bucket to use
        """
        self.bucket_name = bucket_name
        self.s3_client = aws_clients.s3

    def upload_file(self, file_path: str, s3_key: str, metadata: Optional[Dict[str, str]] = None) -> bool:
        """
        Upload a file to S3
        
        Args:
            file_path: Local file path to upload
            s3_key: S3 object key (path in bucket)
            metadata: Optional metadata to attach to the object
            
        Returns:
            True if successful, raises exception otherwise
        """
        try:
            extra_args = {}
            if metadata:
                extra_args['Metadata'] = metadata
            
            self.s3_client.upload_file(file_path, self.bucket_name, s3_key, ExtraArgs=extra_args)
            return True
        except ClientError as e:
            raise Exception(f"Failed to upload file to S3: {e.response['Error']['Message']}")

    def upload_data(self, data: bytes, s3_key: str, content_type: str = 'application/octet-stream', 
                    metadata: Optional[Dict[str, str]] = None) -> bool:
        """
        Upload binary data to S3
        
        Args:
            data: Binary data to upload
            s3_key: S3 object key (path in bucket)
            content_type: MIME type of the data
            metadata: Optional metadata to attach to the object
            
        Returns:
            True if successful, raises exception otherwise
        """
        try:
            extra_args = {'ContentType': content_type}
            if metadata:
                extra_args['Metadata'] = metadata
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=data,
                **extra_args
            )
            return True
        except ClientError as e:
            raise Exception(f"Failed to upload data to S3: {e.response['Error']['Message']}")

    def upload_json(self, data: Dict[str, Any], s3_key: str, metadata: Optional[Dict[str, str]] = None) -> bool:
        """
        Upload JSON data to S3
        
        Args:
            data: Dictionary to serialize as JSON
            s3_key: S3 object key (path in bucket)
            metadata: Optional metadata to attach to the object
            
        Returns:
            True if successful, raises exception otherwise
        """
        try:
            json_data = json.dumps(data, indent=2)
            return self.upload_data(json_data.encode('utf-8'), s3_key, 'application/json', metadata)
        except Exception as e:
            raise Exception(f"Failed to upload JSON to S3: {str(e)}")

    def download_file(self, s3_key: str, local_path: str) -> bool:
        """
        Download a file from S3
        
        Args:
            s3_key: S3 object key (path in bucket)
            local_path: Local file path to save to
            
        Returns:
            True if successful, raises exception otherwise
        """
        try:
            self.s3_client.download_file(self.bucket_name, s3_key, local_path)
            return True
        except ClientError as e:
            raise Exception(f"Failed to download file from S3: {e.response['Error']['Message']}")

    def download_data(self, s3_key: str) -> bytes:
        """
        Download binary data from S3
        
        Args:
            s3_key: S3 object key (path in bucket)
            
        Returns:
            Binary data from S3
        """
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            return response['Body'].read()
        except ClientError as e:
            raise Exception(f"Failed to download data from S3: {e.response['Error']['Message']}")

    def download_json(self, s3_key: str) -> Dict[str, Any]:
        """
        Download and parse JSON data from S3
        
        Args:
            s3_key: S3 object key (path in bucket)
            
        Returns:
            Parsed JSON data as dictionary
        """
        try:
            data = self.download_data(s3_key)
            return json.loads(data.decode('utf-8'))
        except Exception as e:
            raise Exception(f"Failed to download JSON from S3: {str(e)}")

    def delete(self, s3_key: str) -> bool:
        """
        Delete an object from S3
        
        Args:
            s3_key: S3 object key (path in bucket)
            
        Returns:
            True if successful, raises exception otherwise
        """
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError as e:
            raise Exception(f"Failed to delete object from S3: {e.response['Error']['Message']}")

    def exists(self, s3_key: str) -> bool:
        """
        Check if an object exists in S3
        
        Args:
            s3_key: S3 object key (path in bucket)
            
        Returns:
            True if object exists, False otherwise
        """
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            raise Exception(f"Failed to check object existence in S3: {e.response['Error']['Message']}")

    def list_objects(self, prefix: str = '', max_keys: int = 1000) -> List[Dict[str, Any]]:
        """
        List objects in S3 with a given prefix
        
        Args:
            prefix: Prefix to filter objects (e.g., 'market-intelligence/pricing/')
            max_keys: Maximum number of keys to return
            
        Returns:
            List of object metadata dictionaries
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys
            )
            
            if 'Contents' not in response:
                return []
            
            return [
                {
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'],
                    'etag': obj['ETag']
                }
                for obj in response['Contents']
            ]
        except ClientError as e:
            raise Exception(f"Failed to list objects in S3: {e.response['Error']['Message']}")

    def get_metadata(self, s3_key: str) -> Dict[str, Any]:
        """
        Get metadata for an S3 object
        
        Args:
            s3_key: S3 object key (path in bucket)
            
        Returns:
            Object metadata dictionary
        """
        try:
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return {
                'content_type': response.get('ContentType'),
                'content_length': response.get('ContentLength'),
                'last_modified': response.get('LastModified'),
                'etag': response.get('ETag'),
                'metadata': response.get('Metadata', {})
            }
        except ClientError as e:
            raise Exception(f"Failed to get object metadata from S3: {e.response['Error']['Message']}")

    def copy(self, source_key: str, destination_key: str, destination_bucket: Optional[str] = None) -> bool:
        """
        Copy an object within S3
        
        Args:
            source_key: Source S3 object key
            destination_key: Destination S3 object key
            destination_bucket: Destination bucket (defaults to same bucket)
            
        Returns:
            True if successful, raises exception otherwise
        """
        try:
            dest_bucket = destination_bucket or self.bucket_name
            copy_source = {'Bucket': self.bucket_name, 'Key': source_key}
            
            self.s3_client.copy_object(
                CopySource=copy_source,
                Bucket=dest_bucket,
                Key=destination_key
            )
            return True
        except ClientError as e:
            raise Exception(f"Failed to copy object in S3: {e.response['Error']['Message']}")

    def generate_presigned_url(self, s3_key: str, expiration: int = 3600, http_method: str = 'GET') -> str:
        """
        Generate a presigned URL for temporary access to an S3 object
        
        Args:
            s3_key: S3 object key (path in bucket)
            expiration: URL expiration time in seconds (default: 1 hour)
            http_method: HTTP method for the URL (GET, PUT, etc.)
            
        Returns:
            Presigned URL string
        """
        try:
            client_method = 'get_object' if http_method == 'GET' else 'put_object'
            url = self.s3_client.generate_presigned_url(
                client_method,
                Params={'Bucket': self.bucket_name, 'Key': s3_key},
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            raise Exception(f"Failed to generate presigned URL: {e.response['Error']['Message']}")
