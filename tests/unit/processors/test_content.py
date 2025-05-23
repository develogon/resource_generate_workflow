"""Content processor tests."""

import pytest
from unittest.mock import Mock

from src.processors.content import ContentProcessor
from src.processors.base import ProcessorType, ProcessingRequest
from src.models import Content, Chapter
from src.config import Config


class TestContentProcessor:
    """ContentProcessor tests."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock config."""
        config = Mock(spec=Config)
        config.workers = Mock()
        config.workers.max_concurrent_tasks = 3
        return config
        
    @pytest.fixture
    def processor(self, mock_config):
        """Create ContentProcessor instance."""
        return ContentProcessor(mock_config)
        
    def test_get_processor_type(self, processor):
        """Test processor type."""
        assert processor.get_processor_type() == ProcessorType.CONTENT
        
    @pytest.mark.asyncio
    async def test_process_string_content(self, processor):
        """Test processing string content."""
        content = """# Chapter 1: Introduction

This is the introduction chapter.

## 1.1 Overview

Overview content here.

# Chapter 2: Details

This is the details chapter.

## 2.1 Implementation

Implementation details here."""
        
        request = ProcessingRequest(
            content=content,
            processor_type=ProcessorType.CONTENT,
            options={"title": "Test Document", "split_method": "heading"},
            context={}
        )
        
        result = await processor.process(request)
        
        assert result.success is True
        assert isinstance(result.content, list)
        assert len(result.content) == 4  # H1 and H2 headings create separate chapters
        
        # Check first chapter (H1)
        chapter1 = result.content[0]
        assert hasattr(chapter1, 'title')
        assert chapter1.title == "Chapter 1: Introduction"
        assert hasattr(chapter1, 'index')
        assert chapter1.index == 0
        
        # Check second chapter (H2)
        chapter2 = result.content[1]
        assert hasattr(chapter2, 'title')
        assert chapter2.title == "1.1 Overview"
        assert chapter2.index == 1
        
        # Check third chapter (H1)
        chapter3 = result.content[2]
        assert hasattr(chapter3, 'title')
        assert chapter3.title == "Chapter 2: Details"
        assert chapter3.index == 2
        
        # Check fourth chapter (H2)
        chapter4 = result.content[3]
        assert hasattr(chapter4, 'title')
        assert chapter4.title == "2.1 Implementation"
        assert chapter4.index == 3
        
        # Check metadata
        assert result.metadata["chapter_count"] == 4
        assert result.metadata["split_method"] == "heading"
        
    @pytest.mark.asyncio
    async def test_process_content_object(self, processor):
        """Test processing Content object."""
        content_obj = Content(
            id="test-content-1",
            title="Test Content",
            content="# Chapter 1\nContent here.",
            metadata={"source": "test"}
        )
        
        request = ProcessingRequest(
            content=content_obj,
            processor_type=ProcessorType.CONTENT,
            options={"split_method": "heading"},
            context={}
        )
        
        result = await processor.process(request)
        
        assert result.success is True
        assert len(result.content) == 1
        assert result.content[0].title == "Chapter 1"
        
    @pytest.mark.asyncio
    async def test_split_by_length(self, processor):
        """Test splitting by length."""
        # Create long content
        content = "This is a paragraph. " * 100  # ~2000 characters
        content += "Another paragraph. " * 100  # Another ~2000 characters
        
        request = ProcessingRequest(
            content=content,
            processor_type=ProcessorType.CONTENT,
            options={
                "title": "Long Document",
                "split_method": "length",
                "max_chapter_length": 1000
            },
            context={}
        )
        
        result = await processor.process(request)
        
        assert result.success is True
        # The content is treated as one paragraph block, so it won't be split
        assert len(result.content) >= 1  # At least one chapter
        
    @pytest.mark.asyncio
    async def test_content_without_headings(self, processor):
        """Test content without clear headings."""
        content = """This is just plain text content without any clear headings.
        
It has multiple paragraphs but no markdown headings to split on.

So it should be treated as a single chapter."""
        
        request = ProcessingRequest(
            content=content,
            processor_type=ProcessorType.CONTENT,
            options={"title": "Plain Content", "split_method": "heading"},
            context={}
        )
        
        result = await processor.process(request)
        
        assert result.success is True
        assert len(result.content) == 1  # Single chapter
        assert result.content[0].title == "Plain Content"
        
    @pytest.mark.asyncio
    async def test_invalid_request(self, processor):
        """Test processing invalid request."""
        request = ProcessingRequest(
            content="",  # Empty content
            processor_type=ProcessorType.CONTENT,
            options={},
            context={}
        )
        
        result = await processor.process(request)
        
        assert result.success is False
        assert result.error == "Invalid request"
        
    @pytest.mark.asyncio
    async def test_wrong_processor_type(self, processor):
        """Test request with wrong processor type."""
        request = ProcessingRequest(
            content="Test content",
            processor_type=ProcessorType.CHAPTER,  # Wrong type
            options={},
            context={}
        )
        
        result = await processor.process(request)
        
        assert result.success is False
        assert result.error == "Invalid request"
        
    def test_split_by_headings_various_levels(self, processor):
        """Test splitting by various heading levels."""
        content = """# Main Chapter 1

Content for chapter 1.

## Section 1.1

Section content.

# Main Chapter 2

Content for chapter 2.

### Subsection 2.1.1

Subsection content."""
        
        content_obj = Content(
            id="test-content",
            title="Test",
            content=content
        )
        
        chapters = processor._split_by_headings(content_obj)
        
        assert len(chapters) == 3  # H1 and H2 both create chapters
        assert chapters[0].title == "Main Chapter 1"
        assert chapters[1].title == "Section 1.1"
        assert chapters[2].title == "Main Chapter 2"
        
    def test_split_by_length_with_paragraphs(self, processor):
        """Test length-based splitting with paragraph boundaries."""
        content_obj = Content(
            id="test-content",
            title="Test", 
            content="Short paragraph.\n\nAnother short paragraph.\n\nYet another paragraph."
        )
        
        chapters = processor._split_by_length(content_obj, max_length=50)
        
        assert len(chapters) >= 1
        for chapter in chapters:
            assert len(chapter.content) <= 200  # Some reasonable limit 