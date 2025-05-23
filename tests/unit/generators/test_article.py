"""Article Generator クラスのテスト."""

import pytest
import asyncio

from src.generators.article import ArticleGenerator
from src.generators.base import GenerationType, GenerationRequest, GenerationResult
from src.config import Config
from src.models import Content


@pytest.fixture
def config():
    """テスト用設定."""
    config = Config()
    config.workers.max_concurrent_tasks = 2
    return config


@pytest.fixture
def generator(config):
    """テスト用記事ジェネレーター."""
    return ArticleGenerator(config)


@pytest.fixture
def sample_content():
    """テスト用コンテンツ."""
    return Content(
        id="test-1",
        title="プログラミング入門",
        content="プログラミングは現代社会において重要なスキルです。基本的な概念を理解することが大切です。実践的な学習が効果的です。",
        metadata={"category": "education"}
    )


@pytest.fixture
def generation_request(sample_content):
    """テスト用生成リクエスト."""
    return GenerationRequest(
        content=sample_content,
        generation_type=GenerationType.ARTICLE,
        options={"style": "formal", "target_length": "medium", "include_examples": True},
        context={"lang": "ja"}
    )


class TestArticleGenerator:
    """ArticleGenerator のテスト."""
    
    def test_init(self, generator, config):
        """初期化のテスト."""
        assert generator.config == config
        assert generator.get_generation_type() == GenerationType.ARTICLE
        
    def test_prompt_template(self, generator):
        """プロンプトテンプレートのテスト."""
        template = generator.get_prompt_template()
        assert "タイトル: {title}" in template
        assert "元のコンテンツ: {content}" in template
        assert "スタイル: {style}" in template
        assert "言語: {lang}" in template
        
    @pytest.mark.asyncio
    async def test_generate_success(self, generator, generation_request):
        """記事生成成功のテスト."""
        result = await generator.generate(generation_request)
        
        assert result.success is True
        assert result.error is None
        assert result.generation_type == GenerationType.ARTICLE
        assert len(result.content) > 0
        assert isinstance(result.metadata, dict)
        
        # 記事の構造をチェック
        assert "# プログラミング入門" in result.content
        assert "## " in result.content  # 見出しが含まれている
        assert "まとめ" in result.content or "結論" in result.content
        
    @pytest.mark.asyncio
    async def test_generate_with_casual_style(self, generator, sample_content):
        """カジュアルスタイルでの記事生成テスト."""
        request = GenerationRequest(
            content=sample_content,
            generation_type=GenerationType.ARTICLE,
            options={"style": "casual"},
            context={"lang": "ja"}
        )
        
        result = await generator.generate(request)
        
        assert result.success is True
        assert "今回は" in result.content
        assert "まとめ" in result.content
        
    @pytest.mark.asyncio
    async def test_generate_without_examples(self, generator, sample_content):
        """例なしでの記事生成テスト."""
        request = GenerationRequest(
            content=sample_content,
            generation_type=GenerationType.ARTICLE,
            options={"style": "formal", "include_examples": False},
            context={"lang": "ja"}
        )
        
        result = await generator.generate(request)
        
        assert result.success is True
        # 例が含まれていないことを確認
        assert "**例：**" not in result.content
        
    @pytest.mark.asyncio
    async def test_generate_invalid_request(self, generator):
        """無効なリクエストでの生成テスト."""
        invalid_request = GenerationRequest(
            content=None,
            generation_type=GenerationType.ARTICLE,
            options={},
            context={}
        )
        
        result = await generator.generate(invalid_request)
        
        assert result.success is False
        assert result.error == "Invalid generation request"
        assert result.content == ""
        
    @pytest.mark.asyncio
    async def test_generate_wrong_type(self, generator, sample_content):
        """間違った生成タイプでのテスト."""
        request = GenerationRequest(
            content=sample_content,
            generation_type=GenerationType.SCRIPT,  # 間違ったタイプ
            options={},
            context={}
        )
        
        result = await generator.generate(request)
        
        assert result.success is False
        assert result.error == "Invalid generation request"
        
    def test_generate_introduction_formal(self, generator):
        """フォーマルスタイルの導入部生成テスト."""
        intro = generator._generate_introduction(
            "テストタイトル", 
            "テストコンテンツです。詳細な説明が含まれています。", 
            "formal"
        )
        
        assert "# テストタイトル" in intro
        assert "本記事では" in intro
        assert "詳細に解説いたします" in intro
        
    def test_generate_introduction_casual(self, generator):
        """カジュアルスタイルの導入部生成テスト."""
        intro = generator._generate_introduction(
            "テストタイトル", 
            "テストコンテンツです。詳細な説明が含まれています。", 
            "casual"
        )
        
        assert "# テストタイトル" in intro
        assert "今回は" in intro
        assert "詳しく見ていきましょう" in intro
        
    def test_generate_conclusion_formal(self, generator):
        """フォーマルスタイルの結論生成テスト."""
        conclusion = generator._generate_conclusion("テストタイトル", "formal")
        
        assert "## 結論" in conclusion
        assert "詳細に検討いたしました" in conclusion
        
    def test_generate_conclusion_casual(self, generator):
        """カジュアルスタイルの結論生成テスト."""
        conclusion = generator._generate_conclusion("テストタイトル", "casual")
        
        assert "## まとめ" in conclusion
        assert "解説してきました" in conclusion
        
    def test_extract_key_points(self, generator):
        """主要ポイント抽出のテスト."""
        content = "第一のポイントです。第二のポイントです。第三のポイントです。第四のポイントです。"
        
        key_points = generator._extract_key_points(content)
        
        assert len(key_points) == 3  # 最大3つまで
        assert all('title' in point for point in key_points)
        assert all('content' in point for point in key_points)
        assert all('example' in point for point in key_points)
        
    def test_extract_article_metadata(self, generator, generation_request):
        """記事メタデータ抽出のテスト."""
        content = """# タイトル

## セクション1
内容1

## セクション2  
内容2

## まとめ
結論"""
        
        metadata = generator._extract_article_metadata(content, generation_request)
        
        assert metadata['article_type'] == 'generated'
        assert metadata['heading_count'] == 7  # #が7つ（# が1つ、## が6つ）
        assert metadata['paragraph_count'] > 0
        assert metadata['estimated_reading_time_minutes'] > 0
        assert metadata['style'] == 'formal'
        assert metadata['target_length'] == 'medium'
        assert metadata['include_examples'] is True
        
    @pytest.mark.asyncio
    async def test_generate_article_content(self, generator, generation_request):
        """記事コンテンツ生成のテスト."""
        prompt = "テスト用プロンプト"
        
        content = await generator._generate_article_content(prompt, generation_request)
        
        assert len(content) > 0
        assert "# プログラミング入門" in content
        assert "## " in content  # セクション見出し
        assert "まとめ" in content or "結論" in content
        
    def test_generate_main_content_with_examples(self, generator):
        """例ありの本文生成テスト."""
        content = "重要なポイント1です。重要なポイント2です。重要なポイント3です。"
        
        main_content = generator._generate_main_content(content, "formal", "medium", True)
        
        assert "## 1." in main_content
        assert "**例：**" in main_content
        
    def test_generate_main_content_without_examples(self, generator):
        """例なしの本文生成テスト."""
        content = "重要なポイント1です。重要なポイント2です。重要なポイント3です。"
        
        main_content = generator._generate_main_content(content, "formal", "medium", False)
        
        assert "## 1." in main_content
        assert "**例：**" not in main_content 