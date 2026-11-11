"""
INCIDENTX AI - Stage 6.8 CI/CD & Automated DevSecOps Tests
Verifies GitHub Actions CI workflow definitions, Bandit security configurations,
and local DevSecOps pipeline verification script.
"""

import compileall
import os
from pathlib import Path
import yaml


def test_github_actions_workflow_syntax():
    """Verify .github/workflows/ci.yml parses cleanly and defines standard enterprise jobs."""
    workflow_path = Path(".github/workflows/ci.yml")
    assert workflow_path.exists(), "CI workflow file .github/workflows/ci.yml must exist"

    with open(workflow_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert "jobs" in data
    jobs = data["jobs"]
    assert "backend-validation" in jobs
    assert "frontend-validation" in jobs
    assert "container-security-audit" in jobs

    # Triggers
    assert "on" in data
    triggers = data["on"]
    assert "push" in triggers
    assert "pull_request" in triggers


def test_bandit_config_syntax():
    """Verify .bandit.yaml configuration syntax and rule exclusions."""
    bandit_path = Path(".bandit.yaml")
    assert bandit_path.exists(), ".bandit.yaml must exist"

    with open(bandit_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    assert "exclude_dirs" in config
    assert "tests" in config["exclude_dirs"]
    assert "skips" in config
    assert "B101" in config["skips"]


def test_devsecops_check_script_is_executable():
    """Verify infrastructure/scripts/devsecops_check.sh exists and is executable."""
    script_path = Path("infrastructure/scripts/devsecops_check.sh")
    assert script_path.exists(), "devsecops_check.sh must exist"
    assert os.access(script_path, os.X_OK), "devsecops_check.sh must have executable bit set"


def test_python_syntax_and_ast_compilation():
    """Verify all Python modules in backend compile cleanly without syntax errors."""
    success = compileall.compile_dir("backend", quiet=1)
    assert success is True, "All backend Python files must compile cleanly"
