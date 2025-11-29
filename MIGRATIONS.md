# Database Migrations

This document explains how to manage database schema changes using Alembic.

## Setup

Alembic is already configured. The configuration files are:
- `alembic.ini` - Alembic configuration
- `alembic/env.py` - Migration environment setup
- `alembic/versions/` - Migration scripts

## Running Migrations

### Apply all pending migrations

```bash
alembic upgrade head
```

### Rollback one migration

```bash
alembic downgrade -1
```

### Rollback to specific revision

```bash
alembic downgrade <revision_id>
```

### View current database version

```bash
alembic current
```

### View migration history

```bash
alembic history
```

## Creating New Migrations

### Auto-generate migration from model changes

```bash
alembic revision --autogenerate -m "Description of changes"
```

This will:
1. Compare current models with database schema
2. Generate a migration script in `alembic/versions/`
3. Include upgrade() and downgrade() functions

### Create empty migration

```bash
alembic revision -m "Description of changes"
```

Then manually edit the generated file to add your changes.

## Migration Best Practices

1. **Always review auto-generated migrations** - Alembic might not catch everything
2. **Test migrations on a copy of production data** before applying to production
3. **Write both upgrade() and downgrade()** functions
4. **Keep migrations small and focused** - one logical change per migration
5. **Never edit applied migrations** - create a new migration instead

## Production Deployment

### Initial Setup (First Time)

```bash
# 1. Create database
createdb lookuply

# 2. Apply all migrations
alembic upgrade head
```

### Updating Production

```bash
# 1. Pull latest code
git pull origin main

# 2. Apply new migrations
alembic upgrade head

# 3. Restart application
docker compose restart coordinator
```

## Current Migrations

### 001 - Initial migration (2025-11-29)
- Creates `urls` table with all columns
- Adds indexes on url, domain, status, priority
- Creates URLStatus enum type

## Troubleshooting

### "Target database is not up to date"

```bash
# Check current version
alembic current

# View pending migrations
alembic history

# Apply pending migrations
alembic upgrade head
```

### "Can't locate revision identified by '...'"

```bash
# Stamp database with current version
alembic stamp head
```

### Reset database (development only)

```bash
# Drop all tables
alembic downgrade base

# Recreate from scratch
alembic upgrade head
```

## Docker Compose Integration

Migrations are run automatically when the coordinator container starts:

```yaml
# In docker-compose.yml
coordinator:
  # ...
  command: >
    sh -c "alembic upgrade head &&
           uvicorn src.main:app --host 0.0.0.0 --port 8000"
```

## Further Reading

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
