"""Test suite for security modules."""
import pytest
from webapp.security.ssrf import SSRFValidator
from webapp.security.rate_limit import RateLimiter, TokenBucket
from webapp.security.audit import AuditLogger, AuditEvent
import time
import tempfile
import os


class TestSSRFValidator:
    """Tests for SSRF protection validator."""

    def test_valid_https_url_accepted(self):
        """Test that valid HTTPS URLs are accepted."""
        is_valid, error = SSRFValidator.validate("https://example.com")
        assert is_valid
        assert error == ""

    def test_valid_http_url_accepted(self):
        """Test that valid HTTP URLs are accepted."""
        is_valid, error = SSRFValidator.validate("http://example.com")
        assert is_valid
        assert error == ""

    def test_localhost_blocked(self):
        """Test that localhost is blocked."""
        is_valid, error = SSRFValidator.validate("http://localhost/")
        assert not is_valid
        assert "blocked" in error.lower()

    def test_127_0_0_1_blocked(self):
        """Test that 127.0.0.1 is blocked."""
        is_valid, error = SSRFValidator.validate("http://127.0.0.1/")
        assert not is_valid
        assert "blocked" in error.lower()

    def test_private_ip_10_blocked(self):
        """Test that 10.x.x.x addresses are blocked."""
        is_valid, error = SSRFValidator.validate("http://10.0.0.1/")
        assert not is_valid
        assert "blocked" in error.lower()

    def test_private_ip_192_168_blocked(self):
        """Test that 192.168.x.x addresses are blocked."""
        is_valid, error = SSRFValidator.validate("http://192.168.1.1/")
        assert not is_valid
        assert "blocked" in error.lower()

    def test_metadata_endpoint_blocked(self):
        """Test that AWS/GCP metadata endpoint is blocked."""
        is_valid, error = SSRFValidator.validate("http://169.254.169.254/")
        assert not is_valid
        assert "blocked" in error.lower()

    def test_ftp_scheme_rejected(self):
        """Test that non-HTTP schemes are rejected."""
        is_valid, error = SSRFValidator.validate("ftp://example.com")
        assert not is_valid
        assert "scheme" in error.lower()

    def test_file_scheme_rejected(self):
        """Test that file:// scheme is rejected."""
        is_valid, error = SSRFValidator.validate("file:///etc/passwd")
        assert not is_valid
        assert "scheme" in error.lower()

    def test_url_without_hostname_rejected(self):
        """Test that URL without hostname is rejected."""
        is_valid, error = SSRFValidator.validate("http://")
        assert not is_valid

    def test_ipv6_loopback_blocked(self):
        """Test that IPv6 loopback is blocked."""
        is_valid, error = SSRFValidator.validate("http://[::1]/")
        assert not is_valid
        assert "blocked" in error.lower()


class TestTokenBucket:
    """Tests for token bucket rate limiter."""

    def test_initial_tokens_available(self):
        """Test that bucket starts with full capacity."""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        assert bucket.consume(5)
        assert bucket.consume(5)

    def test_refill_over_time(self):
        """Test that tokens refill over time."""
        bucket = TokenBucket(capacity=10, refill_rate=10.0)  # 10 tokens/sec
        
        # Consume all tokens
        assert bucket.consume(10)
        
        # Should fail immediately
        assert not bucket.consume(1)
        
        # Wait and tokens should refill
        time.sleep(0.2)  # 0.2s = 2 tokens at 10/sec
        assert bucket.consume(2)

    def test_cannot_exceed_capacity(self):
        """Test that tokens don't exceed capacity."""
        bucket = TokenBucket(capacity=5, refill_rate=10.0)
        
        # Wait for potential refill
        time.sleep(1.0)
        
        # Should only have capacity worth
        assert bucket.consume(5)
        assert not bucket.consume(1)

    def test_wait_time_calculation(self):
        """Test that wait time is calculated correctly."""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)  # 1 token/sec
        
        # Consume all tokens
        bucket.consume(10)
        
        # Need 5 tokens -> should wait ~5 seconds
        wait = bucket.get_wait_time(5)
        assert 4.5 <= wait <= 5.5


