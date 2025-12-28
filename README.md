# Webhook FastAPI Service

Production-style FastAPI service with:
- WhatsApp-like message ingestion (exactly-once semantics)
- HMAC-SHA256 signature validation
- Health probes (liveness/readiness)
- Paginated/filterable messages endpoint
- Prometheus metrics
- Analytical stats endpoint
- 12-factor environment configuration
- Structured JSON logging
- Docker Compose deployment with SQLite

## Quick Start

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL=sqlite:///./app.db
export WEBHOOK_SECRET=your-secret-key

# Run the app
uvicorn app.main:app --reload
```

### Docker Compose

```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

## API Endpoints

- **POST /webhook** - Ingest messages with HMAC validation
- **GET /messages** - Paginated/filterable message retrieval
- **GET /stats** - Analytical statistics
- **GET /health/live** - Liveness probe
- **GET /health/ready** - Readiness probe
- **GET /metrics** - Prometheus metrics

## Testing

```bash
pytest tests/ -v
```

## Configuration

Set via environment variables:
- `DATABASE_URL` - SQLite connection string (required)
- `WEBHOOK_SECRET` - HMAC secret key (required for webhook validation)
- `LOG_LEVEL` - Logging level (default: INFO)
