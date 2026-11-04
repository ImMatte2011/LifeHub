#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "=== LifeHub Init ==="

if [ ! -f .env ]; then
  cp .env.example .env
  echo ""
  echo "  Created .env from .env.example."
  echo "  → Edit .env and set POSTGRES_PASSWORD, SECRET_KEY, ADMIN_PASSWORD."
  echo "  → Then run this script again."
  echo ""
  exit 0
fi

echo "Building and starting services..."
docker compose up -d --build

echo ""
echo "  LifeHub is starting up."
echo ""
echo "  Frontend : http://localhost:${FRONTEND_PORT:-3000}"
echo "  Backend  : http://localhost:${BACKEND_PORT:-8000}"
echo "  API docs : http://localhost:${BACKEND_PORT:-8000}/api/docs"
echo ""
echo "  Logs: docker compose logs -f"
