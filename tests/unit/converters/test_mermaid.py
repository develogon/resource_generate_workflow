"""Mermaid converter tests."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, mock_open
import tempfile
import os

from src.converters.mermaid import MermaidConverter
from src.converters.base import ImageType
from src.config import Config


class TestMermaidConverter:
    """MermaidConverter tests."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock config."""
        config = Mock(spec=Config)
        config.workers = Mock()
        config.workers.max_concurrent_tasks = 3
        config.image = Mock()
        config.image.width = 800
        config.image.height = 600
        config.image.conversion_timeout = 30.0
        config.image.mermaid_cli_path = 'mmdc'
        return config
        
    @pytest.fixture
    def converter(self, mock_config):
        """Create MermaidConverter instance."""
        return MermaidConverter(mock_config)
        
    def test_get_supported_type(self, converter):
        """Test supported image type."""
        assert converter.get_supported_type() == ImageType.MERMAID
        
    def test_validate_source_flowchart(self, converter):
        """Test flowchart source validation."""
        flowchart = '''graph TD
    A[Start] --> B{Decision}
    B -->|Yes| C[Process 1]
    B -->|No| D[Process 2]
    C --> E[End]
    D --> E'''
        
        assert converter.validate_source(flowchart) is True
        
    def test_validate_source_sequence_diagram(self, converter):
        """Test sequence diagram validation."""
        sequence = '''sequenceDiagram
    participant A as Alice
    participant B as Bob
    A->>B: Hello Bob, how are you?
    B-->>A: Great!'''
        
        assert converter.validate_source(sequence) is True
        
    def test_validate_source_various_types(self, converter):
        """Test various mermaid diagram types."""
        diagrams = [
            'flowchart LR\n    A --> B',
            'classDiagram\n    Class01 <|-- AveryLongClass',
            'stateDiagram\n    [*] --> Still',
            'erDiagram\n    CUSTOMER ||--o{ ORDER : places',
            'gantt\n    title A Gantt Diagram',
            'pie title Pets adopted by volunteers\n    "Dogs" : 386',
            'journey\n    title My working day',
            'gitgraph\n    commit',
            'requirementDiagram\n    requirement test_req {',
            'timeline\n    title History of Social Media Platform'
        ]
        
        for diagram in diagrams:
            assert converter.validate_source(diagram) is True, f"Failed for: {diagram}"
            
    def test_validate_source_code_block(self, converter):
        """Test code block format validation."""
        code_block = '''```mermaid
graph LR
    A --> B
    B --> C
```'''
        
        assert converter.validate_source(code_block) is True
        
    def test_validate_source_invalid(self, converter):
        """Test invalid source validation."""
        assert converter.validate_source("") is False
        assert converter.validate_source("not mermaid") is False
        assert converter.validate_source("random text here") is False
        
    def test_extract_mermaid_content_from_code_block(self, converter):
        """Test extracting mermaid content from markdown code block."""
        markdown = '''```mermaid
graph TD
    A --> B
    B --> C
```'''
        
        extracted = converter.extract_mermaid_content(markdown)
        assert 'graph TD' in extracted
        assert 'A --> B' in extracted
        assert '```' not in extracted
        
    def test_extract_mermaid_content_plain(self, converter):
        """Test extracting content from plain mermaid."""
        plain = '''graph TD
    A --> B
    B --> C'''
        
        extracted = converter.extract_mermaid_content(plain)
        assert extracted == plain
        
    @pytest.mark.asyncio
    async def test_convert_with_cli_mock(self, converter):
        """Test conversion using CLI with mocks."""
        mermaid_content = '''graph TD
    A[Start] --> B[End]'''
        
        with patch('tempfile.NamedTemporaryFile') as mock_temp:
            mock_temp.return_value.__enter__.return_value.name = '/tmp/test.mmd'
            
            with patch.object(converter, '_check_mermaid_cli', return_value=True):
                with patch.object(converter, '_run_mermaid_cli', return_value=True):
                    with patch('os.path.exists', return_value=True):
                        with patch('builtins.open', mock_open(read_data=b'mock_image_data')):
                            result = await converter.convert(mermaid_content)
                            
                            assert result == b'mock_image_data'
                            
    @pytest.mark.asyncio
    async def test_convert_with_headless_fallback(self, converter):
        """Test conversion fallback to headless when CLI unavailable."""
        mermaid_content = '''graph TD
    A[Start] --> B[End]'''
        
        with patch('tempfile.NamedTemporaryFile') as mock_temp:
            mock_temp.return_value.__enter__.return_value.name = '/tmp/test.mmd'
            
            with patch.object(converter, '_check_mermaid_cli', return_value=False):
                with patch.object(converter, '_run_mermaid_headless', return_value=True):
                    with patch('os.path.exists', return_value=True):
                        with patch('builtins.open', mock_open(read_data=b'mock_image_data')):
                            result = await converter.convert(mermaid_content)
                            
                            assert result == b'mock_image_data'
                            
    @pytest.mark.asyncio
    async def test_convert_invalid_source(self, converter):
        """Test converting invalid source."""
        with pytest.raises(ValueError, match="Invalid Mermaid source"):
            await converter.convert("")
            
    @pytest.mark.asyncio
    async def test_check_mermaid_cli_available(self, converter):
        """Test CLI availability check when available."""
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.wait.return_value = None
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process
            
            result = await converter._check_mermaid_cli()
            assert result is True
            
    @pytest.mark.asyncio
    async def test_check_mermaid_cli_unavailable(self, converter):
        """Test CLI availability check when unavailable."""
        with patch('asyncio.create_subprocess_exec', side_effect=FileNotFoundError()):
            result = await converter._check_mermaid_cli()
            assert result is False
            
    @pytest.mark.asyncio
    async def test_run_mermaid_cli_success(self, converter):
        """Test successful CLI execution."""
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate.return_value = (b'success', b'')
            mock_subprocess.return_value = mock_process
            
            with patch('asyncio.wait_for', return_value=(b'success', b'')):
                result = await converter._run_mermaid_cli('/tmp/input.mmd', '/tmp/output.png')
                
                assert result is True
                mock_subprocess.assert_called_once()
                
                # Check command line arguments
                args = mock_subprocess.call_args[1]
                cmd = mock_subprocess.call_args[0]
                assert 'mmdc' in cmd
                assert '-i' in cmd
                assert '-o' in cmd
                
    @pytest.mark.asyncio
    async def test_run_mermaid_cli_error(self, converter):
        """Test CLI execution with error."""
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.returncode = 1
            mock_process.communicate.return_value = (b'', b'conversion failed')
            mock_subprocess.return_value = mock_process
            
            with patch('asyncio.wait_for', return_value=(b'', b'conversion failed')):
                with pytest.raises(RuntimeError, match="Mermaid CLI conversion failed"):
                    await converter._run_mermaid_cli('/tmp/input.mmd', '/tmp/output.png')
                    
    @pytest.mark.asyncio
    async def test_run_mermaid_cli_timeout(self, converter):
        """Test CLI timeout."""
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = AsyncMock()
            mock_subprocess.return_value = mock_process
            
            with patch('asyncio.wait_for', side_effect=asyncio.TimeoutError()):
                with pytest.raises(asyncio.TimeoutError):
                    await converter._run_mermaid_cli('/tmp/input.mmd', '/tmp/output.png')
                    
    @pytest.mark.asyncio
    async def test_run_mermaid_headless_success(self, converter):
        """Test successful headless execution."""
        content = 'graph TD\nA --> B'
        
        with patch('tempfile.NamedTemporaryFile') as mock_temp:
            mock_temp.return_value.__enter__.return_value.name = '/tmp/script.js'
            
            with patch('asyncio.create_subprocess_exec') as mock_subprocess:
                mock_process = AsyncMock()
                mock_process.returncode = 0
                mock_process.communicate.return_value = (b'success', b'')
                mock_subprocess.return_value = mock_process
                
                with patch('asyncio.wait_for', return_value=(b'success', b'')):
                    with patch('os.path.exists', return_value=False):  # Script cleanup
                        result = await converter._run_mermaid_headless(content, '/tmp/output.png')
                        
                        assert result is True
                        
    def test_generate_puppeteer_script(self, converter):
        """Test Puppeteer script generation."""
        content = 'graph TD\nA --> B'
        script = converter._generate_puppeteer_script(
            content,
            '/tmp/output.png',
            width=1024,
            height=768,
            theme='dark',
            background='transparent'
        )
        
        assert 'puppeteer' in script
        assert '1024' in script
        assert '768' in script
        assert '/tmp/output.png' in script
        assert 'dark' in script
        assert 'transparent' in script.lower()
        assert 'graph TD' in script
        assert 'mermaid' in script.lower()
        
    def test_mermaid_keywords_detection(self, converter):
        """Test mermaid keyword detection."""
        # Test all supported diagram types
        keywords = [
            'graph', 'flowchart', 'sequenceDiagram', 'classDiagram',
            'stateDiagram', 'erDiagram', 'gantt', 'pie', 'journey',
            'gitgraph', 'requirementDiagram', 'timeline'
        ]
        
        for keyword in keywords:
            content = f'{keyword} TD\n    A --> B'
            assert converter.validate_source(content) is True, f"Failed for keyword: {keyword}"
            
    def test_case_insensitive_validation(self, converter):
        """Test case insensitive validation."""
        content_upper = 'GRAPH TD\n    A --> B'
        content_lower = 'graph td\n    a --> b'
        content_mixed = 'Graph TD\n    A --> B'
        
        assert converter.validate_source(content_upper) is True
        assert converter.validate_source(content_lower) is True
        assert converter.validate_source(content_mixed) is True 