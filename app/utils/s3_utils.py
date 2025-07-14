"""
Utility functions for S3/Minio file storage operations.
This module provides functionality for both AWS S3 and Minio storage backends.
"""
import os
import uuid
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from flask import current_app
import logging

logger = logging.getLogger(__name__)

def get_s3_client():
    """
    Creates and returns an S3 client configured based on application settings.
    Works with both AWS S3 and Minio storage backends.
    
    Returns:
        boto3.client: Configured S3 client
    """
    # Use environment variables or application config
    endpoint = current_app.config.get('S3_ENDPOINT')
    access_key = current_app.config.get('S3_ACCESS_KEY')
    secret_key = current_app.config.get('S3_SECRET_KEY') 
    region = current_app.config.get('S3_REGION', 'us-east-1')
    use_ssl = current_app.config.get('S3_USE_SSL', True)
    
    # Check if using Minio (self-hosted) instead of AWS S3
    is_minio = current_app.config.get('S3_USE_MINIO', False)
    
    # Configure the client differently for Minio vs AWS S3
    if is_minio:
        s3_client = boto3.client(
            's3',
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            config=Config(signature_version='s3v4'),
            use_ssl=use_ssl,
            verify=use_ssl  # For self-signed certs in dev, might want to disable
        )
    else:
        # Standard AWS S3 client
        s3_client = boto3.client(
            's3',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )
    
    return s3_client

def ensure_bucket_exists():
    """
    Checks if the configured S3 bucket exists and creates it if it doesn't.
    
    Returns:
        bool: True if bucket exists or was created, False if failed
    """
    bucket_name = current_app.config.get('S3_BUCKET_NAME')
    if not bucket_name:
        logger.error("S3_BUCKET_NAME not configured")
        return False
    
    s3_client = get_s3_client()
    
    try:
        # Check if bucket exists
        s3_client.head_bucket(Bucket=bucket_name)
        logger.info(f"Bucket {bucket_name} exists")
        return True
    except ClientError as e:
        # If bucket doesn't exist, create it
        if e.response['Error']['Code'] == '404' or e.response['Error']['Code'] == 'NoSuchBucket':
            try:
                region = current_app.config.get('S3_REGION', 'us-east-1')
                if region == 'us-east-1':
                    s3_client.create_bucket(Bucket=bucket_name)
                else:
                    location = {'LocationConstraint': region}
                    s3_client.create_bucket(
                        Bucket=bucket_name,
                        CreateBucketConfiguration=location
                    )
                logger.info(f"Bucket {bucket_name} created")
                return True
            except ClientError as create_error:
                logger.error(f"Error creating bucket {bucket_name}: {str(create_error)}")
                return False
        else:
            logger.error(f"Error checking bucket {bucket_name}: {str(e)}")
            return False

def upload_file_to_s3(file_data, filename, content_type=None):
    """
    Uploads a file to the S3/Minio bucket.
    
    Args:
        file_data: File-like object or bytes to upload
        filename: Original filename (for reference)
        content_type: MIME type of the file
        
    Returns:
        str: The S3 object key for the uploaded file
    
    Raises:
        ValueError: If configuration is invalid
        ClientError: If S3 operation fails
        Exception: Various exceptions for upload failures
    """
    # Generate a unique object key that will be used for both S3 and local storage
    unique_id = str(uuid.uuid4())
    object_key = f"workspace_files/{unique_id}-{filename}"
    
    # Check for minimum required S3 configuration
    bucket_name = current_app.config.get('S3_BUCKET_NAME')
    endpoint = current_app.config.get('S3_ENDPOINT')
    access_key = current_app.config.get('S3_ACCESS_KEY') 
    secret_key = current_app.config.get('S3_SECRET_KEY')
    
    # First try local storage if any of the required S3 config is missing
    if not all([endpoint, bucket_name, access_key, secret_key]):
        logger.warning("S3 configuration incomplete, using local storage fallback")
        return _store_file_locally(file_data, filename, object_key)
    
    # Try S3 storage with proper error handling
    try:
        # Get S3 client - wrapped in try/except for better error messaging
        s3_client = get_s3_client()
        
        # Prepare extra args for upload
        extra_args = {}
        if content_type:
            extra_args['ContentType'] = content_type
        
        # Reset file pointer to beginning if it's a file-like object with seek method
        if hasattr(file_data, 'seek'):
            file_data.seek(0)
            
        # Upload the file
        s3_client.upload_fileobj(
            file_data,
            bucket_name,
            object_key,
            ExtraArgs=extra_args
        )
        
        logger.info(f"File uploaded successfully to S3: {object_key}")
        return object_key
    except (ClientError, ValueError, Exception) as e:
        logger.error(f"S3 upload failed ({type(e).__name__}): {str(e)}")
        logger.warning("Falling back to local storage")
        return _store_file_locally(file_data, filename, object_key)


