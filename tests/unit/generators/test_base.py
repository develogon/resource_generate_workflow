"""Generators Base クラスのテスト."""

import pytest
import asyncio
from unittest.mock import Mock

from src.generators.base import (
    BaseGenerator, 
    GenerationType, 
    GenerationRequest, 
    GenerationResult
)
from src.config import Config
from src.models import Content


class MockGenerator(BaseGenerator):
    """テスト用ジェネレーター."""
    
    async def generate(self, request: GenerationRequest) -> GenerationResult:
        """テスト用生成処理."""
        if not request.content.content:
            raise ValueError("Empty content body")
            
        generated_content = f"Generated: {request.content.content}"
        metadata = self.extract_metadata(request, generated_content)
        
        return GenerationResult(
            content=generated_content,
            metadata=metadata,
            generation_type=self.get_generation_type(),
            success=True
        )
        
    def get_generation_type(self) -> GenerationType:
        """テスト用タイプ."""
        return GenerationType.ARTICLE
        
    def get_prompt_template(self) -> str:
        """テスト用プロンプトテンプレート."""
        return "Generate article for: {title}\nContent: {content}"


@pytest.fixture
def config():
    """テスト用設定."""
    config = Config()
    config.workers.max_concurrent_tasks = 2
    return config


@pytest.fixture
def generator(config):
    """テスト用ジェネレーター."""
    return MockGenerator(config)


@pytest.fixture
def sample_content():
    """テスト用コンテンツ."""
    return Content(
        id="test-1",
        title="Test Title",
        content="Test content body",
        metadata={"author": "test"}
    )


@pytest.fixture
def generation_request(sample_content):
    """テスト用生成リクエスト."""
    return GenerationRequest(
        content=sample_content,
        generation_type=GenerationType.ARTICLE,
        options={"style": "formal"},
        context={"lang": "ja"}
    )


