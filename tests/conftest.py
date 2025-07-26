#!/usr/bin/env python3
"""
Pytest configuration for conversational DevOps AI tests
"""

import pytest
import pytest_asyncio
import asyncio
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Configure pytest-asyncio
pytest_plugins = ['pytest_asyncio']


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up test environment variables"""
    # Set test environment variables
    os.environ['POSTGRES_URL'] = 'postgresql://test:test@localhost:5432/test_db'
    os.environ['OPENAI_API_KEY'] = 'test_key'
    os.environ['DISCORD_TOKEN_DEVOPS'] = 'test_token'
    os.environ['DEFAULT_SERVER_ID'] = 'test_server'
    
    yield
    
    # Cleanup if needed
    pass


@pytest.fixture
def mock_env_vars():
    """Mock environment variables for testing"""
    return {
        'POSTGRES_URL': 'postgresql://test:test@localhost:5432/test_db',
        'OPENAI_API_KEY': 'test_openai_key',
        'DISCORD_TOKEN_DEVOPS': 'test_discord_token',
        'DISCORD_TOKEN_GROK4': 'test_grok_token',
        'DISCORD_TOKEN_CLAUDE': 'test_claude_token',
        'XAI_API_KEY': 'test_xai_key',
        'ANTHROPIC_API_KEY': 'test_anthropic_key',
        'DEFAULT_SERVER_ID': 'test_server_123'
    }


# Configure asyncio mode for pytest-asyncio
def pytest_configure(config):
    """Configure pytest with asyncio settings"""
    config.option.asyncio_mode = "auto"