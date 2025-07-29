"""
Bulk operations and batch processing for Codegen API client
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional, AsyncGenerator, Callable, Union, Tuple
from dataclasses import dataclass
import time
from datetime import datetime
import structlog
from .models import (
    UserResponse, AgentRunResponse, OrganizationResponse,
    AgentRunsResponse, UsersResponse, PaginatedResponse
)
from .exceptions import BulkOperationError, CodegenAPIError

logger = structlog.get_logger(__name__)


@dataclass
class BulkOperationConfig:
    """Configuration for bulk operations"""
    max_workers: int = 5
    batch_size: int = 100
    max_retries: int = 3
    retry_delay: float = 1.0
    timeout_per_operation: float = 30.0
    fail_fast: bool = False  # Stop on first error
    progress_callback: Optional[Callable[[int, int], None]] = None


@dataclass
class BulkOperationResult:
    """Result of a bulk operation"""
    total_items: int
    successful_items: int
    failed_items: int
    results: List[Any]
    errors: List[Dict[str, Any]]
    duration_seconds: float
    success_rate: float


class BulkOperationManager:
    """Manages bulk operations with concurrency and error handling"""
    
    def __init__(self, config: Optional[BulkOperationConfig] = None):
        self.config = config or BulkOperationConfig()
        self._stats = {
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'total_items_processed': 0
        }
    
    async def execute_bulk_async(self,
                                items: List[Any],
                                operation_func: Callable,
                                *args,
                                **kwargs) -> BulkOperationResult:
        """Execute bulk operation asynchronously"""
        start_time = time.time()
        total_items = len(items)
        successful_items = 0
        failed_items = 0
        results = []
        errors = []
        
        logger.info("Starting bulk async operation", 
                   total_items=total_items,
                   max_workers=self.config.max_workers)
        
        # Create semaphore to limit concurrency
        semaphore = asyncio.Semaphore(self.config.max_workers)
        
        async def process_item(item, index):
            async with semaphore:
                try:
                    if asyncio.iscoroutinefunction(operation_func):
                        result = await operation_func(item, *args, **kwargs)
                    else:
                        result = operation_func(item, *args, **kwargs)
                    
                    if self.config.progress_callback:
                        self.config.progress_callback(index + 1, total_items)
                    
                    return {'success': True, 'result': result, 'item': item, 'index': index}
                    
                except Exception as e:
                    error_info = {
                        'success': False,
                        'error': str(e),
                        'error_type': type(e).__name__,
                        'item': item,
                        'index': index
                    }
                    
                    if self.config.fail_fast:
                        raise BulkOperationError(f"Operation failed at item {index}: {str(e)}")
                    
                    return error_info
        
        # Execute all operations concurrently
        tasks = [process_item(item, i) for i, item in enumerate(items)]
        
        try:
            completed_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for result in completed_results:
                if isinstance(result, Exception):
                    failed_items += 1
                    errors.append({
                        'error': str(result),
                        'error_type': type(result).__name__
                    })
                elif result['success']:
                    successful_items += 1
                    results.append(result['result'])
                else:
                    failed_items += 1
                    errors.append(result)
            
        except Exception as e:
            logger.error("Bulk operation failed", error=str(e))
            raise BulkOperationError(f"Bulk operation failed: {str(e)}")
        
        duration = time.time() - start_time
        success_rate = (successful_items / total_items) * 100 if total_items > 0 else 0
        
        # Update stats
        self._stats['total_operations'] += 1
        self._stats['total_items_processed'] += total_items
        
        if success_rate > 50:  # Consider successful if more than 50% succeeded
            self._stats['successful_operations'] += 1
        else:
            self._stats['failed_operations'] += 1
        
        result = BulkOperationResult(
            total_items=total_items,
            successful_items=successful_items,
            failed_items=failed_items,
            results=results,
            errors=errors,
            duration_seconds=duration,
            success_rate=success_rate
        )
        
        logger.info("Bulk async operation completed",
                   total_items=total_items,
                   successful_items=successful_items,
                   failed_items=failed_items,
                   success_rate=success_rate,
                   duration_seconds=duration)
        
        return result
    
    def execute_bulk_sync(self,
                         items: List[Any],
                         operation_func: Callable,
                         *args,
                         **kwargs) -> BulkOperationResult:
        """Execute bulk operation synchronously with ThreadPoolExecutor"""
        start_time = time.time()
        total_items = len(items)
        successful_items = 0
        failed_items = 0
        results = []
        errors = []
        
        logger.info("Starting bulk sync operation",
                   total_items=total_items,
                   max_workers=self.config.max_workers)
        
        def process_item(item_with_index):
            item, index = item_with_index
            try:
                result = operation_func(item, *args, **kwargs)
                
                if self.config.progress_callback:
                    self.config.progress_callback(index + 1, total_items)
                
                return {'success': True, 'result': result, 'item': item, 'index': index}
                
            except Exception as e:
                error_info = {
                    'success': False,
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'item': item,
                    'index': index
                }
                
                if self.config.fail_fast:
                    raise BulkOperationError(f"Operation failed at item {index}: {str(e)}")
                
                return error_info
        
        # Execute with ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            items_with_index = [(item, i) for i, item in enumerate(items)]
            futures = {executor.submit(process_item, item_info): item_info for item_info in items_with_index}
            
            for future in as_completed(futures):
                try:
                    result = future.result()
                    
                    if result['success']:
                        successful_items += 1
                        results.append(result['result'])
                    else:
                        failed_items += 1
                        errors.append(result)
                        
                except Exception as e:
                    failed_items += 1
                    errors.append({
                        'error': str(e),
                        'error_type': type(e).__name__
                    })
        
        duration = time.time() - start_time
        success_rate = (successful_items / total_items) * 100 if total_items > 0 else 0
        
        # Update stats
        self._stats['total_operations'] += 1
        self._stats['total_items_processed'] += total_items
        
        if success_rate > 50:
            self._stats['successful_operations'] += 1
        else:
            self._stats['failed_operations'] += 1
        
        result = BulkOperationResult(
            total_items=total_items,
            successful_items=successful_items,
            failed_items=failed_items,
            results=results,
            errors=errors,
            duration_seconds=duration,
            success_rate=success_rate
        )
        
        logger.info("Bulk sync operation completed",
                   total_items=total_items,
                   successful_items=successful_items,
                   failed_items=failed_items,
                   success_rate=success_rate,
                   duration_seconds=duration)
        
        return result
    
    def get_stats(self) -> Dict[str, Any]:
        """Get bulk operation statistics"""
        return {
            'total_operations': self._stats['total_operations'],
            'successful_operations': self._stats['successful_operations'],
            'failed_operations': self._stats['failed_operations'],
            'total_items_processed': self._stats['total_items_processed'],
            'success_rate': (self._stats['successful_operations'] / max(1, self._stats['total_operations'])) * 100,
            'average_items_per_operation': self._stats['total_items_processed'] / max(1, self._stats['total_operations'])
        }


class PaginationHelper:
    """Helper for handling paginated API responses"""
    
    @staticmethod
    async def get_all_pages_async(fetch_func: Callable,
                                 initial_skip: int = 0,
                                 limit: int = 100,
                                 max_pages: Optional[int] = None) -> List[Any]:
        """Fetch all pages from a paginated API endpoint asynchronously"""
        all_items = []
        skip = initial_skip
        page_count = 0
        
        while True:
            if max_pages and page_count >= max_pages:
                break
            
            try:
                response = await fetch_func(skip=skip, limit=limit)
                
                # Handle different response types
                if hasattr(response, 'items'):
                    items = response.items
                    total = getattr(response, 'total', None)
                elif isinstance(response, dict) and 'items' in response:
                    items = response['items']
                    total = response.get('total')
                else:
                    # Assume response is a list
                    items = response if isinstance(response, list) else [response]
                    total = None
                
                all_items.extend(items)
                
                # Check if we've got all items
                if len(items) < limit:
                    break
                
                if total and len(all_items) >= total:
                    break
                
                skip += limit
                page_count += 1
                
                # Add small delay to avoid overwhelming the API
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error("Error fetching page", skip=skip, limit=limit, error=str(e))
                raise
        
        logger.info("Fetched all pages", total_items=len(all_items), pages_fetched=page_count + 1)
        return all_items
    
    @staticmethod
    def get_all_pages_sync(fetch_func: Callable,
                          initial_skip: int = 0,
                          limit: int = 100,
                          max_pages: Optional[int] = None) -> List[Any]:
        """Fetch all pages from a paginated API endpoint synchronously"""
        all_items = []
        skip = initial_skip
        page_count = 0
        
        while True:
            if max_pages and page_count >= max_pages:
                break
            
            try:
                response = fetch_func(skip=skip, limit=limit)
                
                # Handle different response types
                if hasattr(response, 'items'):
                    items = response.items
                    total = getattr(response, 'total', None)
                elif isinstance(response, dict) and 'items' in response:
                    items = response['items']
                    total = response.get('total')
                else:
                    items = response if isinstance(response, list) else [response]
                    total = None
                
                all_items.extend(items)
                
                if len(items) < limit:
                    break
                
                if total and len(all_items) >= total:
                    break
                
                skip += limit
                page_count += 1
                
                # Add small delay
                time.sleep(0.1)
                
            except Exception as e:
                logger.error("Error fetching page", skip=skip, limit=limit, error=str(e))
                raise
        
        logger.info("Fetched all pages", total_items=len(all_items), pages_fetched=page_count + 1)
        return all_items


class StreamingPaginator:
    """Streaming paginator for large datasets"""
    
    def __init__(self, fetch_func: Callable, batch_size: int = 100):
        self.fetch_func = fetch_func
        self.batch_size = batch_size
    
    async def stream_items(self) -> AsyncGenerator[Any, None]:
        """Stream items one by one from paginated API"""
        skip = 0
        
        while True:
            try:
                response = await self.fetch_func(skip=skip, limit=self.batch_size)
                
                # Handle different response types
                if hasattr(response, 'items'):
                    items = response.items
                elif isinstance(response, dict) and 'items' in response:
                    items = response['items']
                else:
                    items = response if isinstance(response, list) else [response]
                
                if not items:
                    break
                
                for item in items:
                    yield item
                
                if len(items) < self.batch_size:
                    break
                
                skip += self.batch_size
                
                # Small delay between batches
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error("Error streaming items", skip=skip, error=str(e))
                raise
    
    async def stream_batches(self) -> AsyncGenerator[List[Any], None]:
        """Stream items in batches from paginated API"""
        skip = 0
        
        while True:
            try:
                response = await self.fetch_func(skip=skip, limit=self.batch_size)
                
                # Handle different response types
                if hasattr(response, 'items'):
                    items = response.items
                elif isinstance(response, dict) and 'items' in response:
                    items = response['items']
                else:
                    items = response if isinstance(response, list) else [response]
                
                if not items:
                    break
                
                yield items
                
                if len(items) < self.batch_size:
                    break
                
                skip += self.batch_size
                
                # Small delay between batches
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error("Error streaming batches", skip=skip, error=str(e))
                raise


class BatchProcessor:
    """Process items in batches with configurable batch size and processing"""
    
    def __init__(self, batch_size: int = 100, max_workers: int = 5):
        self.batch_size = batch_size
        self.max_workers = max_workers
    
    async def process_in_batches(self,
                               items: List[Any],
                               batch_processor: Callable[[List[Any]], Any]) -> List[Any]:
        """Process items in batches"""
        results = []
        
        # Split items into batches
        batches = [items[i:i + self.batch_size] for i in range(0, len(items), self.batch_size)]
        
        logger.info("Processing in batches", 
                   total_items=len(items),
                   batch_count=len(batches),
                   batch_size=self.batch_size)
        
        # Process batches concurrently
        semaphore = asyncio.Semaphore(self.max_workers)
        
        async def process_batch(batch, batch_index):
            async with semaphore:
                try:
                    if asyncio.iscoroutinefunction(batch_processor):
                        result = await batch_processor(batch)
                    else:
                        result = batch_processor(batch)
                    
                    logger.debug("Batch processed", 
                               batch_index=batch_index,
                               batch_size=len(batch))
                    
                    return result
                    
                except Exception as e:
                    logger.error("Batch processing failed",
                               batch_index=batch_index,
                               error=str(e))
                    raise
        
        # Execute all batches
        tasks = [process_batch(batch, i) for i, batch in enumerate(batches)]
        batch_results = await asyncio.gather(*tasks)
        
        # Flatten results if they are lists
        for batch_result in batch_results:
            if isinstance(batch_result, list):
                results.extend(batch_result)
            else:
                results.append(batch_result)
        
        logger.info("Batch processing completed",
                   total_batches=len(batches),
                   total_results=len(results))
        
        return results


# Utility functions for common bulk operations
async def bulk_fetch_users(client, org_id: str, user_ids: List[str]) -> BulkOperationResult:
    """Bulk fetch users by their IDs"""
    bulk_manager = BulkOperationManager()
    
    async def fetch_user(user_id):
        return await client.get_user(org_id, user_id)
    
    return await bulk_manager.execute_bulk_async(user_ids, fetch_user)


async def bulk_create_agent_runs(client, 
                                org_id: int,
                                run_configs: List[Dict[str, Any]]) -> BulkOperationResult:
    """Bulk create agent runs"""
    bulk_manager = BulkOperationManager()
    
    async def create_run(config):
        return await client.create_agent_run(org_id, **config)
    
    return await bulk_manager.execute_bulk_async(run_configs, create_run)


async def stream_all_agent_runs(client, org_id: int) -> AsyncGenerator[AgentRunResponse, None]:
    """Stream all agent runs for an organization"""
    paginator = StreamingPaginator(
        lambda skip, limit: client.list_agent_runs(org_id, skip=skip, limit=limit)
    )
    
    async for run in paginator.stream_items():
        yield run


async def get_all_users_with_pagination(client, org_id: str) -> List[UserResponse]:
    """Get all users using automatic pagination"""
    return await PaginationHelper.get_all_pages_async(
        lambda skip, limit: client.get_users(org_id, skip=skip, limit=limit)
    )


# Progress tracking utilities
class ProgressTracker:
    """Track progress of bulk operations"""
    
    def __init__(self, total_items: int, update_interval: int = 10):
        self.total_items = total_items
        self.update_interval = update_interval
        self.completed_items = 0
        self.start_time = time.time()
        self.last_update = 0
    
    def update(self, completed: int, total: Optional[int] = None):
        """Update progress"""
        self.completed_items = completed
        if total:
            self.total_items = total
        
        # Only log progress at intervals
        if completed - self.last_update >= self.update_interval or completed == self.total_items:
            elapsed = time.time() - self.start_time
            rate = completed / elapsed if elapsed > 0 else 0
            eta = (self.total_items - completed) / rate if rate > 0 else 0
            
            logger.info("Bulk operation progress",
                       completed=completed,
                       total=self.total_items,
                       percentage=round((completed / self.total_items) * 100, 1),
                       rate_per_second=round(rate, 2),
                       eta_seconds=round(eta, 1))
            
            self.last_update = completed


# Global bulk operation manager
default_bulk_manager = BulkOperationManager()