def _store_file_locally(file_data, filename, object_key):
    """
    Store a file in the local filesystem as a fallback when S3 is unavailable.
    
    Args:
        file_data: The file data to store
        filename: The original filename
        object_key: The object key to use (already generated)
    
    Returns:
        str: The object key for later reference
    """
    try:
        # Create local uploads directory if it doesn't exist
        import os
        upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'workspace_files')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Extract the filename part from object_key
        local_filename = object_key.split('/')[-1] if '/' in object_key else object_key
        
        # Generate the file path
        file_path = os.path.join(upload_dir, local_filename)
        
        # Reset file pointer to beginning
        if hasattr(file_data, 'seek'):
            file_data.seek(0)
            
        # Save the file locally
        with open(file_path, 'wb') as f:
            if hasattr(file_data, 'read'):
                f.write(file_data.read())
            else:
                f.write(file_data)
                
        logger.warning(f"File saved to local storage: {file_path}")
        return object_key
    except Exception as e:
        logger.error(f"Failed to save file locally: {str(e)}")
        raise Exception(f"Failed to save file: {str(e)}")

def get_file_download_url(object_key, expires_in=3600):
    """
    Generates a pre-signed URL for downloading a file from S3/Minio.
    
    Args:
        object_key: The S3 object key
        expires_in: URL expiration time in seconds (default 1 hour)
        
    Returns:
        str: Pre-signed download URL
        
    Raises:
        Exception: If the URL generation fails
    """
    bucket_name = current_app.config.get('S3_BUCKET_NAME')
    endpoint = current_app.config.get('S3_ENDPOINT')
    
    # Local file fallback for development environments
    if not endpoint or not bucket_name:
        try:
            from flask import url_for
            # Extract filename from object key
            filename = object_key.split('/')[-1] if '/' in object_key else object_key
            
            # Generate URL to static file
            return url_for('static', filename=f'uploads/{object_key}', _external=True)
        except Exception as e:
            logger.error(f"Error generating local file URL: {str(e)}")
            raise Exception(f"Error generating download URL: {str(e)}")
    
    if not bucket_name:
        raise ValueError("S3_BUCKET_NAME not configured")
    
    s3_client = get_s3_client()
    
    try:
        response = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name, 'Key': object_key},
            ExpiresIn=expires_in  # URL valid for 1 hour by default
        )
        return response
    except ClientError as e:
        logger.error(f"Error generating download URL: {str(e)}")
        raise Exception(f"Error generating download URL: {str(e)}")

def delete_file_from_s3(object_key):
    """
    Deletes a file from the S3/Minio bucket.
    
    Args:
        object_key: The S3 object key to delete
        
    Returns:
        bool: True if successfully deleted, False otherwise
        
    Raises:
        Exception: If deletion fails
    """
    bucket_name = current_app.config.get('S3_BUCKET_NAME')
    if not bucket_name:
        raise ValueError("S3_BUCKET_NAME not configured")
    
    s3_client = get_s3_client()
    
    try:
        s3_client.delete_object(Bucket=bucket_name, Key=object_key)
        logger.info(f"File deleted successfully: {object_key}")
        return True
    except ClientError as e:
        logger.error(f"Error deleting file from S3: {str(e)}")
        raise Exception(f"Error deleting file: {str(e)}")
