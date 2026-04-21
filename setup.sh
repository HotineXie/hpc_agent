#!/usr/bin/env bash
# HPC Agent — one-time setup script
# Usage: bash setup.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== HPC Agent Setup ==="
echo ""

# ── Backend ───────────────────────────────────────────────────────────────────
echo "[1/4] Installing backend dependencies..."
cd "$SCRIPT_DIR/backend"
if command -v uv &>/dev/null; then
  uv pip install -e .
else
  pip install -e .
fi
if [ ! -f .env ]; then
  cp .env.example .env
  echo "      Created backend/.env — please fill in GLOBUS_COMPUTE_TOKEN if needed"
fi
cd "$SCRIPT_DIR"

# ── Runner setup ──────────────────────────────────────────────────────────────
echo "[2/4] Preparing runner..."
cd "$SCRIPT_DIR/runner"
node scripts/setup.js

echo "[3/4] Installing runner dependencies..."
npm install

if [ ! -f .env ]; then
  cp .env.example .env
  echo "      Created runner/.env — please fill in ANTHROPIC_API_KEY"
fi

echo "[4/4] Installing monitor dependencies..."
if [ -d monitor ]; then
  cd monitor && npm install && cd ..
fi

cd "$SCRIPT_DIR"

# ── Root .env ─────────────────────────────────────────────────────────────────
if [ ! -f .env ]; then
  cp .env.example .env
  echo "      Created .env"
fi

echo ""
echo "=== Setup complete! ==="
echo ""
echo "To start:"
echo "  Terminal 1: cd backend && python run.py"
echo "  Terminal 2: cd runner && npm start"
echo "  Terminal 3: cd runner && npm run monitor"
echo ""
echo "Then open http://localhost:5173"
echo ""
echo "IMPORTANT: Edit .env files and add your API keys before starting."
