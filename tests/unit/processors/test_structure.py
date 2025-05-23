"""Structure processor tests."""

import pytest
from unittest.mock import Mock

from src.processors.structure import (
    StructureProcessor, 
    StructureElement, 
    DocumentStructure
)
from src.processors.base import ProcessorType, ProcessingRequest
from src.models import Content
from src.config import Config


class TestStructureElement:
    """StructureElement tests."""
    
    def test_create_structure_element(self):
        """Test creating StructureElement."""
        element = StructureElement(
            type="heading",
            level=1,
            content="Test Heading",
            metadata={"word_count": 2}
        )
        
        assert element.type == "heading"
        assert element.level == 1
        assert element.content == "Test Heading"
        assert element.metadata["word_count"] == 2


class TestDocumentStructure:
    """DocumentStructure tests."""
    
    def test_create_document_structure(self):
        """Test creating DocumentStructure."""
        elements = [
            StructureElement("heading", 1, "Title", {}),
            StructureElement("paragraph", 0, "Content", {})
        ]
        
        structure = DocumentStructure(
            title="Test Document",
            elements=elements,
            hierarchy={"sections": []},
            metadata={"total_elements": 2}
        )
        
        assert structure.title == "Test Document"
        assert len(structure.elements) == 2
        assert structure.metadata["total_elements"] == 2


