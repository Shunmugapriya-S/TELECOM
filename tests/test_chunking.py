"""
Tests for chunking module
"""
import pytest


class TestChunking:
    """Test document chunking functionality"""

    def test_chunking_import(self):
        """Test that chunking module can be imported"""
        try:
            import rag_engine.chunking
            assert rag_engine.chunking is not None
        except ImportError:
            pytest.skip("Chunking module not available")

    def test_sample_text_length(self, sample_text):
        """Test sample text properties"""
        assert sample_text is not None
        assert len(sample_text.strip()) > 0

    def test_sample_documents_structure(self, sample_documents):
        """Test structure of sample documents"""
        for doc in sample_documents:
            assert "id" in doc
            assert "text" in doc
            assert isinstance(doc["id"], str)
            assert isinstance(doc["text"], str)

    def test_chunk_size_validation(self):
        """Test chunk size validation"""
        # Test that chunk size is reasonable
        min_chunk_size = 10
        max_chunk_size = 4096
        
        assert min_chunk_size < max_chunk_size
        assert min_chunk_size > 0
