"""SVG Converter クラスのテスト."""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock, mock_open
import sys

from src.converters.svg import SVGConverter
from src.converters.base import ImageType
from src.config import Config


@pytest.fixture
def config():
    """テスト用設定."""
    config = Config()
    config.workers.max_concurrent_tasks = 2
    config.image.width = 800
    config.image.height = 600
    config.image.format = "PNG"
    return config


@pytest.fixture
def converter(config):
    """テスト用SVGコンバーター."""
    return SVGConverter(config)


@pytest.fixture
def sample_svg():
    """テスト用SVGデータ."""
    return '''<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
        <circle cx="50" cy="50" r="40" fill="red"/>
    </svg>'''


@pytest.fixture
def simple_svg_content():
    """シンプルなSVGコンテンツ（SVGタグなし）."""
    return '<circle cx="50" cy="50" r="40" fill="blue"/>'


class TestSVGConverter:
    """SVGConverter のテスト."""
    
    def test_init(self, converter, config):
        """初期化のテスト."""
        assert converter.config == config
        assert converter.get_supported_type() == ImageType.SVG
        
    def test_validate_source_valid_svg(self, converter, sample_svg):
        """有効なSVGの検証テスト."""
        assert converter.validate_source(sample_svg) is True
        
    def test_validate_source_valid_svg_content(self, converter, simple_svg_content):
        """有効なSVGコンテンツの検証テスト."""
        assert converter.validate_source(simple_svg_content) is True
        
    def test_validate_source_invalid_empty(self, converter):
        """無効なSVG（空）の検証テスト."""
        assert converter.validate_source("") is False
        assert converter.validate_source(None) is False
        
    def test_validate_source_invalid_no_svg(self, converter):
        """無効なSVG（SVG要素なし）の検証テスト."""
        assert converter.validate_source("just plain text") is False
        assert converter.validate_source("<div>not svg</div>") is False
        
    def test_validate_source_invalid_no_xml(self, converter):
        """無効なSVG（XML構造なし）の検証テスト."""
        assert converter.validate_source("svg without brackets") is False
        
    def test_preprocess_svg_with_svg_tag(self, converter, sample_svg):
        """SVGタグありのデータの前処理テスト."""
        result = converter._preprocess_svg(sample_svg, 800, 600)
        
        assert 'width="800"' in result
        assert 'height="600"' in result
        assert '<svg' in result
        
    def test_preprocess_svg_without_svg_tag(self, converter, simple_svg_content):
        """SVGタグなしのデータの前処理テスト."""
        result = converter._preprocess_svg(simple_svg_content, 800, 600)
        
        assert result.startswith('<svg')
        assert 'width="800"' in result
        assert 'height="600"' in result
        assert simple_svg_content in result
        assert result.endswith('</svg>')
        
    @pytest.mark.asyncio
    async def test_convert_invalid_source(self, converter):
        """無効なソースでの変換テスト."""
        with pytest.raises(ValueError, match="Invalid SVG source data"):
            await converter.convert("")
            
    @pytest.mark.asyncio
    async def test_convert_unsupported_format(self, converter, sample_svg):
        """サポートされていないフォーマットでの変換テスト."""
        with pytest.raises(RuntimeError, match="SVG conversion failed"):
            await converter.convert(sample_svg, format="gif")
            
    @pytest.mark.asyncio
    async def test_convert_to_png_with_cairosvg(self, converter, sample_svg):
        """cairosvgを使用したPNG変換テスト."""
        # cairosvgのモック設定
        mock_cairosvg = MagicMock()
        mock_cairosvg.svg2png.return_value = b'fake_png_data'
        
        with patch.dict('sys.modules', {'cairosvg': mock_cairosvg}):
            result = await converter.convert(sample_svg, format="png")
            
            assert result == b'fake_png_data'
            mock_cairosvg.svg2png.assert_called_once()
            
    @pytest.mark.asyncio
    async def test_convert_to_png_fallback(self, converter, sample_svg):
        """cairosvgなしでのPNG変換フォールバックテスト."""
        # cairosvgが利用できない状況をシミュレート
        with patch.dict('sys.modules', {'cairosvg': None}):
            result = await converter.convert(sample_svg, format="png")
            
            # フォールバック変換が実行されることを確認
            assert isinstance(result, bytes)
            assert len(result) > 0
            assert result.startswith(b'\x89PNG\r\n\x1a\n')  # PNG署名
            
    @pytest.mark.asyncio
    async def test_convert_to_jpg_with_libraries(self, converter, sample_svg):
        """ライブラリを使用したJPG変換テスト."""
        # cairosvgのモック設定
        mock_cairosvg = MagicMock()
        mock_cairosvg.svg2png.return_value = b'fake_png_data'
        
        # PILのモック設定
        mock_image = MagicMock()
        mock_png_image = MagicMock()
        mock_png_image.mode = 'RGBA'
        mock_png_image.size = (800, 600)
        mock_png_image.split.return_value = [None, None, None, MagicMock()]  # Alpha channel
        
        mock_rgb_image = MagicMock()
        mock_image.new.return_value = mock_rgb_image
        mock_image.open.return_value = mock_png_image
        
        # save メソッドのモック
        def mock_save(buffer, format, quality):
            buffer.write(b'fake_jpg_data')
            
        mock_rgb_image.save = mock_save
        
        with patch.dict('sys.modules', {'cairosvg': mock_cairosvg, 'PIL.Image': mock_image}):
            result = await converter.convert(sample_svg, format="jpg")
            
            assert isinstance(result, bytes)
            mock_cairosvg.svg2png.assert_called_once()
            mock_image.open.assert_called_once()
            
    @pytest.mark.asyncio
    async def test_convert_to_jpg_fallback(self, converter, sample_svg):
        """ライブラリなしでのJPG変換フォールバックテスト."""
        # 必要なライブラリが利用できない状況をシミュレート
        with patch.dict('sys.modules', {'cairosvg': None, 'PIL': None}):
            result = await converter.convert(sample_svg, format="jpg")
            
            # フォールバック変換が実行されることを確認
            assert isinstance(result, bytes)
            assert len(result) > 0
            assert result.startswith(b'\xff\xd8\xff\xe0')  # JPEG署名
            
    @pytest.mark.asyncio
    async def test_convert_with_custom_dimensions(self, converter, sample_svg):
        """カスタム寸法での変換テスト."""
        with patch.dict('sys.modules', {'cairosvg': None}):
            result = await converter.convert(
                sample_svg, 
                width=1200, 
                height=900, 
                format="png"
            )
            
            assert isinstance(result, bytes)
            assert len(result) > 0
            
    @pytest.mark.asyncio
    async def test_fallback_conversion_png(self, converter, sample_svg):
        """フォールバック変換（PNG）のテスト."""
        result = await converter._fallback_conversion(sample_svg, 'png', 800, 600)
        
        assert isinstance(result, bytes)
        assert result.startswith(b'\x89PNG\r\n\x1a\n')
        assert len(result) <= 1008  # ヘッダー + 最大1000バイト
        
    @pytest.mark.asyncio
    async def test_fallback_conversion_jpg(self, converter, sample_svg):
        """フォールバック変換（JPG）のテスト."""
        result = await converter._fallback_conversion(sample_svg, 'jpg', 800, 600)
        
        assert isinstance(result, bytes)
        assert result.startswith(b'\xff\xd8\xff\xe0')
        assert len(result) <= 1004  # ヘッダー + 最大1000バイト
        
    @pytest.mark.asyncio
    async def test_batch_convert_mixed_results(self, converter):
        """バッチ変換（成功・失敗混在）のテスト."""
        sources = [
            '<svg><circle cx="50" cy="50" r="40" fill="red"/></svg>',
            '',  # 無効なソース
            '<svg><rect x="10" y="10" width="80" height="80" fill="blue"/></svg>'
        ]
        
        with patch.dict('sys.modules', {'cairosvg': None}):
            results = await converter.batch_convert(sources)
            
            # エラーのある要素はスキップされる
            assert len(results) == 2
            assert all(isinstance(result, bytes) for result in results) 