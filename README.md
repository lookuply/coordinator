# Lookuply Coordinator

**URL Frontier & Task Queue for Decentralized Crawler Network**

## Overview

The Coordinator is the central orchestration component of Lookuply's decentralized crawler network. It manages the URL frontier, distributes crawling tasks to crawler nodes, and tracks crawling progress.

## Features

- **URL Frontier**: Manages queue of URLs to crawl
- **Task Distribution**: Celery-based task queue for crawler nodes
- **Node Management**: Register and track crawler nodes
- **Priority Queuing**: Prioritize important URLs
- **Duplicate Detection**: Prevent re-crawling URLs
- **Rate Limiting**: Respect robots.txt and crawl politeness

## Tech Stack

- **Python 3.13**
- **FastAPI**: REST API
- **PostgreSQL 16**: URL frontier storage
- **Celery**: Task queue
- **Redis**: Celery broker
- **Alembic**: Database migrations
- **Pydantic**: Data validation

## Quick Start

### Prerequisites

- Python 3.13+
- PostgreSQL 16+
- Redis 7+
- Docker (optional)

### Installation

```bash
# Clone repository
git clone https://github.com/lookuply/coordinator.git
cd coordinator

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Setup database
createdb lookuply
alembic upgrade head

# Create .env file
cp .env.example .env
# Edit .env with your configuration
```

### Running

```bash
# Start API server
uvicorn src.main:app --reload

# Start Celery worker (in another terminal)
celery -A src.celery worker --loglevel=info
```

### Testing

```bash
# Run tests
pytest

# Run tests with coverage
pytest --cov=src --cov-report=html

# Run linters
ruff check .
mypy src/
```

## Project Structure

```
coordinator/
├── src/
│   ├── __init__.py
│   ├── main.py              # FastAPI app
│   ├── celery.py            # Celery config
│   ├── config.py            # Configuration
│   ├── database.py          # Database connection
│   ├── models/              # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── url.py           # URL model
│   │   └── crawler_node.py  # Crawler node model
│   ├── schemas/             # Pydantic schemas
│   │   ├── __init__.py
│   │   ├── url.py
│   │   └── crawler_node.py
│   ├── api/                 # API routes
│   │   ├── __init__.py
│   │   ├── urls.py          # URL endpoints
│   │   └── nodes.py         # Node endpoints
│   ├── services/            # Business logic
│   │   ├── __init__.py
│   │   ├── frontier.py      # URL frontier service
│   │   └── scheduler.py     # Task scheduler
│   └── tasks/               # Celery tasks
│       ├── __init__.py
│       └── crawl.py         # Crawl tasks
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Pytest fixtures
│   ├── test_api/
│   ├── test_services/
│   └── test_tasks/
├── alembic/                 # Database migrations
├── .github/
│   └── workflows/           # CI/CD workflows
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
├── .env.example
└── README.md
```

## API Endpoints

### URL Frontier

```http
POST   /api/v1/urls              # Add URLs to frontier
GET    /api/v1/urls              # Get URLs to crawl
GET    /api/v1/urls/{url_id}     # Get URL status
DELETE /api/v1/urls/{url_id}     # Remove URL
```

### Crawler Nodes

```http
POST   /api/v1/nodes             # Register crawler node
GET    /api/v1/nodes             # List crawler nodes
GET    /api/v1/nodes/{node_id}   # Get node status
DELETE /api/v1/nodes/{node_id}   # Unregister node
```

### Tasks

```http
GET    /api/v1/tasks/next        # Get next crawl task
POST   /api/v1/tasks/{task_id}/complete  # Mark task complete
POST   /api/v1/tasks/{task_id}/fail      # Mark task failed
```

## Development

### Test-Driven Development (TDD)

This project follows strict TDD:

1. **Red**: Write failing test first
2. **Green**: Write minimal code to pass
3. **Refactor**: Improve code while keeping tests green

**Coverage requirement**: >80% (enforced in CI)

### SOLID Principles

- **Single Responsibility**: Each class has one responsibility
- **Open/Closed**: Open for extension, closed for modification
- **Liskov Substitution**: Subtypes must be substitutable
- **Interface Segregation**: Small, focused interfaces
- **Dependency Inversion**: Depend on abstractions

### Git Workflow

```bash
# Create feature branch
git checkout -b feature/url-frontier

# Make changes, write tests first!
# ... TDD cycle ...

# Commit with conventional commits
git commit -m "feat: implement URL frontier service"

# Push and create PR
git push origin feature/url-frontier
gh pr create --title "feat: URL frontier service"
```

### Conventional Commits

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `test:` Tests
- `refactor:` Code refactoring
- `perf:` Performance improvement
- `chore:` Maintenance

## Deployment

### Docker

```bash
# Build image
docker build -t lookuply/coordinator .

# Run container
docker run -p 8000:8000 lookuply/coordinator
```

### Docker Compose

```bash
# Start all services (from infrastructure repo)
cd ../infrastructure
docker compose up -d coordinator
```

### Production

Deployed via GitHub Actions to Hetzner server:

```bash
# Automatic deployment on push to main
git push origin main
```

See [deployment guide](https://github.com/lookuply/project-docs/blob/master/guides/deployment.md).

## Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/lookuply

# Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# API
API_HOST=0.0.0.0
API_PORT=8000
API_SECRET_KEY=your-secret-key

# Crawling
MAX_URLS_PER_NODE=10
CRAWL_DELAY_SECONDS=1
RESPECT_ROBOTS_TXT=true
```

## Architecture

See [ARCHITECTURE.md](https://github.com/lookuply/project-docs/blob/master/ARCHITECTURE.md).

## Contributing

See [CONTRIBUTING.md](https://github.com/lookuply/project-docs/blob/master/guides/contributing.md).

## License

MIT License - see [LICENSE](LICENSE)

## Contact

- **Email**: hello@lookuply.info
- **Docs**: https://github.com/lookuply/project-docs
- **Website**: https://lookuply.info

---

**Privacy-First | Decentralized | Open-Source**
# Trigger deployment