class TestBaseGenerator:
    """BaseGenerator のテスト."""
    
    def test_init(self, generator, config):
        """初期化のテスト."""
        assert generator.config == config
        assert generator.semaphore._value == config.workers.max_concurrent_tasks
        
    def test_generation_type(self, generator):
        """生成タイプのテスト."""
        assert generator.get_generation_type() == GenerationType.ARTICLE
        
    def test_prompt_template(self, generator):
        """プロンプトテンプレートのテスト."""
        template = generator.get_prompt_template()
        assert "Generate article for: {title}" in template
        assert "Content: {content}" in template
        
    def test_validate_request_valid(self, generator, generation_request):
        """有効なリクエストの検証テスト."""
        assert generator.validate_request(generation_request) is True
        
    def test_validate_request_invalid_empty(self, generator):
        """無効なリクエスト（空）の検証テスト."""
        assert generator.validate_request(None) is False
        
    def test_validate_request_invalid_no_content(self, generator):
        """無効なリクエスト（コンテンツなし）の検証テスト."""
        request = GenerationRequest(
            content=None,
            generation_type=GenerationType.ARTICLE,
            options={},
            context={}
        )
        assert generator.validate_request(request) is False
        
    def test_validate_request_invalid_wrong_type(self, generator, sample_content):
        """無効なリクエスト（間違ったタイプ）の検証テスト."""
        request = GenerationRequest(
            content=sample_content,
            generation_type=GenerationType.SCRIPT,  # 間違ったタイプ
            options={},
            context={}
        )
        assert generator.validate_request(request) is False
        
    def test_build_prompt(self, generator, generation_request):
        """プロンプト構築のテスト."""
        prompt = generator.build_prompt(generation_request)
        assert "Generate article for: Test Title" in prompt
        assert "Content: Test content body" in prompt
        
    def test_extract_metadata(self, generator, generation_request):
        """メタデータ抽出のテスト."""
        generated_content = "Generated content for testing"
        metadata = generator.extract_metadata(generation_request, generated_content)
        
        assert metadata["word_count"] == 4  # "Generated", "content", "for", "testing"
        assert metadata["char_count"] == len(generated_content)
        assert metadata["generation_type"] == "article"
        assert metadata["source_title"] == "Test Title"
        assert "generated_at" in metadata
        
    @pytest.mark.asyncio
    async def test_generate_success(self, generator, generation_request):
        """生成成功のテスト."""
        result = await generator.generate(generation_request)
        
        assert result.success is True
        assert result.error is None
        assert result.generation_type == GenerationType.ARTICLE
        assert result.content == "Generated: Test content body"
        assert isinstance(result.metadata, dict)
        
    @pytest.mark.asyncio
    async def test_generate_error(self, generator, sample_content):
        """生成エラーのテスト."""
        # 空のコンテンツでエラーを発生させる
        empty_content = Content(
            id="test-empty",
            title="Test",
            content="",  # 空のコンテンツ
            metadata={}
        )
        request = GenerationRequest(
            content=empty_content,
            generation_type=GenerationType.ARTICLE,
            options={},
            context={}
        )
        
        with pytest.raises(ValueError):
            await generator.generate(request)
            
    @pytest.mark.asyncio
    async def test_safe_generate_success(self, generator, generation_request):
        """セマフォ制御付き生成成功のテスト."""
        result = await generator._safe_generate(generation_request)
        
        assert result.success is True
        assert result.content == "Generated: Test content body"
        
    @pytest.mark.asyncio
    async def test_safe_generate_error(self, generator, sample_content):
        """セマフォ制御付き生成エラーのテスト."""
        # 空のコンテンツでエラーを発生させる
        empty_content = Content(
            id="test-empty",
            title="Test",
            content="",
            metadata={}
        )
        request = GenerationRequest(
            content=empty_content,
            generation_type=GenerationType.ARTICLE,
            options={},
            context={}
        )
        
        result = await generator._safe_generate(request)
        assert result.success is False
        assert result.error is not None
        assert "Empty content body" in result.error
        
    @pytest.mark.asyncio
    async def test_batch_generate_success(self, generator, sample_content):
        """バッチ生成成功のテスト."""
        contents = [
            Content(id=f"test-{i}", title=f"Title {i}", content=f"Content {i}", metadata={})
            for i in range(3)
        ]
        requests = [
            GenerationRequest(
                content=content,
                generation_type=GenerationType.ARTICLE,
                options={},
                context={}
            )
            for content in contents
        ]
        
        results = await generator.batch_generate(requests)
        
        assert len(results) == 3
        for i, result in enumerate(results):
            assert result.success is True
            assert result.content == f"Generated: Content {i}"
            
    @pytest.mark.asyncio
    async def test_batch_generate_with_errors(self, generator, sample_content):
        """エラーを含むバッチ生成のテスト."""
        contents = [
            Content(id="test-1", title="Title 1", content="Content 1", metadata={}),
            Content(id="test-2", title="Title 2", content="", metadata={}),  # エラー
            Content(id="test-3", title="Title 3", content="Content 3", metadata={}),
        ]
        requests = [
            GenerationRequest(
                content=content,
                generation_type=GenerationType.ARTICLE,
                options={},
                context={}
            )
            for content in contents
        ]
        
        results = await generator.batch_generate(requests)
        
        assert len(results) == 3
        assert results[0].success is True
        assert results[1].success is False  # エラー
        assert results[2].success is True
        
    @pytest.mark.asyncio
    async def test_batch_generate_empty(self, generator):
        """空のバッチ生成のテスト."""
        results = await generator.batch_generate([])
        assert results == []
        
    @pytest.mark.asyncio
    async def test_concurrent_generation(self, generator, sample_content):
        """並行生成のテスト."""
        contents = [
            Content(id=f"test-{i}", title=f"Title {i}", content=f"Content {i}", metadata={})
            for i in range(5)
        ]
        requests = [
            GenerationRequest(
                content=content,
                generation_type=GenerationType.ARTICLE,
                options={},
                context={}
            )
            for content in contents
        ]
        
        # 並行実行
        tasks = [generator._safe_generate(request) for request in requests]
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 5
        for i, result in enumerate(results):
            assert result.success is True
            assert result.content == f"Generated: Content {i}"
            
    def test_abstract_methods(self):
        """抽象メソッドのテスト."""
        with pytest.raises(TypeError):
            BaseGenerator(Config()) 