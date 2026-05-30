"""
Shared pytest configuration.
Each test file uses its own isolated SQLite DB to avoid conflicts.
"""
import pytest


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "integration: mark test as integration test")


def pytest_collection_modifyitems(config, items):
    """Auto-mark integration test classes."""
    for item in items:
        if "integration" in item.nodeid.lower():
            item.add_marker(pytest.mark.integration)
