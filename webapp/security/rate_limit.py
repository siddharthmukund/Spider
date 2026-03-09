"""Rate limiting module using token bucket algorithm.

Provides both in-memory and Redis-backed rate limiting.
"""
import time
from collections import defaultdict
from dataclasses import dataclass, field
from threading import Lock
from typing import Dict, Optional
import os


@dataclass
class TokenBucket:
    """Token bucket rate limiter implementation."""
    
    capacity: int
    refill_rate: float  # tokens per second
    tokens: float = field(default=0.0)
    last_refill: float = field(default_factory=time.monotonic)
    lock: Lock = field(default_factory=Lock)
    
    def __post_init__(self):
        """Initialize tokens to capacity."""
        self.tokens = float(self.capacity)
    
    def consume(self, tokens: int = 1) -> bool:
        """
        Attempt to consume tokens from the bucket.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            bool: True if tokens were available and consumed, False otherwise
        """
        with self.lock:
            now = time.monotonic()
            elapsed = now - self.last_refill
            
            # Refill tokens based on elapsed time
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            self.last_refill = now
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            
            return False
    
    def get_wait_time(self, tokens: int = 1) -> float:
        """
        Get time to wait until tokens are available.
        
        Args:
            tokens: Number of tokens needed
            
        Returns:
            float: Seconds to wait, or 0 if tokens already available
        """
        with self.lock:
            now = time.monotonic()
            elapsed = now - self.last_refill
            future_tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            
            if future_tokens >= tokens:
                return 0.0
            
            deficit = tokens - future_tokens
            return deficit / self.refill_rate


class RateLimiter:
    """Per-client rate limiting using token bucket algorithm."""
    
    def __init__(
        self,
        requests_per_minute: int = 60,
        burst_capacity: Optional[int] = None
    ):
        """
        Initialize rate limiter.
        
        Args:
            requests_per_minute: Sustained rate limit
            burst_capacity: Maximum burst capacity (defaults to requests_per_minute)
        """
        self.requests_per_minute = requests_per_minute
        self.burst_capacity = burst_capacity or requests_per_minute
        self.refill_rate = requests_per_minute / 60.0  # tokens per second
        
        self.buckets: Dict[str, TokenBucket] = defaultdict(self._create_bucket)
        self._cleanup_lock = Lock()
        self._last_cleanup = time.monotonic()
    
    def _create_bucket(self) -> TokenBucket:
        """Create a new token bucket for a client."""
        return TokenBucket(
            capacity=self.burst_capacity,
            refill_rate=self.refill_rate
        )
    
    def check(self, client_id: str, tokens: int = 1) -> bool:
        """
        Check if request should be allowed.
        
        Args:
            client_id: Unique identifier for the client (e.g., IP address)
            tokens: Number of tokens to consume (default 1)
            
        Returns:
            bool: True if request allowed, False if rate limited
        """
        # Periodic cleanup of old buckets
        self._periodic_cleanup()
        
        bucket = self.buckets[client_id]
        return bucket.consume(tokens)
    
    def get_wait_time(self, client_id: str, tokens: int = 1) -> float:
        """
        Get time to wait until request can be allowed.
        
        Args:
            client_id: Unique identifier for the client
            tokens: Number of tokens needed
            
        Returns:
            float: Seconds to wait
        """
        bucket = self.buckets[client_id]
        return bucket.get_wait_time(tokens)
    
    def _periodic_cleanup(self):
        """Remove old buckets to prevent memory leak."""
        with self._cleanup_lock:
            now = time.monotonic()
            # Cleanup every 5 minutes
            if now - self._last_cleanup < 300:
                return
            
            self._last_cleanup = now
            
            # Remove buckets inactive for >10 minutes
            inactive_threshold = now - 600
            to_remove = [
                client_id for client_id, bucket in self.buckets.items()
                if bucket.last_refill < inactive_threshold
            ]
            
            for client_id in to_remove:
                del self.buckets[client_id]


class RedisRateLimiter:
    """Redis-backed rate limiter for distributed systems."""
    
    def __init__(
        self,
        redis_url: Optional[str] = None,
        requests_per_minute: int = 60,
        window_seconds: int = 60
    ):
        """
        Initialize Redis rate limiter.
        
        Args:
            redis_url: Redis connection URL (defaults to REDIS_URL env var)
            requests_per_minute: Request limit per window
            window_seconds: Time window in seconds
        """
        import redis
        
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.requests_per_minute = requests_per_minute
        self.window_seconds = window_seconds
        
        try:
            self.redis = redis.from_url(self.redis_url, decode_responses=True)
            self.redis.ping()
        except Exception as e:
            raise RuntimeError(f"Failed to connect to Redis at {self.redis_url}: {e}")
    
    def check(self, client_id: str) -> bool:
        """
        Check if request should be allowed using Redis sliding window.
        
        Args:
            client_id: Unique identifier for the client
            
        Returns:
            bool: True if request allowed, False if rate limited
        """
        key = f"rate_limit:{client_id}"
        now = time.time()
        window_start = now - self.window_seconds
        
        try:
            pipe = self.redis.pipeline()
            
            # Remove old entries outside the window
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Count requests in current window
            pipe.zcard(key)
            
            # Add current request
            pipe.zadd(key, {str(now): now})
            
            # Set expiry
            pipe.expire(key, self.window_seconds)
            
            results = pipe.execute()
            count = results[1]  # Count from zcard
            
            return count < self.requests_per_minute
            
        except Exception as e:
            # On Redis failure, fail open (allow request) to avoid blocking legitimate traffic
            # Log the error in production
            return True
    
    def get_remaining(self, client_id: str) -> int:
        """
        Get remaining requests in current window.
        
        Args:
            client_id: Unique identifier for the client
            
        Returns:
            int: Number of requests remaining
        """
        key = f"rate_limit:{client_id}"
        now = time.time()
        window_start = now - self.window_seconds
        
        try:
            # Remove old entries and count
            pipe = self.redis.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zcard(key)
            results = pipe.execute()
            count = results[1]
            
            return max(0, self.requests_per_minute - count)
            
        except Exception:
            return self.requests_per_minute  # Fail open


# Factory function to create appropriate rate limiter
def create_rate_limiter(
    requests_per_minute: int = 60,
    use_redis: bool = False,
    redis_url: Optional[str] = None
) -> RateLimiter | RedisRateLimiter:
    """
    Create a rate limiter instance.
    
    Args:
        requests_per_minute: Request limit
        use_redis: Whether to use Redis-backed limiter
        redis_url: Redis connection URL (if use_redis=True)
        
    Returns:
        RateLimiter or RedisRateLimiter instance
    """
    if use_redis:
        return RedisRateLimiter(
            redis_url=redis_url,
            requests_per_minute=requests_per_minute
        )
    else:
        return RateLimiter(requests_per_minute=requests_per_minute)
