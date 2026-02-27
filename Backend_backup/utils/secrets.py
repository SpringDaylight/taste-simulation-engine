"""
AWS Secrets Manager utility
"""
import os
import json
import boto3
from botocore.exceptions import ClientError


def get_secret(secret_name: str, region_name: str = "ap-northeast-2") -> dict:
    """
    Get secret from AWS Secrets Manager
    
    Args:
        secret_name: Name of the secret in Secrets Manager
        region_name: AWS region (default: ap-northeast-2)
    
    Returns:
        dict: Secret key-value pairs
    
    Raises:
        ClientError: If secret cannot be retrieved
    """
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ResourceNotFoundException':
            print(f"Secret {secret_name} not found")
        elif error_code == 'InvalidRequestException':
            print(f"Invalid request for secret {secret_name}")
        elif error_code == 'InvalidParameterException':
            print(f"Invalid parameter for secret {secret_name}")
        elif error_code == 'DecryptionFailure':
            print(f"Decryption failed for secret {secret_name}")
        elif error_code == 'InternalServiceError':
            print(f"Internal service error for secret {secret_name}")
        raise e

    # Parse and return secret
    secret = get_secret_value_response['SecretString']
    return json.loads(secret)


def load_kakao_secrets() -> dict:
    """
    Load Kakao OAuth secrets from AWS Secrets Manager or environment variables
    
    Returns:
        dict: Kakao OAuth configuration
    """
    env = os.getenv("ENV", "development")
    
    if env == "production" or env == "staging":
        # Load from AWS Secrets Manager
        try:
            secrets = get_secret("bolrea-malrea/kakao")
            print("Loaded Kakao secrets from AWS Secrets Manager")
            return {
                "KAKAO_CLIENT_ID": secrets.get("KAKAO_CLIENT_ID", ""),
                "KAKAO_CLIENT_SECRET": secrets.get("KAKAO_CLIENT_SECRET", ""),
                "KAKAO_REDIRECT_URI": secrets.get("KAKAO_REDIRECT_URI", ""),
            }
        except Exception as e:
            print(f"Failed to load secrets from AWS Secrets Manager: {e}")
            print("Falling back to environment variables")
    
    # Development or fallback - use environment variables
    return {
        "KAKAO_CLIENT_ID": os.getenv("KAKAO_CLIENT_ID", ""),
        "KAKAO_CLIENT_SECRET": os.getenv("KAKAO_CLIENT_SECRET", ""),
        "KAKAO_REDIRECT_URI": os.getenv("KAKAO_REDIRECT_URI", "http://localhost:5173/auth/kakao/callback"),
    }
