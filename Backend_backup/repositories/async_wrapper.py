"""
Async wrapper utilities for repository operations

This module provides utilities to wrap synchronous SQLAlchemy repository
operations with asyncio.to_thread() for concurrent request handling.
"""
import asyncio
import logging
from typing import Type, Any, Callable, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from db import SessionLocal

# Configure logger
logger = logging.getLogger(__name__)


class AsyncRepositoryWrapper:
    """Generic async wrapper for repository operations"""
    
    @staticmethod
    async def execute_query(
        repo_class: Type,
        method_name: str,
        *args,
        timeout: float = 30.0,
        **kwargs
    ) -> Any:
        """
        Execute repository method in thread pool with proper session lifecycle and error handling
        
        This method wraps synchronous repository operations to run in a thread pool,
        allowing the async event loop to continue processing other requests while
        waiting for database I/O operations.
        
        Session Lifecycle:
        1. Open: Create new session via SessionLocal()
        2. Execute: Run repository method with provided arguments
        3. Commit: Commit transaction on success
        4. Rollback: Rollback transaction on error
        5. Close: Always close session in finally block
        
        Error Handling:
        - SQLAlchemyError: Database errors are caught, rolled back, and propagated
        - asyncio.TimeoutError: Long-running operations are timed out
        - Session cleanup errors are logged but don't fail the request
        
        Args:
            repo_class: Repository class to instantiate
            method_name: Name of the repository method to call
            *args: Positional arguments to pass to the method
            timeout: Timeout in seconds for the operation (default: 30.0)
            **kwargs: Keyword arguments to pass to the method
            
        Returns:
            Result from the repository method
            
        Raises:
            SQLAlchemyError: For database errors (connection, query, constraint violations, etc.)
            asyncio.TimeoutError: If operation exceeds timeout
            AttributeError: If method_name doesn't exist on repo_class
            
        Example:
            # Get all movie vectors with movie info
            result = await AsyncRepositoryWrapper.execute_query(
                MovieVectorRepository,
                'get_all_with_movie_info'
            )
            
            # Search movies with filters
            movies = await AsyncRepositoryWrapper.execute_query(
                MovieRepository,
                'search',
                query="action",
                genres=["Action"],
                limit=10
            )
        """
        def _execute():
            """Inner function to execute in thread pool"""
            db: Optional[Session] = None
            try:
                # Open session
                db = SessionLocal()
                
                # Instantiate repository with session
                repo = repo_class(db)
                
                # Get method from repository
                method = getattr(repo, method_name)
                
                # Execute method with provided arguments
                result = method(*args, **kwargs)
                
                # Commit transaction on success
                db.commit()
                
                return result
                
            except SQLAlchemyError as e:
                # Rollback transaction on database error
                if db:
                    try:
                        db.rollback()
                    except Exception as rollback_error:
                        logger.error(f"Failed to rollback transaction: {rollback_error}")
                # Propagate SQLAlchemy error with original type
                raise
                
            except Exception as e:
                # Rollback transaction on any other error
                if db:
                    try:
                        db.rollback()
                    except Exception as rollback_error:
                        logger.error(f"Failed to rollback transaction: {rollback_error}")
                raise
                
            finally:
                # Always close session
                if db:
                    try:
                        db.close()
                    except Exception as close_error:
                        # Log but don't raise - session cleanup failure shouldn't fail request
                        logger.error(f"Failed to close database session: {close_error}")
        
        try:
            # Execute in thread pool with timeout to avoid blocking event loop
            return await asyncio.wait_for(
                asyncio.to_thread(_execute),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            # Propagate timeout error with original type
            logger.error(f"Database operation timed out: {repo_class.__name__}.{method_name}")
            raise
        except SQLAlchemyError:
            # Propagate SQLAlchemy errors with original types for proper error handling
            raise
        except Exception as e:
            # Wrap unexpected errors
            raise RuntimeError(f"Unexpected error in async repository operation: {e}") from e
