"""
Async wrapper for LLMClient to enable non-blocking LLM operations
"""
import asyncio
from typing import List, Dict, Optional
from botocore.exceptions import BotoCoreError, ClientError
from llm_lab.client import LLMClient


class AsyncLLMClient:
    """Async wrapper for LLMClient"""
    
    def __init__(self, model_id: str = None, timeout: float = 30.0):
        """
        Initialize AsyncLLMClient
        
        Args:
            model_id: Optional model ID to use (defaults to env variable)
            timeout: Timeout in seconds for LLM operations (default: 30.0)
        """
        self._sync_client = LLMClient(model_id)
        self._timeout = timeout
    
    async def generate(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> Dict:
        """
        Async wrapper for LLM generation with error handling and timeout
        
        Executes blocking boto3 call in thread pool to avoid blocking the event loop.
        Handles boto3 errors (BotoCoreError, ClientError) and timeout errors.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            system_prompt: Optional system prompt
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            
        Returns:
            Dict with 'response' and 'usage' keys
            
        Raises:
            BotoCoreError: For boto3 core errors (connection, configuration, etc.)
            ClientError: For AWS service errors (throttling, invalid request, etc.)
            asyncio.TimeoutError: If operation exceeds timeout
            KeyError: For malformed response from LLM
        """
        try:
            # Execute with timeout to prevent indefinite blocking
            return await asyncio.wait_for(
                asyncio.to_thread(
                    self._sync_client.generate,
                    messages,
                    system_prompt,
                    temperature,
                    max_tokens
                ),
                timeout=self._timeout
            )
        except asyncio.TimeoutError:
            # Propagate timeout error with original type
            raise
        except (BotoCoreError, ClientError):
            # Propagate boto3 errors with original types for proper error handling
            raise
        except KeyError:
            # Propagate KeyError for malformed responses
            raise
        except Exception as e:
            # Wrap unexpected errors
            raise RuntimeError(f"Unexpected error in async LLM generate: {e}") from e
    
    async def generate_simple(
        self,
        prompt: str,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Async wrapper for simple generation with error handling and timeout
        
        Executes blocking boto3 call in thread pool to avoid blocking the event loop.
        Handles boto3 errors (BotoCoreError, ClientError) and timeout errors.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            
        Returns:
            Generated text
            
        Raises:
            BotoCoreError: For boto3 core errors (connection, configuration, etc.)
            ClientError: For AWS service errors (throttling, invalid request, etc.)
            asyncio.TimeoutError: If operation exceeds timeout
            KeyError: For malformed response from LLM
        """
        try:
            # Execute with timeout to prevent indefinite blocking
            return await asyncio.wait_for(
                asyncio.to_thread(
                    self._sync_client.generate_simple,
                    prompt,
                    system_prompt
                ),
                timeout=self._timeout
            )
        except asyncio.TimeoutError:
            # Propagate timeout error with original type
            raise
        except (BotoCoreError, ClientError):
            # Propagate boto3 errors with original types for proper error handling
            raise
        except KeyError:
            # Propagate KeyError for malformed responses
            raise
        except Exception as e:
            # Wrap unexpected errors
            raise RuntimeError(f"Unexpected error in async LLM generate_simple: {e}") from e
