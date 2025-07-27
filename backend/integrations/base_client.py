"""
Base client for external service integrations
"""
import asyncio
import aiohttp
import structlog
from typing import Dict, Any, Optional, Union
from abc import ABC, abstractmethod
from datetime import datetime, timedelta

logger = structlog.get_logger(__name__)


class APIError(Exception):
    """Base exception for API errors"""
    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[Dict] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data or {}


class RateLimitError(APIError):
    """Exception for rate limit errors"""
    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message, status_code=429)
        self.retry_after = retry_after


class AuthenticationError(APIError):
    """Exception for authentication errors"""
    def __init__(self, message: str):
        super().__init__(message, status_code=401)


class BaseClient(ABC):
    """Base class for external service clients"""
    
    def __init__(self, 
                 service_name: str,
                 base_url: str,
                 api_key: Optional[str] = None,
                 timeout: int = 30,
                 max_retries: int = 3,
                 retry_delay: float = 1.0):
        self.service_name = service_name
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        self.logger = logger.bind(service=service_name)
        self._session: Optional[aiohttp.ClientSession] = None
        self._rate_limit_reset: Optional[datetime] = None
        self._rate_limit_remaining: int = 1000  # Default high value
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def _ensure_session(self) -> None:
        """Ensure aiohttp session is created"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                headers=self._get_default_headers()
            )
    
    async def close(self) -> None:
        """Close the HTTP session"""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    @abstractmethod
    def _get_default_headers(self) -> Dict[str, str]:
        """Get default headers for requests"""
        pass
    
    async def _make_request(self,
                           method: str,
                           endpoint: str,
                           data: Optional[Dict[str, Any]] = None,
                           params: Optional[Dict[str, Any]] = None,
                           headers: Optional[Dict[str, str]] = None,
                           retry_count: int = 0) -> Dict[str, Any]:
        """Make HTTP request with retry logic and rate limiting"""
        await self._ensure_session()
        
        # Check rate limiting
        if self._rate_limit_reset and datetime.utcnow() < self._rate_limit_reset:
            if self._rate_limit_remaining <= 0:
                wait_time = (self._rate_limit_reset - datetime.utcnow()).total_seconds()
                self.logger.warning("Rate limit exceeded, waiting",
                                  wait_time=wait_time,
                                  service=self.service_name)
                await asyncio.sleep(wait_time)
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        request_headers = self._get_default_headers()
        if headers:
            request_headers.update(headers)
        
        try:
            self.logger.debug("Making API request",
                            method=method,
                            url=url,
                            retry_count=retry_count)
            
            async with self._session.request(
                method=method,
                url=url,
                json=data,
                params=params,
                headers=request_headers
            ) as response:
                
                # Update rate limit info from headers
                self._update_rate_limit_info(response.headers)
                
                response_text = await response.text()
                
                # Handle different response types
                if response.status == 204:  # No content
                    return {}
                
                try:
                    response_data = await response.json() if response_text else {}
                except Exception:
                    response_data = {"raw_response": response_text}
                
                # Handle successful responses
                if 200 <= response.status < 300:
                    self.logger.debug("API request successful",
                                    status_code=response.status,
                                    response_size=len(response_text))
                    return response_data
                
                # Handle rate limiting
                if response.status == 429:
                    retry_after = self._get_retry_after(response.headers)
                    if retry_count < self.max_retries:
                        self.logger.warning("Rate limited, retrying",
                                          retry_after=retry_after,
                                          retry_count=retry_count)
                        await asyncio.sleep(retry_after or self.retry_delay)
                        return await self._make_request(method, endpoint, data, params, headers, retry_count + 1)
                    else:
                        raise RateLimitError(
                            f"Rate limit exceeded for {self.service_name}",
                            retry_after=retry_after
                        )
                
                # Handle authentication errors
                if response.status == 401:
                    raise AuthenticationError(f"Authentication failed for {self.service_name}")
                
                # Handle other client/server errors
                error_message = self._extract_error_message(response_data)
                if response.status >= 500 and retry_count < self.max_retries:
                    # Retry server errors
                    self.logger.warning("Server error, retrying",
                                      status_code=response.status,
                                      error=error_message,
                                      retry_count=retry_count)
                    await asyncio.sleep(self.retry_delay * (2 ** retry_count))  # Exponential backoff
                    return await self._make_request(method, endpoint, data, params, headers, retry_count + 1)
                
                raise APIError(
                    f"{self.service_name} API error: {error_message}",
                    status_code=response.status,
                    response_data=response_data
                )
        
        except aiohttp.ClientError as e:
            if retry_count < self.max_retries:
                self.logger.warning("Network error, retrying",
                                  error=str(e),
                                  retry_count=retry_count)
                await asyncio.sleep(self.retry_delay * (2 ** retry_count))
                return await self._make_request(method, endpoint, data, params, headers, retry_count + 1)
            
            raise APIError(f"Network error for {self.service_name}: {str(e)}")
    
    def _update_rate_limit_info(self, headers: Dict[str, str]) -> None:
        """Update rate limit information from response headers"""
        # GitHub-style rate limiting
        if 'x-ratelimit-remaining' in headers:
            self._rate_limit_remaining = int(headers['x-ratelimit-remaining'])
        if 'x-ratelimit-reset' in headers:
            reset_timestamp = int(headers['x-ratelimit-reset'])
            self._rate_limit_reset = datetime.utcfromtimestamp(reset_timestamp)
        
        # Generic rate limiting
        elif 'ratelimit-remaining' in headers:
            self._rate_limit_remaining = int(headers['ratelimit-remaining'])
        if 'ratelimit-reset' in headers:
            reset_timestamp = int(headers['ratelimit-reset'])
            self._rate_limit_reset = datetime.utcfromtimestamp(reset_timestamp)
    
    def _get_retry_after(self, headers: Dict[str, str]) -> Optional[int]:
        """Extract retry-after value from headers"""
        retry_after = headers.get('retry-after')
        if retry_after:
            try:
                return int(retry_after)
            except ValueError:
                # Could be a date string, but we'll just use default
                pass
        return None
    
    def _extract_error_message(self, response_data: Dict[str, Any]) -> str:
        """Extract error message from response data"""
        # Try common error message fields
        for field in ['message', 'error', 'detail', 'error_description']:
            if field in response_data:
                return str(response_data[field])
        
        # If no standard error field, return the whole response
        return str(response_data)
    
    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """Make GET request"""
        return await self._make_request('GET', endpoint, params=params, **kwargs)
    
    async def post(self, endpoint: str, data: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """Make POST request"""
        return await self._make_request('POST', endpoint, data=data, **kwargs)
    
    async def put(self, endpoint: str, data: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """Make PUT request"""
        return await self._make_request('PUT', endpoint, data=data, **kwargs)
    
    async def patch(self, endpoint: str, data: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """Make PATCH request"""
        return await self._make_request('PATCH', endpoint, data=data, **kwargs)
    
    async def delete(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make DELETE request"""
        return await self._make_request('DELETE', endpoint, **kwargs)
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check for this service"""
        try:
            start_time = datetime.utcnow()
            await self._health_check_request()
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return {
                "service": self.service_name,
                "status": "healthy",
                "response_time_ms": round(response_time, 2),
                "rate_limit_remaining": self._rate_limit_remaining,
                "rate_limit_reset": self._rate_limit_reset.isoformat() if self._rate_limit_reset else None
            }
        except Exception as e:
            return {
                "service": self.service_name,
                "status": "unhealthy",
                "error": str(e)
            }
    
    @abstractmethod
    async def _health_check_request(self) -> None:
        """Service-specific health check request"""
        pass