class TestStructureProcessor:
    """StructureProcessor tests."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock config."""
        config = Mock(spec=Config)
        config.workers = Mock()
        config.workers.max_concurrent_tasks = 3
        return config
        
    @pytest.fixture
    def processor(self, mock_config):
        """Create StructureProcessor instance."""
        return StructureProcessor(mock_config)
        
    def test_get_processor_type(self, processor):
        """Test processor type."""
        assert processor.get_processor_type() == ProcessorType.STRUCTURE
        
    @pytest.mark.asyncio
    async def test_process_markdown_content(self, processor):
        """Test processing markdown content."""
        content = """# Main Title

This is the introduction paragraph.

## Section 1

Section content here.

```python
def hello():
    print("Hello, World!")
```

- List item 1
- List item 2
- List item 3

![Test Image](image.png)

| Column 1 | Column 2 |
|----------|----------|
| Data 1   | Data 2   |

### Subsection 1.1

More content here."""
        
        request = ProcessingRequest(
            content=content,
            processor_type=ProcessorType.STRUCTURE,
            options={"title": "Test Document", "analysis_method": "markdown"},
            context={}
        )
        
        result = await processor.process(request)
        
        assert result.success is True
        assert isinstance(result.content, DocumentStructure)
        
        structure = result.content
        assert structure.title == "Test Document"
        assert len(structure.elements) > 0
        
        # Check that different element types are detected
        element_types = [element.type for element in structure.elements]
        assert "heading" in element_types
        assert "paragraph" in element_types
        assert "code" in element_types
        assert "list" in element_types
        assert "image" in element_types
        assert "table" in element_types
        
        # Check metadata
        assert result.metadata["element_count"] == len(structure.elements)
        assert result.metadata["title"] == "Test Document"
        
    @pytest.mark.asyncio
    async def test_process_plain_text(self, processor):
        """Test processing plain text content."""
        content = """This is plain text content.

It has multiple paragraphs but no special markdown formatting.

This should be analyzed as simple paragraphs."""
        
        request = ProcessingRequest(
            content=content,
            processor_type=ProcessorType.STRUCTURE,
            options={"title": "Plain Document", "analysis_method": "plain_text"},
            context={}
        )
        
        result = await processor.process(request)
        
        assert result.success is True
        structure = result.content
        assert structure.title == "Plain Document"
        
        # All elements should be paragraphs
        for element in structure.elements:
            assert element.type == "paragraph"
            assert element.level == 0
            
    @pytest.mark.asyncio
    async def test_process_content_object(self, processor):
        """Test processing Content object."""
        content_obj = Content(
            id="test-content-1",
            title="Content Object",
            content="# Heading\n\nParagraph content.",
            metadata={"source": "test"}
        )
        
        request = ProcessingRequest(
            content=content_obj,
            processor_type=ProcessorType.STRUCTURE,
            options={"analysis_method": "markdown"},
            context={}
        )
        
        result = await processor.process(request)
        
        assert result.success is True
        assert result.content.title == "Content Object"
        
    def test_parse_heading(self, processor):
        """Test heading parsing."""
        element = processor._parse_heading("## Test Heading")
        
        assert element.type == "heading"
        assert element.level == 2
        assert element.content == "Test Heading"
        assert element.metadata["original_line"] == "## Test Heading"
        
    def test_parse_code_block(self, processor):
        """Test code block parsing."""
        lines = [
            "```python",
            "def hello():",
            "    print('Hello')",
            "```"
        ]
        
        element, skip_lines = processor._parse_code_block(lines, 0)
        
        assert element.type == "code"
        assert element.metadata["language"] == "python"
        assert "def hello():" in element.content
        assert skip_lines == 3
        
    def test_parse_list(self, processor):
        """Test list parsing."""
        lines = [
            "- Item 1",
            "- Item 2",
            "- Item 3",
            "",
            "Next paragraph"
        ]
        
        element, skip_lines = processor._parse_list(lines, 0)
        
        assert element.type == "list"
        assert element.metadata["item_count"] == 3
        assert "Item 1" in element.content
        
    def test_parse_image(self, processor):
        """Test image parsing."""
        line = "![Alt text](image.png)"
        element = processor._parse_image(line)
        
        assert element.type == "image"
        assert element.content == "Alt text"
        assert element.metadata["url"] == "image.png"
        assert element.metadata["alt_text"] == "Alt text"
        
    def test_parse_table(self, processor):
        """Test table parsing."""
        lines = [
            "| Column 1 | Column 2 |",
            "|----------|----------|",
            "| Data 1   | Data 2   |",
            "| Data 3   | Data 4   |",
            "",
            "Next paragraph"
        ]
        
        element, skip_lines = processor._parse_table(lines, 0)
        
        assert element is not None
        assert element.type == "table"
        assert element.metadata["column_count"] == 2
        assert element.metadata["row_count"] == 2
        assert "Column 1" in element.metadata["columns"]
        
    def test_parse_table_invalid(self, processor):
        """Test invalid table parsing."""
        lines = [
            "| Column 1 | Column 2 |",
            "Not a separator line",
            "| Data 1   | Data 2   |"
        ]
        
        element, skip_lines = processor._parse_table(lines, 0)
        
        assert element is None
        assert skip_lines == 0
        
    def test_build_hierarchy(self, processor):
        """Test hierarchy building."""
        elements = [
            StructureElement("heading", 1, "Chapter 1", {}),
            StructureElement("paragraph", 0, "Chapter content", {}),
            StructureElement("heading", 2, "Section 1.1", {}),
            StructureElement("paragraph", 0, "Section content", {}),
            StructureElement("heading", 1, "Chapter 2", {}),
            StructureElement("paragraph", 0, "More content", {})
        ]
        
        hierarchy = processor._build_hierarchy(elements)
        
        assert "sections" in hierarchy
        assert len(hierarchy["sections"]) == 3  # Two H1 chapters + one H2 section
        
        # Check first section (H1)
        section1 = hierarchy["sections"][0]
        assert section1["title"] == "Chapter 1"
        assert section1["level"] == 1
        assert len(section1["content"]) == 1  # One paragraph
        
        # Check second section (H2)
        section2 = hierarchy["sections"][1]
        assert section2["title"] == "Section 1.1"
        assert section2["level"] == 2
        assert len(section2["content"]) == 1  # One paragraph
        
        # Check third section (H1)
        section3 = hierarchy["sections"][2]
        assert section3["title"] == "Chapter 2"
        assert section3["level"] == 1
        assert len(section3["content"]) == 1  # One paragraph
        
    def test_analyze_document_metadata(self, processor):
        """Test document metadata analysis."""
        elements = [
            StructureElement("heading", 1, "Title", {}),
            StructureElement("paragraph", 0, "Content", {}),
            StructureElement("code", 0, "print('hello')", {"language": "python"}),
            StructureElement("image", 0, "Alt text", {}),
            StructureElement("heading", 2, "Subtitle", {})
        ]
        
        metadata = processor._analyze_document_metadata(elements)
        
        assert metadata["total_elements"] == 5
        assert metadata["element_types"]["heading"] == 2
        assert metadata["element_types"]["paragraph"] == 1
        assert metadata["element_types"]["code"] == 1
        assert metadata["element_types"]["image"] == 1
        assert metadata["heading_levels"][1] == 1
        assert metadata["heading_levels"][2] == 1
        assert metadata["has_code"] is True
        assert metadata["has_images"] is True
        
    def test_is_special_line(self, processor):
        """Test special line detection."""
        assert processor._is_special_line("# Heading") is True
        assert processor._is_special_line("- List item") is True
        assert processor._is_special_line("```code") is True
        assert processor._is_special_line("![Image](url)") is True
        assert processor._is_special_line("| Table | Cell |") is True
        assert processor._is_special_line("Regular paragraph") is False
        
    @pytest.mark.asyncio
    async def test_invalid_request(self, processor):
        """Test processing invalid request."""
        request = ProcessingRequest(
            content="",  # Empty content
            processor_type=ProcessorType.STRUCTURE,
            options={},
            context={}
        )
        
        result = await processor.process(request)
        
        assert result.success is False
        assert result.error == "Invalid request" 