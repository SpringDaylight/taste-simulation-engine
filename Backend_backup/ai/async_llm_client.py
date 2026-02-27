"""
Async wrapper for BedrockClient to enable non-blocking LLM operations
"""
import asyncio
from botocore.exceptions import BotoCoreError, ClientError
from ai.llm_client import BedrockClient


class AsyncBedrockClient:
    """Async wrapper for BedrockClient"""
    
    def __init__(self, timeout: float = 30.0):
        """
        Initialize AsyncBedrockClient
        
        Args:
            timeout: Timeout in seconds for LLM operations (default: 30.0)
        """
        self._sync_client = BedrockClient()
        self._timeout = timeout
    
    async def invoke(self, system_prompt: str, user_prompt: str, retry: int = 2) -> str:
        """
        Async wrapper for Bedrock invoke with error handling and timeout
        
        Executes blocking boto3 call in thread pool to avoid blocking the event loop.
        Handles boto3 errors (BotoCoreError, ClientError) and timeout errors.
        
        Args:
            system_prompt: System prompt for the LLM
            user_prompt: User prompt for the LLM
            retry: Number of retry attempts (default: 2)
            
        Returns:
            Generated text response from the LLM
            
        Raises:
            BotoCoreError: For boto3 core errors (connection, configuration, etc.)
            ClientError: For AWS service errors (throttling, invalid request, etc.)
            asyncio.TimeoutError: If operation exceeds timeout
            RuntimeError: For other LLM invocation failures
        """
        try:
            # Execute with timeout to prevent indefinite blocking
            return await asyncio.wait_for(
                asyncio.to_thread(
                    self._sync_client.invoke,
                    system_prompt,
                    user_prompt,
                    retry
                ),
                timeout=self._timeout
            )
        except asyncio.TimeoutError:
            # Propagate timeout error with original type
            raise
        except (BotoCoreError, ClientError):
            # Propagate boto3 errors with original types for proper error handling
            raise
        except RuntimeError:
            # Propagate RuntimeError from sync client (already wrapped)
            raise
        except Exception as e:
            # Wrap unexpected errors
            raise RuntimeError(f"Unexpected error in async Bedrock invoke: {e}") from e
