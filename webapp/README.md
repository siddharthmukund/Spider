# FastAPI Web API for SEO Crawler

A production-ready FastAPI web service with comprehensive security features including authentication, SSRF protection, rate limiting, and audit logging.

## Quick Start

### 1. Install Dependencies

```bash
# Activate project venv
source .venv/bin/activate

# Install webapp dependencies
pip install -r webapp/requirements.txt
```

### 2. Configure Security (Required)

```bash
# Generate a secure API key
export WEBAPP_API_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

# Save it for future use
echo "Your API key: $WEBAPP_API_KEY"
```

### 3. Start Server

```bash
uvicorn webapp.main:app --reload --host 127.0.0.1 --port 8000
```

### 4. Make Authenticated Requests

```bash
# Start a crawl
curl -X POST "http://127.0.0.1:8000/start" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $WEBAPP_API_KEY" \
  -d '{"base_url": "https://example.com", "max_pages": 10}'

# Get task status
curl "http://127.0.0.1:8000/status/{task_id}" \
  -H "X-API-Key: $WEBAPP_API_KEY"

# Watch events (SSE)
curl -N "http://127.0.0.1:8000/events/{task_id}" \
  -H "X-API-Key: $WEBAPP_API_KEY"
```

## Security Features (Phase 2)

### ✅ Authentication
- **Required**: All endpoints (except `/health`) require `X-API-Key` header
- **Algorithm**: Constant-time comparison to prevent timing attacks
- **Configuration**: Set `WEBAPP_API_KEY` environment variable

### ✅ SSRF Protection
- Blocks localhost, private IPs, cloud metadata endpoints
- DNS resolution to catch domain-to-IP tricks
- Only HTTP/HTTPS schemes allowed

### ✅ Rate Limiting
- **Default**: 60 requests per minute per client IP
- **Algorithm**: Token bucket with smooth refill
- **Distributed**: Supports Redis for multi-instance deployments

### ✅ Audit Logging
- All security events logged to `webapp/data/audit.log`
- Structured JSON format for easy parsing
- Events: auth success/failure, SSRF blocks, rate limits, crawl lifecycle

## Environment Variables

```bash
# Required
WEBAPP_API_KEY=your-secure-key-here          # Generate with secrets.token_urlsafe(32)

# Optional - Rate Limiting
RATE_LIMIT_MAX=60                            # Requests per minute (default: 60)
RATE_LIMIT_WINDOW=60                         # Time window in seconds (default: 60)

# Optional - Distributed Mode
REDIS_URL=redis://localhost:6379/0           # Enable Redis-backed rate limiting
USE_CELERY=1                                 # Enable Celery distributed tasks

# Optional - Task Persistence
AUTO_RESUME=1                                # Auto-resume tasks on restart (default: 1)
```

## API Endpoints

### Public Endpoints (No Auth Required)
- `GET /` - API documentation redirect
- `GET /health` - Health check

### Protected Endpoints (Require X-API-Key Header)
- `POST /start` - Start a new crawl task
  - Body: `{"base_url": "https://example.com", "max_pages": 10, "max_workers": 2}`
  - Returns: `{"task_id": "abc123", ...}`
  
- `GET /status/{task_id}` - Get task status
  - Returns: `{"id": "abc123", "status": "running", ...}`
  
- `GET /events/{task_id}` - Server-Sent Events stream
  - Returns: Real-time event stream
  
- `GET /report/{task_id}` - Download JSON report
  - Returns: Complete SEO report (when task finished)
  
- `GET /ws/{task_id}` - WebSocket connection
  - Returns: Real-time updates via WebSocket

## Docker Deployment

### Docker Compose (Recommended for Local Testing)

```bash
# Start all services (web, redis, celery)
docker-compose up --build

# Set API key in docker-compose.yml environment section
```

### Docker Image Publishing

Images are automatically published to GitHub Container Registry (GHCR) on:
- Version tag pushes (e.g., `v1.2.3`)
- Published releases

```bash
# Pull latest image
docker pull ghcr.io/yourusername/seocrawler:latest

# Run with environment variables
docker run -e WEBAPP_API_KEY=your-key ghcr.io/yourusername/seocrawler:latest
```

## Celery Distributed Mode

For high-throughput deployments:

```bash
# Install Celery dependencies
pip install -r webapp/requirements.txt

# Set environment variables
export REDIS_URL=redis://localhost:6379/0
export USE_CELERY=1
export WEBAPP_API_KEY=your-secure-key

# Start Celery worker
celery -A webapp.tasks worker --loglevel=info

# Start web server
uvicorn webapp.main:app --host 0.0.0.0 --port 8000
```

## Task Persistence

Tasks and events are persisted to disk:
- **Tasks**: `webapp/data/tasks.json` - Task metadata
- **Events**: `webapp/data/<task_id>/events.log` - Event logs
- **Audit**: `webapp/data/audit.log` - Security audit log

Tasks survive server restarts when `AUTO_RESUME=1` (default).

## Security Best Practices

### API Key Management
1. Never commit keys to version control
2. Use different keys per environment (dev, staging, prod)
3. Rotate keys quarterly
4. Store in secrets manager (AWS Secrets Manager, HashiCorp Vault)

### Rate Limiting Tuning
- **API Gateway**: 100-1000 requests/minute
- **Individual Users**: 10-60 requests/minute
- **Batch Jobs**: Unlimited (use service account)

### Audit Log Retention
- **Development**: 7 days
- **Production**: 90-365 days (compliance-dependent)
- Use log rotation (logrotate, CloudWatch Logs)

## Troubleshooting

### 401 Unauthorized
```bash
# Ensure API key is set
echo $WEBAPP_API_KEY

# Generate new key if missing
export WEBAPP_API_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
```

### 429 Rate Limited
```bash
# Increase rate limit
export RATE_LIMIT_MAX=120

# Or wait for tokens to refill (1 per second by default)
```

### 400 SSRF Blocked
```bash
# Ensure URL is public (not localhost/private IP)
# Valid: https://example.com
# Invalid: http://localhost, http://192.168.1.1
```

## CI/CD Integration

GitHub Actions includes:
1. **Unit Tests**: `pytest tests/`
2. **Integration Tests**: Redis + Celery worker
3. **Docker Build**: Multi-stage build with security scanning
4. **Image Publishing**: GHCR on tags and releases

```yaml
# .github/workflows/ci.yml
env:
  WEBAPP_API_KEY: ${{ secrets.WEBAPP_API_KEY }}
  REDIS_URL: redis://localhost:6379/0
```

## Documentation

- **Phase 2 Security**: [docs/PHASE2_COMPLETION.md](../docs/PHASE2_COMPLETION.md)
- **Release Signing**: [docs/release_signing.md](../docs/release_signing.md)
- **DMG Creation**: [docs/release_dmg.md](../docs/release_dmg.md)

## Support

For issues or questions:
1. Check audit logs: `tail -f webapp/data/audit.log`
2. Review security documentation: [PHASE2_COMPLETION.md](../docs/PHASE2_COMPLETION.md)
3. Run tests: `pytest tests/ -v`
