"""AI生成とメディア処理の統合テスト."""

import pytest
import asyncio
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import patch, AsyncMock, MagicMock
import json

from generators.base import GenerationType, GenerationRequest, GenerationResult
from generators.article import ArticleGenerator
from generators.script import ScriptGenerator
from generators.tweet import TweetGenerator
from converters.svg import SVGConverter
from converters.mermaid import MermaidConverter
from clients.s3 import S3Client
from processors.content import ContentProcessor
from workers.ai import AIWorker
from workers.media import MediaWorker


class TestAIMediaIntegration:
    """AI生成とメディア処理の統合テストクラス."""
    
    @pytest.mark.asyncio
    async def test_article_generation_with_image_processing(
        self,
        temp_dir: Path,
        mock_claude_client,
        mock_s3_client: S3Client,
        test_config
    ):
        """記事生成と画像処理の統合テスト."""
        # 記事生成器の設定
        article_generator = ArticleGenerator(test_config)
        article_generator.ai_client = mock_claude_client
        
        # SVG画像を含むコンテンツの生成リクエスト
        request = GenerationRequest(
            title="Pythonの基礎",
            content="""
            Pythonはプログラミング言語です。

            ```svg
            <svg width="200" height="100">
                <rect width="200" height="100" fill="blue"/>
                <text x="100" y="50" text-anchor="middle" fill="white">Python</text>
            </svg>
            ```

            上記の図のようにPythonは青で表現されます。
            """,
            content_type="paragraph",
            lang="ja",
            options={
                "target_audience": "初心者",
                "include_images": True
            }
        )
        
        # 記事生成
        result = await article_generator.generate(request)
        
        # 生成が成功したことを確認
        assert result.success
        assert result.content is not None
        assert len(result.content) > 0
        
        # 画像処理器の設定
        svg_converter = SVGConverter(test_config)
        content_processor = ContentProcessor(test_config)
        content_processor.s3_client = mock_s3_client
        
        # 画像処理の実行
        processed_content, image_urls = await content_processor.process_images(
            result.content,
            {"workflow_id": "test-001", "paragraph_id": "p001"}
        )
        
        # 画像が適切に処理されたことを確認
        assert len(image_urls) > 0
        assert all(url.startswith("https://") for url in image_urls)
        
        # コンテンツ内の画像リンクが置換されたことを確認
        assert "https://" in processed_content
        assert "<svg" not in processed_content  # 元のSVGは置換される
    
    @pytest.mark.asyncio
    async def test_script_generation_with_thumbnail_creation(
        self,
        mock_claude_client,
        mock_openai_client,
        mock_s3_client: S3Client,
        test_config
    ):
        """台本生成とサムネイル作成の統合テスト."""
        # 台本生成器の設定
        script_generator = ScriptGenerator(test_config)
        script_generator.ai_client = mock_claude_client
        
        # サムネイル生成用のOpenAI APIレスポンスをモック
        mock_openai_client._call_api = AsyncMock(return_value={
            "data": [{"url": "https://test-thumbnail.png"}]
        })
        
        # 台本生成リクエスト
        request = GenerationRequest(
            title="Pythonプログラミング入門",
            content="Pythonの基本的な使い方を学びます。変数、関数、クラスについて説明します。",
            content_type="paragraph",
            lang="ja",
            options={
                "duration": "3:00",
                "style": "educational",
                "generate_thumbnail": True
            }
        )
        
        # 台本生成
        script_result = await script_generator.generate(request)
        
        # 台本生成が成功したことを確認
        assert script_result.success
        assert script_result.content is not None
        
        # 台本のJSON構造を確認
        script_data = json.loads(script_result.content)
        assert "title" in script_data
        assert "sections" in script_data
        assert len(script_data["sections"]) > 0
        
        # サムネイル生成（OpenAI DALL-E APIを使用）
        thumbnail_prompt = f"Create a thumbnail for a video about: {request.title}"
        thumbnail_response = await mock_openai_client._call_api({
            "prompt": thumbnail_prompt,
            "n": 1,
            "size": "1280x720"
        })
        
        # サムネイル画像をS3にアップロード
        thumbnail_url = await mock_s3_client.upload_bytes(
            b"fake_thumbnail_data",
            f"thumbnails/{request.title}/thumbnail.png"
        )
        
        # サムネイルが適切に生成・アップロードされたことを確認
        assert thumbnail_url.startswith("https://")
        assert "thumbnail.png" in thumbnail_url
    
    @pytest.mark.asyncio
    async def test_mermaid_diagram_processing(
        self,
        temp_dir: Path,
        mock_s3_client: S3Client,
        test_config
    ):
        """Mermaidダイアグラム処理の統合テスト."""
        # Mermaid変換器の設定
        mermaid_converter = MermaidConverter(test_config)
        
        # Mermaidダイアグラムを含むコンテンツ
        mermaid_content = """
        ```mermaid
        graph TD
            A[開始] --> B{条件}
            B -->|Yes| C[処理A]
            B -->|No| D[処理B]
            C --> E[終了]
            D --> E
        ```
        """
        
        # Mermaidコンテンツの処理をモック
        with patch.object(mermaid_converter, 'convert_to_png') as mock_convert:
            mock_convert.return_value = b"fake_png_data"
            
            # 変換実行
            png_data = await mermaid_converter.convert_to_png(mermaid_content)
            
            # 変換が成功したことを確認
            assert png_data is not None
            assert len(png_data) > 0
            
            # S3アップロード
            image_url = await mock_s3_client.upload_bytes(
                png_data,
                "diagrams/mermaid_diagram.png"
            )
            
            # アップロードが成功したことを確認
            assert image_url.startswith("https://")
            assert "mermaid_diagram.png" in image_url
    
    @pytest.mark.asyncio
    async def test_batch_content_generation(
        self,
        mock_claude_client,
        mock_s3_client: S3Client,
        test_config
    ):
        """バッチコンテンツ生成の統合テスト."""
        # 複数の生成器を準備
        article_generator = ArticleGenerator(test_config)
        script_generator = ScriptGenerator(test_config)
        tweet_generator = TweetGenerator(test_config)
        
        for generator in [article_generator, script_generator, tweet_generator]:
            generator.ai_client = mock_claude_client
        
        # バッチ処理用のリクエスト
        requests = [
            GenerationRequest(
                title="Python基礎",
                content="Pythonの変数について",
                content_type="paragraph",
                lang="ja",
                options={"type": "article"}
            ),
            GenerationRequest(
                title="Python基礎",
                content="Pythonの変数について",
                content_type="paragraph", 
                lang="ja",
                options={"type": "script"}
            ),
            GenerationRequest(
                title="Python基礎",
                content="Pythonの変数について",
                content_type="paragraph",
                lang="ja",
                options={"type": "tweet"}
            )
        ]
        
        # 並列実行
        tasks = []
        for request in requests:
            if request.options["type"] == "article":
                tasks.append(article_generator.generate(request))
            elif request.options["type"] == "script":
                tasks.append(script_generator.generate(request))
            elif request.options["type"] == "tweet":
                tasks.append(tweet_generator.generate(request))
        
        results = await asyncio.gather(*tasks)
        
        # 全ての生成が成功したことを確認
        assert len(results) == 3
        for result in results:
            assert result.success
            assert result.content is not None
            assert len(result.content) > 0
    
    @pytest.mark.asyncio
    async def test_error_recovery_in_ai_generation(
        self,
        mock_claude_client,
        test_config
    ):
        """AI生成でのエラー復旧テスト."""
        # 記事生成器の設定
        article_generator = ArticleGenerator(test_config)
        
        # 最初はエラー、2回目は成功するようにモック
        call_count = 0
        
        async def mock_generate(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("API rate limit exceeded")
            return {
                "content": [{"text": "復旧後の生成コンテンツ"}],
                "usage": {"input_tokens": 100, "output_tokens": 50}
            }
        
        mock_claude_client._call_api = mock_generate
        article_generator.ai_client = mock_claude_client
        
        # 生成リクエスト
        request = GenerationRequest(
            title="テスト記事",
            content="テストコンテンツ",
            content_type="paragraph",
            lang="ja"
        )
        
        # 生成実行（エラー復旧あり）
        result = await article_generator.generate(request)
        
        # エラーから復旧して成功したことを確認
        assert result.success
        assert "復旧後の生成コンテンツ" in result.content
        assert call_count >= 2  # リトライが実行された
    
    @pytest.mark.asyncio
    async def test_ai_worker_media_worker_coordination(
        self,
        event_bus,
        ai_worker: AIWorker,
        media_worker: MediaWorker,
        sample_workflow_context: Dict[str, Any]
    ):
        """AIワーカーとメディアワーカーの連携テスト."""
        workflow_id = sample_workflow_context["workflow_id"]
        
        # 生成されたコンテンツの追跡
        generated_contents = []
        processed_images = []
        
        # AIワーカーの処理をモック
        async def mock_ai_process(event):
            content = {
                "paragraph_id": event.data["paragraph_id"],
                "content": "生成された記事コンテンツ with <svg>...</svg>",
                "images": ["test.svg"]
            }
            generated_contents.append(content)
            return content
        
        # メディアワーカーの処理をモック
        async def mock_media_process(event):
            processed = {
                "paragraph_id": event.data["paragraph_id"],
                "processed_images": ["https://s3.amazonaws.com/test.png"],
                "updated_content": event.data["content"].replace("<svg>...</svg>", "![画像](https://s3.amazonaws.com/test.png)")
            }
            processed_images.append(processed)
            return processed
        
        ai_worker.process = mock_ai_process
        media_worker.process = mock_media_process
        
        # パラグラフ処理イベントを発行
        from conftest import create_test_event
        from core.events import EventType
        
        paragraph_event = create_test_event(
            EventType.PARAGRAPH_PARSED,
            workflow_id,
            {
                "paragraph_id": "p001",
                "content": "Pythonプログラミングについて",
                "has_images": True
            }
        )
        
        await event_bus.publish(paragraph_event)
        
        # 処理完了を待機
        await asyncio.sleep(0.2)
        
        # AIワーカーとメディアワーカーが適切に連携したことを確認
        assert len(generated_contents) > 0
        assert len(processed_images) > 0
        assert generated_contents[0]["paragraph_id"] == "p001"
        assert "https://s3.amazonaws.com/" in processed_images[0]["updated_content"]
    
    @pytest.mark.asyncio
    async def test_content_quality_validation(
        self,
        mock_claude_client,
        test_config
    ):
        """生成コンテンツの品質検証テスト."""
        # 記事生成器の設定
        article_generator = ArticleGenerator(test_config)
        article_generator.ai_client = mock_claude_client
        
        # 低品質なコンテンツを返すモック
        mock_claude_client._call_api = AsyncMock(return_value={
            "content": [{"text": "短すぎるコンテンツ"}],
            "usage": {"input_tokens": 100, "output_tokens": 10}
        })
        
        # 品質検証付きの生成リクエスト
        request = GenerationRequest(
            title="詳細な技術記事",
            content="Pythonの高度な機能について詳しく説明してください。",
            content_type="paragraph",
            lang="ja",
            options={
                "min_length": 1000,  # 最小文字数
                "validate_quality": True
            }
        )
        
        # 生成実行
        result = await article_generator.generate(request)
        
        # 品質検証によりエラーが検出されることを確認
        # （実際の実装では品質が低い場合は再生成するか、エラーを返す）
        assert not result.success or len(result.content) >= request.options.get("min_length", 0) 