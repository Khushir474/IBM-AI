"""Pytest configuration and shared fixtures."""

import os
import sys
from pathlib import Path

# Add src directory to path so imports work
sys.path.insert(0, str(Path(__file__).parent))

# Set up test environment variables
os.environ.setdefault("CASSANDRA_HOST", "localhost")
os.environ.setdefault("CASSANDRA_PORT", "9042")
os.environ.setdefault("WXD_HOST", "localhost")
os.environ.setdefault("PRESTO_HOST", "localhost")
os.environ.setdefault("PRESTO_PORT", "8080")
os.environ.setdefault("WORKSHOP_USER", "test-user")
os.environ.setdefault("WORKSHOP_PASSWORD", "test-password")
os.environ.setdefault("WORKSHOP_SCHEMA_SUFFIX", "test")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("DEBUG", "false")


import pytest


@pytest.fixture(scope="session")
def test_env():
    """Provide test environment variables."""
    return {
        "CASSANDRA_HOST": "localhost",
        "PRESTO_HOST": "localhost",
        "WXD_HOST": "localhost",
        "WORKSHOP_USER": "test",
        "WORKSHOP_PASSWORD": "test",
        "WORKSHOP_SCHEMA_SUFFIX": "test",
    }
