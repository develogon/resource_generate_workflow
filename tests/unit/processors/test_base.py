"""Base processor tests."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from dataclasses import dataclass
from typing import Dict, Any

from src.processors.base import (
    BaseProcessor, 
    ProcessorType, 
    ProcessingRequest, 
    ProcessingResult
)
from src.config import Config


class TestProcessorType:
    """ProcessorType enum tests."""
    
    def test_processor_type_values(self):
        """Test ProcessorType enum values."""
        assert ProcessorType.CONTENT.value == "content"
        assert ProcessorType.CHAPTER.value == "chapter"
        assert ProcessorType.SECTION.value == "section"
        assert ProcessorType.PARAGRAPH.value == "paragraph"
        assert ProcessorType.STRUCTURE.value == "structure"


class TestProcessingRequest:
    """ProcessingRequest dataclass tests."""
    
    def test_create_processing_request(self):
        """Test creating ProcessingRequest."""
        request = ProcessingRequest(
            content="test content",
            processor_type=ProcessorType.CONTENT,
            options={"test": True},
            context={"user": "test"}
        )
        
        assert request.content == "test content"
        assert request.processor_type == ProcessorType.CONTENT
        assert request.options["test"] is True
        assert request.context["user"] == "test"


class TestProcessingResult:
    """ProcessingResult dataclass tests."""
    
    def test_create_processing_result_success(self):
        """Test creating successful ProcessingResult."""
        result = ProcessingResult(
            content="processed content",
            metadata={"count": 1},
            processor_type=ProcessorType.CONTENT,
            success=True
        )
        
        assert result.content == "processed content"
        assert result.metadata["count"] == 1
        assert result.processor_type == ProcessorType.CONTENT
        assert result.success is True
        assert result.error is None
        
    def test_create_processing_result_failure(self):
        """Test creating failed ProcessingResult."""
        result = ProcessingResult(
            content="",
            metadata={},
            processor_type=ProcessorType.CONTENT,
            success=False,
            error="Test error"
        )
        
        assert result.content == ""
        assert result.metadata == {}
        assert result.success is False
        assert result.error == "Test error"


class MockProcessor(BaseProcessor):
    """Mock processor for testing."""
    
    def __init__(self, config: Config, should_fail: bool = False):
        super().__init__(config)
        self.should_fail = should_fail
        
    def get_processor_type(self) -> ProcessorType:
        return ProcessorType.CONTENT
        
    async def process(self, request: ProcessingRequest) -> ProcessingResult:
        if self.should_fail:
            raise ValueError("Mock processing error")
            
        return ProcessingResult(
            content=f"processed: {request.content}",
            metadata={"mock": True},
            processor_type=self.get_processor_type(),
            success=True
        )


class TestBaseProcessor:
    """BaseProcessor tests."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock config."""
        config = Mock(spec=Config)
        config.workers = Mock()
        config.workers.max_concurrent_tasks = 3
        return config
        
    @pytest.fixture
    def processor(self, mock_config):
        """Create mock processor."""
        return MockProcessor(mock_config)
        
    def test_processor_initialization(self, mock_config):
        """Test processor initialization."""
        processor = MockProcessor(mock_config)
        assert processor.config == mock_config
        assert processor.semaphore._value == 3
        
    def test_get_processor_type(self, processor):
        """Test get_processor_type method."""
        assert processor.get_processor_type() == ProcessorType.CONTENT
        
    @pytest.mark.asyncio
    async def test_process_success(self, processor):
        """Test successful processing."""
        request = ProcessingRequest(
            content="test",
            processor_type=ProcessorType.CONTENT,
            options={},
            context={}
        )
        
        result = await processor.process(request)
        
        assert result.success is True
        assert result.content == "processed: test"
        assert result.metadata["mock"] is True
        assert result.error is None
        
    @pytest.mark.asyncio
    async def test_safe_process_with_error(self, mock_config):
        """Test _safe_process with error handling."""
        processor = MockProcessor(mock_config, should_fail=True)
        request = ProcessingRequest(
            content="test",
            processor_type=ProcessorType.CONTENT,
            options={},
            context={}
        )
        
        result = await processor._safe_process(request)
        
        assert result.success is False
        assert result.error == "Mock processing error"
        assert result.content == "test"
        
    @pytest.mark.asyncio
    async def test_batch_process_success(self, processor):
        """Test successful batch processing."""
        requests = [
            ProcessingRequest(
                content=f"test{i}",
                processor_type=ProcessorType.CONTENT,
                options={},
                context={}
            )
            for i in range(3)
        ]
        
        results = await processor.batch_process(requests)
        
        assert len(results) == 3
        for i, result in enumerate(results):
            assert result.success is True
            assert result.content == f"processed: test{i}"
            
    @pytest.mark.asyncio
    async def test_batch_process_empty_list(self, processor):
        """Test batch processing with empty list."""
        results = await processor.batch_process([])
        assert results == []
        
    @pytest.mark.asyncio
    async def test_batch_process_with_errors(self, mock_config):
        """Test batch processing with some errors."""
        processor = MockProcessor(mock_config, should_fail=True)
        requests = [
            ProcessingRequest(
                content="test",
                processor_type=ProcessorType.CONTENT,
                options={},
                context={}
            )
        ]
        
        results = await processor.batch_process(requests)
        
        assert len(results) == 1
        assert results[0].success is False
        assert "Mock processing error" in results[0].error
        
    def test_validate_request_valid(self, processor):
        """Test request validation with valid request."""
        request = ProcessingRequest(
            content="test",
            processor_type=ProcessorType.CONTENT,
            options={},
            context={}
        )
        
        assert processor.validate_request(request) is True
        
    def test_validate_request_invalid_content(self, processor):
        """Test request validation with invalid content."""
        request = ProcessingRequest(
            content="",
            processor_type=ProcessorType.CONTENT,
            options={},
            context={}
        )
        
        assert processor.validate_request(request) is False
        
    def test_validate_request_wrong_type(self, processor):
        """Test request validation with wrong processor type."""
        request = ProcessingRequest(
            content="test",
            processor_type=ProcessorType.CHAPTER,  # Different type
            options={},
            context={}
        )
        
        assert processor.validate_request(request) is False
        
    def test_extract_metadata(self, processor):
        """Test metadata extraction."""
        request = ProcessingRequest(
            content="test",
            processor_type=ProcessorType.CONTENT,
            options={},
            context={}
        )
        
        result = "processed result"
        metadata = processor.extract_metadata(request, result)
        
        assert metadata["processor_type"] == "content"
        assert metadata["input_type"] == "str"
        assert metadata["output_type"] == "str"
        assert "processed_at" in metadata 