class TestRateLimiter:
    """Tests for rate limiter."""

    def test_allows_requests_under_limit(self):
        """Test that requests under limit are allowed."""
        limiter = RateLimiter(requests_per_minute=60)
        
        # Should allow 60 requests
        for _ in range(60):
            assert limiter.check("client1")

    def test_blocks_requests_over_limit(self):
        """Test that requests over limit are blocked."""
        limiter = RateLimiter(requests_per_minute=10)
        
        # Use up all tokens
        for _ in range(10):
            assert limiter.check("client1")
        
        # Next request should be blocked
        assert not limiter.check("client1")

    def test_separate_clients_independent(self):
        """Test that different clients have independent limits."""
        limiter = RateLimiter(requests_per_minute=10)
        
        # Client 1 uses all tokens
        for _ in range(10):
            assert limiter.check("client1")
        
        # Client 2 should still have tokens
        assert limiter.check("client2")

    def test_refill_allows_more_requests(self):
        """Test that tokens refill over time."""
        limiter = RateLimiter(requests_per_minute=60)  # 1 per second
        
        # Use 5 tokens
        for _ in range(5):
            assert limiter.check("client1")
        
        # Wait for refill
        time.sleep(1.5)  # Should refill ~1.5 tokens
        
        # Should allow at least 1 more request
        assert limiter.check("client1")

    def test_geo_aware_limits(self):
        """Geo rules override default limits based on client IP."""
        # set environment variable with geo rules
        os.environ['RATE_LIMIT_GEO'] = '{"US": {"rpm": 2, "burst": 2}, "DEFAULT": {"rpm": 1, "burst": 1}}'
        limiter = RateLimiter(requests_per_minute=60)
        # IP in US range
        for _ in range(2):
            assert limiter.check("user", client_ip="192.0.2.5")
        assert not limiter.check("user", client_ip="192.0.2.5")
        # IP outside rules uses default
        assert limiter.check("foo", client_ip="8.8.8.8")
        assert not limiter.check("foo", client_ip="8.8.8.8")
        # clean up
        del os.environ['RATE_LIMIT_GEO']

    def test_tier_based_limits(self):
        """Tier rules change rate based on user scopes."""
        os.environ['RATE_LIMIT_TIERS'] = '{"premium": {"rpm": 3, "burst": 3}, "*": {"rpm": 1, "burst": 1}}'
        limiter = RateLimiter(requests_per_minute=60)
        # premium scope should allow 3
        for _ in range(3):
            assert limiter.check("alice", user_scopes=["premium"])
        assert not limiter.check("alice", user_scopes=["premium"])
        # default scope
        assert limiter.check("bob", user_scopes=["basic"])
        assert not limiter.check("bob", user_scopes=["basic"])
        del os.environ['RATE_LIMIT_TIERS']


class TestAuditLogger:
    """Tests for audit logging."""

    def test_logger_creates_file(self):
        """Test that logger creates log file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test_audit.log")
            logger = AuditLogger(log_file=log_file)
            
            logger.log(
                AuditEvent.AUTH_SUCCESS,
                client_ip="127.0.0.1",
                user_id="test_user"
            )
            
            assert os.path.exists(log_file)

    def test_log_format_is_json(self):
        """Test that logs are in JSON format."""
        import json
        
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test_audit.log")
            logger = AuditLogger(log_file=log_file)
            
            logger.log(
                AuditEvent.CRAWL_START,
                client_ip="1.2.3.4",
                details={"task_id": "test-123"}
            )
            
            with open(log_file, 'r') as f:
                line = f.readline()
                data = json.loads(line)
                
                assert data["event"] == AuditEvent.CRAWL_START.value
                assert data["client_ip"] == "1.2.3.4"
                assert "timestamp" in data

    def test_helper_methods(self):
        """Test that helper methods work correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test_audit.log")
            logger = AuditLogger(log_file=log_file)
            
            logger.log_auth_success("1.2.3.4", "user1")
            logger.log_auth_failure("5.6.7.8", "Invalid key")
            logger.log_crawl_start("1.2.3.4", "task-1", "https://example.com")
            
            # Should have 3 log entries
            with open(log_file, 'r') as f:
                lines = f.readlines()
                assert len(lines) == 3

    def test_get_recent_events(self):
        """Test retrieving recent events from log."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test_audit.log")
            logger = AuditLogger(log_file=log_file)
            
            # Log multiple events
            for i in range(5):
                logger.log(
                    AuditEvent.AUTH_SUCCESS,
                    client_ip=f"1.2.3.{i}",
                    user_id=f"user{i}"
                )
            
            # Retrieve recent events
            events = logger.get_recent_events(count=3)
            assert len(events) == 3
            
            # Should be in reverse order (most recent first)
            assert events[0]["client_ip"] == "1.2.3.4"

    def test_filter_by_event_type(self):
        """Test filtering events by type."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test_audit.log")
            logger = AuditLogger(log_file=log_file)
            
            logger.log_auth_success("1.2.3.4")
            logger.log_auth_failure("1.2.3.5")
            logger.log_auth_success("1.2.3.6")
            
            # Filter only success events
            events = logger.get_recent_events(
                count=10,
                event_type=AuditEvent.AUTH_SUCCESS
            )
            
            assert len(events) == 2
            assert all(e["event"] == AuditEvent.AUTH_SUCCESS.value for e in events)

