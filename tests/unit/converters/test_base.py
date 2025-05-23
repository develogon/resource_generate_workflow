"""Converters Base クラスのテスト."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock

from src.converters.base import BaseConverter, ImageType
from src.config import Config


class TestConverter(BaseConverter):
    """テスト用コンバーター."""
    
    async def convert(self, source: str, **kwargs) -> bytes:
        """テスト用変換処理."""
        if not source:
            raise ValueError("Empty source")
        return source.encode('utf-8')
        
    def get_supported_type(self) -> ImageType:
        """テスト用タイプ."""
        return ImageType.SVG


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
    """テスト用コンバーター."""
    return TestConverter(config)


class TestBaseConverter:
    """BaseConverter のテスト."""
    
    def test_init(self, converter, config):
        """初期化のテスト."""
        assert converter.config == config
        assert converter.semaphore._value == config.workers.max_concurrent_tasks
        
    def test_validate_source_valid(self, converter):
        """有効なソースの検証テスト."""
        assert converter.validate_source("valid source") is True
        
    def test_validate_source_invalid(self, converter):
        """無効なソースの検証テスト."""
        assert converter.validate_source("") is False
        assert converter.validate_source(None) is False
        assert converter.validate_source(123) is False
        
    def test_get_output_format(self, converter):
        """出力フォーマット取得のテスト."""
        assert converter.get_output_format() == "png"
        
    def test_get_output_size(self, converter):
        """出力サイズ取得のテスト."""
        assert converter.get_output_size() == (800, 600)
        
    @pytest.mark.asyncio
    async def test_convert_success(self, converter):
        """変換成功のテスト."""
        result = await converter.convert("test")
        assert result == b"test"
        
    @pytest.mark.asyncio
    async def test_convert_error(self, converter):
        """変換エラーのテスト."""
        with pytest.raises(ValueError):
            await converter.convert("")
            
    @pytest.mark.asyncio
    async def test_batch_convert_success(self, converter):
        """バッチ変換成功のテスト."""
        sources = ["test1", "test2", "test3"]
        results = await converter.batch_convert(sources)
        
        assert len(results) == 3
        assert results[0] == b"test1"
        assert results[1] == b"test2"
        assert results[2] == b"test3"
        
    @pytest.mark.asyncio
    async def test_batch_convert_with_errors(self, converter):
        """エラーを含むバッチ変換のテスト."""
        sources = ["test1", "", "test3"]  # 空文字列はエラー
        results = await converter.batch_convert(sources)
        
        # エラーのある要素はスキップされる
        assert len(results) == 2
        assert results[0] == b"test1"
        assert results[1] == b"test3"
        
    @pytest.mark.asyncio
    async def test_batch_convert_empty(self, converter):
        """空のバッチ変換のテスト."""
        results = await converter.batch_convert([])
        assert results == []
        
    @pytest.mark.asyncio
    async def test_safe_convert_success(self, converter):
        """セマフォ制御付き変換成功のテスト."""
        result = await converter._safe_convert("test")
        assert result == b"test"
        
    @pytest.mark.asyncio
    async def test_safe_convert_error(self, converter):
        """セマフォ制御付き変換エラーのテスト."""
        with pytest.raises(ValueError):
            await converter._safe_convert("")
            
    @pytest.mark.asyncio
    async def test_concurrent_conversion(self, converter):
        """並行変換のテスト."""
        sources = [f"test{i}" for i in range(5)]
        
        # 並行実行
        tasks = [converter._safe_convert(source) for source in sources]
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 5
        for i, result in enumerate(results):
            assert result == f"test{i}".encode('utf-8')
            
    def test_abstract_methods(self):
        """抽象メソッドのテスト."""
        with pytest.raises(TypeError):
            BaseConverter(Config()) 