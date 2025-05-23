"""DrawIO converter tests."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, mock_open
import tempfile
import os

from src.converters.drawio import DrawIOConverter
from src.converters.base import ImageType
from src.config import Config


class TestDrawIOConverter:
    """DrawIOConverter tests."""
    
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
        config.image.drawio_path = None
        return config
        
    @pytest.fixture
    def converter(self, mock_config):
        """Create DrawIOConverter instance."""
        return DrawIOConverter(mock_config)
        
    def test_get_supported_type(self, converter):
        """Test supported image type."""
        assert converter.get_supported_type() == ImageType.DRAWIO
        
    def test_validate_source_url(self, converter):
        """Test URL source validation."""
        assert converter.validate_source("https://example.com/diagram.drawio") is True
        assert converter.validate_source("http://example.com/diagram.drawio") is True
        
    def test_validate_source_xml_content(self, converter):
        """Test XML content validation."""
        valid_xml = '''<mxfile host="app.diagrams.net">
  <diagram>
    <mxGraphModel>
      <root>
        <mxCell id="0"/>
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>'''
        
        assert converter.validate_source(valid_xml) is True
        
    def test_validate_source_invalid(self, converter):
        """Test invalid source validation."""
        assert converter.validate_source("") is False
        assert converter.validate_source("not a valid source") is False
        
    @pytest.mark.asyncio
    async def test_convert_from_content_mock(self, converter):
        """Test converting from content with mocked file operations."""
        drawio_content = '''<mxfile host="app.diagrams.net">
  <diagram>
    <mxGraphModel>
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
        <mxCell id="2" value="Test" style="rounded=1;" vertex="1" parent="1">
          <mxGeometry x="20" y="20" width="120" height="60" as="geometry"/>
        </mxCell>
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>'''
        
        # Mock the entire conversion process
        with patch('tempfile.NamedTemporaryFile') as mock_temp:
            mock_temp.return_value.__enter__.return_value.name = '/tmp/test.drawio'
            
            with patch('os.path.exists') as mock_exists:
                mock_exists.return_value = True
                
                with patch('builtins.open', mock_open(read_data=b'mock_image_data')):
                    with patch.object(converter, '_run_drawio_headless', return_value=True) as mock_run:
                        result = await converter.convert(drawio_content)
                        
                        assert result == b'mock_image_data'
                        mock_run.assert_called_once()
                        
    @pytest.mark.asyncio
    async def test_convert_from_url_mock(self, converter):
        """Test converting from URL with mocked HTTP client."""
        url = "https://example.com/diagram.drawio"
        drawio_content = '''<mxfile><diagram><mxGraphModel><root><mxCell id="0"/></root></mxGraphModel></diagram></mxfile>'''
        
        # Mock the entire _convert_from_url method instead of aiohttp
        with patch.object(converter, '_convert_from_url', return_value=b'mock_data') as mock_convert:
            result = await converter.convert(url)
            
            assert result == b'mock_data'
            mock_convert.assert_called_once_with(url)
                
    @pytest.mark.asyncio
    async def test_convert_invalid_source(self, converter):
        """Test converting invalid source."""
        with pytest.raises(ValueError, match="Invalid DrawIO source"):
            await converter.convert("")
            
    def test_generate_puppeteer_script(self, converter):
        """Test Puppeteer script generation."""
        script = converter._generate_puppeteer_script(
            '/tmp/input.drawio',
            '/tmp/output.png',
            width=1024,
            height=768
        )
        
        assert 'puppeteer' in script
        assert '1024' in script
        assert '768' in script
        assert '/tmp/output.png' in script
        assert 'app.diagrams.net' in script
        
    @pytest.mark.asyncio
    async def test_run_drawio_desktop_mock(self, converter, mock_config):
        """Test desktop DrawIO execution with mocks."""
        mock_config.image.drawio_path = '/usr/bin/drawio'
        converter.config = mock_config
        
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate.return_value = (b'success', b'')
            mock_subprocess.return_value = mock_process
            
            with patch('asyncio.wait_for', return_value=(b'success', b'')):
                result = await converter._run_drawio_desktop('/tmp/input.drawio', '/tmp/output.png')
                
                assert result is True
                mock_subprocess.assert_called_once()
                
    @pytest.mark.asyncio
    async def test_run_drawio_desktop_error(self, converter, mock_config):
        """Test desktop DrawIO execution with error."""
        mock_config.image.drawio_path = '/usr/bin/drawio'
        converter.config = mock_config
        
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.returncode = 1
            mock_process.communicate.return_value = (b'', b'conversion failed')
            mock_subprocess.return_value = mock_process
            
            with patch('asyncio.wait_for', return_value=(b'', b'conversion failed')):
                with pytest.raises(RuntimeError, match="DrawIO conversion failed"):
                    await converter._run_drawio_desktop('/tmp/input.drawio', '/tmp/output.png')
                    
    @pytest.mark.asyncio
    async def test_run_drawio_headless_mock(self, converter):
        """Test headless DrawIO execution with mocks."""
        with patch('tempfile.NamedTemporaryFile') as mock_temp:
            mock_temp.return_value.__enter__.return_value.name = '/tmp/script.js'
            
            with patch('asyncio.create_subprocess_exec') as mock_subprocess:
                mock_process = AsyncMock()
                mock_process.returncode = 0
                mock_process.communicate.return_value = (b'success', b'')
                mock_subprocess.return_value = mock_process
                
                with patch('asyncio.wait_for', return_value=(b'success', b'')):
                    with patch('os.path.exists', return_value=False):  # Script cleanup
                        result = await converter._run_drawio_headless('/tmp/input.drawio', '/tmp/output.png')
                        
                        assert result is True
                        
    @pytest.mark.asyncio
    async def test_run_drawio_headless_timeout(self, converter):
        """Test headless DrawIO timeout."""
        with patch('tempfile.NamedTemporaryFile') as mock_temp:
            mock_temp.return_value.__enter__.return_value.name = '/tmp/script.js'
            
            with patch('asyncio.create_subprocess_exec') as mock_subprocess:
                mock_process = AsyncMock()
                mock_subprocess.return_value = mock_process
                
                with patch('asyncio.wait_for', side_effect=asyncio.TimeoutError()):
                    with patch('os.path.exists', return_value=False):
                        with pytest.raises(asyncio.TimeoutError):
                            await converter._run_drawio_headless('/tmp/input.drawio', '/tmp/output.png')
                            
    def test_drawio_content_validation(self, converter):
        """Test various DrawIO content formats."""
        # Valid mxfile format
        mxfile_content = '<mxfile host="app.diagrams.net"><diagram></diagram></mxfile>'
        assert converter.validate_source(mxfile_content) is True
        
        # Valid diagram format
        diagram_content = '<diagram><mxGraphModel><root></root></mxGraphModel></diagram>'
        assert converter.validate_source(diagram_content) is True
        
        # Invalid content
        assert converter.validate_source('not xml') is False
        assert converter.validate_source('<svg></svg>') is False  # Not DrawIO format 