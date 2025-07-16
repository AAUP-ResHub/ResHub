# Local development configuration - DO NOT commit this file to version control!

# S3/MinIO configuration
S3_ENDPOINT = 'http://localhost:9000'  # Change this to your S3 endpoint URL
S3_ACCESS_KEY = 'minioadmin'      # Default MinIO access key
S3_SECRET_KEY = 'minioadmin'      # Default MinIO secret key
S3_REGION = 'us-east-1'                # Change if needed
S3_BUCKET_NAME = 'reshub-files'        # Your S3 bucket name
S3_USE_SSL = False                     # Set to True if your endpoint uses HTTPS
S3_USE_MINIO = True                    # Set to True if using MinIO, False for AWS S3

# Debug settings
DEBUG = True                           # Enable Flask debug mode
