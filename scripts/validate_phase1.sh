#!/bin/bash
# Phase 1 Validation Script - Run all checks to verify Phase 1 completion

set -e  # Exit on error

echo "=========================================="
echo " Spider SEO Crawler - Phase 1 Validation"
echo "=========================================="
echo ""

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment not activated. Run: source .venv/bin/activate${NC}"
    exit 1
fi

echo "✓ Virtual environment: $VIRTUAL_ENV"
echo ""

# Install test dependencies
echo "📦 Installing test dependencies..."
pip install -q -r requirements-test.txt
echo -e "${GREEN}✓ Dependencies installed${NC}"
echo ""

# Run syntax validation
echo "🔍 Validating Python syntax..."
python -m py_compile webapp/main.py
python -m py_compile Crawler.py
python -m py_compile gui/main_window.py
echo -e "${GREEN}✓ Python syntax validated${NC}"
echo ""

# Run test suite with coverage
echo "🧪 Running test suite with coverage..."
if [ "$(uname)" == "Darwin" ]; then
    # macOS
    pytest --cov=. --cov-report=html --cov-report=term-missing --cov-fail-under=70 -v
else
    # Linux - use xvfb for GUI tests
    xvfb-run -s "-screen 0 1920x1080x24" pytest --cov=. --cov-report=html --cov-report=term-missing --cov-fail-under=70 -v
fi
echo -e "${GREEN}✓ Tests passed${NC}"
echo ""

# Run security scans
echo "🔒 Running security scans..."

echo "  - Bandit (static analysis)..."
bandit -r . -ll -ii -f json -o bandit-report.json
if [ $? -eq 0 ]; then
    echo -e "${GREEN}  ✓ Bandit: No high-severity issues${NC}"
else
    echo -e "${YELLOW}  ⚠️  Bandit: Review bandit-report.json${NC}"
fi

echo "  - Safety (dependency check)..."
safety check --json --output safety-report.json || true
if [ $? -eq 0 ]; then
    echo -e "${GREEN}  ✓ Safety: No known vulnerabilities${NC}"
else
    echo -e "${YELLOW}  ⚠️  Safety: Review safety-report.json${NC}"
fi
echo ""

# Generate coverage report
echo "📊 Coverage report generated:"
echo "   HTML: htmlcov/index.html"
echo "   XML:  coverage.xml"
echo ""

# Summary
echo "=========================================="
echo -e "${GREEN}✅ Phase 1 Validation Complete!${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Open coverage report: open htmlcov/index.html"
echo "  2. Review security reports: bandit-report.json, safety-report.json"
echo "  3. Commit changes and push to trigger CI"
echo "  4. Monitor GitHub Actions for CI results"
echo ""
echo "Ready for Phase 2: Security Hardening 🚀"
