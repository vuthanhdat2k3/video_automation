#!/usr/bin/env bash
set -euo pipefail

echo "=== AI 2D Animation Studio — Dev Setup ==="

# Start infrastructure
echo "Starting PostgreSQL and Redis..."
docker compose -f infra/docker-compose.yml up -d
echo "Waiting for services to be ready..."
sleep 3

# Install API dependencies
echo "Installing API dependencies..."
cd apps/api
pip install -e ".[dev]" -q
cd ../..

# Install shared package
echo "Installing shared package..."
pip install -e packages/shared -q

# Run migrations
echo "Running database migrations..."
cd apps/api
alembic upgrade head
cd ../..

# Seed demo project
echo "Seeding demo project..."
python scripts/seed_demo_project.py

echo "=== Setup complete! ==="
echo "Run: uvicorn apps.api.app.main:app --reload --port 8000"
