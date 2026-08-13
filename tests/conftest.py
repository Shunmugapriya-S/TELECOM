"""
Pytest configuration and shared fixtures for RAG Engine tests
"""
import os
import sys
from pathlib import Path

import pytest

# Setup rag_engine package namespace dynamically
import sys
from pathlib import Path
from types import ModuleType

if "rag_engine" not in sys.modules:
    root_dir = Path(__file__).resolve().parent
    while root_dir.parent != root_dir and not (root_dir / "requirements.txt").exists():
        root_dir = root_dir.parent
    m = ModuleType("rag_engine")
    m.__path__ = [str(root_dir)]
    sys.modules["rag_engine"] = m

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "asyncio: mark test as async test")


@pytest.fixture
def project_root():
    """Return project root directory"""
    return PROJECT_ROOT


@pytest.fixture
def test_data_dir():
    """Return test data directory"""
    data_dir = PROJECT_ROOT / "tests" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


@pytest.fixture
def sample_text():
    """Return sample text for testing"""
    return """
    Artificial Intelligence (AI) is transforming industries worldwide.
    Machine Learning models can now process vast amounts of data efficiently.
    RAG systems combine retrieval and generation for better accuracy.
    """


@pytest.fixture
def sample_documents():
    """Return sample documents for testing"""
    return [
        {"id": "doc1", "text": "Python is a popular programming language"},
        {"id": "doc2", "text": "Machine learning requires large datasets"},
        {"id": "doc3", "text": "Vector databases store embeddings efficiently"},
    ]
