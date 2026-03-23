#!/bin/bash
# setup_notion_pipeline.sh — Install dependencies for notion_ingestion.py on Mac
# Run once before first ingestion.

set -e
echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  Notion Ingestion Pipeline Setup (Mac)       ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

cd "$(dirname "$0")/.."

# Python deps
echo "[1/2] Installing Python packages..."
pip3 install anthropic supabase playwright Pillow python-dotenv

# Playwright browser
echo ""
echo "[2/2] Installing headless Chromium for Playwright..."
playwright install chromium

echo ""
echo "✅ Setup complete! Run:"
echo "   python scripts/notion_ingestion.py --dry-run --limit 3"
echo "   python scripts/notion_ingestion.py --resume"
echo ""
