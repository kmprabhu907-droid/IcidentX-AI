#!/usr/bin/env bash
# ==============================================================================
# INCIDENTX AI - Local & Pre-Commit DevSecOps Verification Script (Stage 6.8)
# Executes linting, AST security scan, TypeScript typecheck, and test suite.
# ==============================================================================

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

echo "=========================================================="
echo "🛡️  INCIDENTX AI - Automated DevSecOps Pipeline Verification"
echo "=========================================================="
echo "Project Root: $PROJECT_ROOT"
echo ""

# 1. Python Syntax & Compilation Verification
echo "[1/4] Verifying Python Syntax & AST Compilation..."
python3 -m compileall backend/ -q
echo "  ✓ Python backend compiled successfully without syntax errors."
echo ""

# 2. Frontend TypeScript Static Analysis
echo "[2/4] Verifying Frontend TypeScript Type Safety..."
if [ -d "frontend" ]; then
    (cd frontend && npx tsc --noEmit)
    echo "  ✓ Frontend TypeScript typechecked with 0 errors."
else
    echo "  ⚠️  Frontend directory not found, skipping."
fi
echo ""

# 3. Security AST Analysis (Bandit if installed)
echo "[3/4] Running Security Vulnerability Scans..."
if command -v bandit &> /dev/null; then
    bandit -c .bandit.yaml -r backend/ -ll -q
    echo "  ✓ Bandit security scan completed with 0 high-severity vulnerabilities."
else
    echo "  ℹ️  Bandit not installed in global path, skipping local static AST scan."
fi
echo ""

# 4. Automated Pytest Verification
echo "[4/4] Executing Full Pytest Suite..."
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi
PYTHONPATH=. pytest -q --maxfail=1

echo ""
echo "=========================================================="
echo "✅ ALL DEVSECOPS CHECKS PASSED — READY FOR PRODUCTION RELEASE"
echo "=========================================================="
