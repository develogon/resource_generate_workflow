"""AIWorker のテスト."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path

from src.workers.ai import AIWorker, GenerationRequest
from src.workers.base import Event, EventType
from src.config import Config


@pytest.fixture
def config():
    """テスト用設定."""
    config = Config()
    config.workers.max_concurrent_tasks = 2
    config.max_retries = 3
    return config


@pytest.fixture
def ai_worker(config):
    """テスト用AIワーカー."""
    return AIWorker(config, "ai-test-1")


@pytest.fixture
def event_bus():
    """テスト用イベントバス."""
    bus = Mock()
    bus.subscribe = AsyncMock()
    bus.publish = AsyncMock()
    return bus


@pytest.fixture
def state_manager():
    """テスト用状態管理."""
    manager = Mock()
    manager.save_checkpoint = AsyncMock()
    return manager


@pytest.fixture
def metrics():
    """テスト用メトリクス."""
    metrics = Mock()
    metrics.record_processing_time = Mock()
    metrics.record_error = Mock()
    return metrics


@pytest.fixture
def section_parsed_event():
    """セクション解析済みイベント."""
    return Event(
        event_type=EventType.SECTION_PARSED,
        workflow_id="test-workflow-1",
        data={
            "section": {
                "title": "テストセクション",
                "level": 2,
                "content": "これはテストセクションの内容です。API について説明します。",
                "paragraphs": [
                    {
                        "index": 0,
                        "content": "APIの基本概念",
                        "type": "paragraph",
                        "word_count": 5
                    }
                ]
            },
            "chapter": {
                "title": "第1章 テスト",
                "level": 1
            }
        },
        trace_id="trace-123"
    )


@pytest.fixture
def paragraph_parsed_event():
    """パラグラフ解析済みイベント."""
    return Event(
        event_type=EventType.PARAGRAPH_PARSED,
        workflow_id="test-workflow-1",
        data={
            "paragraph": {
                "index": 0,
                "content": "これはテストパラグラフです。データベース について説明します。",
                "type": "paragraph",
                "word_count": 8
            },
            "section": {
                "title": "テストセクション",
                "level": 2,
                "content": "セクション内容"
            }
        },
        trace_id="trace-123"
    )


@pytest.fixture
def chapter_aggregated_event():
    """チャプター集約済みイベント."""
    return Event(
        event_type=EventType.CHAPTER_AGGREGATED,
        workflow_id="test-workflow-1",
        data={
            "chapter": {
                "title": "第1章 テスト",
                "level": 1,
                "content": "チャプター内容",
                "sections": [
                    {
                        "title": "セクション1",
                        "paragraphs": [{"content": "パラグラフ1"}]
                    },
                    {
                        "title": "セクション2", 
                        "paragraphs": [{"content": "パラグラフ2"}]
                    }
                ]
            }
        },
        trace_id="trace-123"
    )


@pytest.fixture
def structure_analyzed_event():
    """構造解析済みイベント."""
    return Event(
        event_type=EventType.STRUCTURE_ANALYZED,
        workflow_id="test-workflow-1",
        data={
            "section": {
                "title": "テストセクション",
                "content": "セクション内容"
            },
            "analysis": {
                "content_type": "technical",
                "complexity_level": "moderate",
                "key_concepts": ["API", "database"]
            }
        },
        trace_id="trace-123"
    )


class TestAIWorker:
    """AIWorker のテスト."""
    
    def test_init(self, ai_worker, config):
        """初期化のテスト."""
        assert ai_worker.config == config
        assert ai_worker.worker_id == "ai-test-1"
        assert ai_worker.semaphore._value == config.workers.max_concurrent_tasks
        assert ai_worker.running is False
        assert ai_worker.claude_client is None
        assert ai_worker.openai_client is None
        assert ai_worker.rate_limiter is None
        
    def test_get_subscriptions(self, ai_worker):
        """購読イベントタイプのテスト."""
        subscriptions = ai_worker.get_subscriptions()
        expected_subscriptions = {
            EventType.SECTION_PARSED,
            EventType.PARAGRAPH_PARSED,
            EventType.CHAPTER_AGGREGATED,
            EventType.STRUCTURE_ANALYZED
        }
        assert subscriptions == expected_subscriptions
        
    @pytest.mark.asyncio
    async def test_start(self, ai_worker, event_bus, state_manager, metrics):
        """ワーカー起動のテスト."""
        await ai_worker.start(event_bus, state_manager, metrics)
        
        assert ai_worker.running is True
        assert ai_worker.event_bus == event_bus
        assert ai_worker.state_manager == state_manager
        assert ai_worker.metrics == metrics
        
        # 購読が正しく行われたかチェック
        assert event_bus.subscribe.call_count == 4
        
    @pytest.mark.asyncio
    async def test_process_section_parsed(self, ai_worker, section_parsed_event, event_bus):
        """セクション解析イベント処理のテスト."""
        ai_worker.event_bus = event_bus
        
        await ai_worker.process(section_parsed_event)
        
        # 構造解析完了イベントが発行されたかチェック
        assert event_bus.publish.call_count == 1
        
        # 発行されたイベントの確認
        published_event = event_bus.publish.call_args[0][0]
        assert published_event.type == EventType.STRUCTURE_ANALYZED
        assert 'analysis' in published_event.data
        
    @pytest.mark.asyncio
    async def test_process_paragraph_parsed(self, ai_worker, paragraph_parsed_event, event_bus):
        """パラグラフ解析イベント処理のテスト."""
        ai_worker.event_bus = event_bus
        
        await ai_worker.process(paragraph_parsed_event)
        
        # 複数のコンテンツ生成イベントが発行されたかチェック
        assert event_bus.publish.call_count >= 4  # article, script, script_json, tweet, description
        
        # 発行されたイベントがすべてCONTENT_GENERATEDタイプかチェック
        for call in event_bus.publish.call_args_list:
            event = call[0][0]
            assert event.type == EventType.CONTENT_GENERATED
            assert 'content' in event.data
            assert 'paragraph' in event.data
            
    @pytest.mark.asyncio
    async def test_process_chapter_aggregated(self, ai_worker, chapter_aggregated_event, event_bus):
        """チャプター集約イベント処理のテスト."""
        ai_worker.event_bus = event_bus
        
        await ai_worker.process(chapter_aggregated_event)
        
        # メタデータ生成イベントが発行されたかチェック
        assert event_bus.publish.call_count == 1
        
        # 発行されたイベントの確認
        published_event = event_bus.publish.call_args[0][0]
        assert published_event.type == EventType.METADATA_GENERATED
        assert 'metadata' in published_event.data
        assert 'thumbnail' in published_event.data
        
    @pytest.mark.asyncio
    async def test_process_structure_analyzed(self, ai_worker, structure_analyzed_event):
        """構造解析イベント処理のテスト."""
        # エラーが発生しないことを確認
        await ai_worker.process(structure_analyzed_event)
        
    @pytest.mark.asyncio
    async def test_process_unknown_event(self, ai_worker):
        """未知のイベントタイプ処理のテスト."""
        unknown_event = Event(
            event_type="unknown.event",
            workflow_id="test-workflow-1",
            data={}
        )
        
        # エラーが発生しないことを確認
        await ai_worker.process(unknown_event)
        
    @pytest.mark.asyncio
    async def test_handle_section_parsed_no_section(self, ai_worker):
        """セクションデータなしのセクション解析イベント処理のテスト."""
        event = Event(
            event_type=EventType.SECTION_PARSED,
            workflow_id="test-workflow-1",
            data={}  # section データなし
        )
        
        with pytest.raises(ValueError, match="No section data provided"):
            await ai_worker._handle_section_parsed(event)
            
    @pytest.mark.asyncio
    async def test_handle_paragraph_parsed_no_paragraph(self, ai_worker):
        """パラグラフデータなしのパラグラフ解析イベント処理のテスト."""
        event = Event(
            event_type=EventType.PARAGRAPH_PARSED,
            workflow_id="test-workflow-1",
            data={}  # paragraph データなし
        )
        
        with pytest.raises(ValueError, match="No paragraph data provided"):
            await ai_worker._handle_paragraph_parsed(event)
            
    @pytest.mark.asyncio
    async def test_handle_chapter_aggregated_no_chapter(self, ai_worker):
        """チャプターデータなしのチャプター集約イベント処理のテスト."""
        event = Event(
            event_type=EventType.CHAPTER_AGGREGATED,
            workflow_id="test-workflow-1",
            data={}  # chapter データなし
        )
        
        with pytest.raises(ValueError, match="No chapter data provided"):
            await ai_worker._handle_chapter_aggregated(event)
            
    @pytest.mark.asyncio
    async def test_analyze_section_structure(self, ai_worker):
        """セクション構造解析のテスト."""
        section_data = {
            "title": "API概要",
            "content": "このセクションではAPI の基本的な使い方について説明します。例 を示しながら解説していきます。",
            "paragraphs": [
                {"content": "パラグラフ1"},
                {"content": "パラグラフ2"}
            ]
        }
        
        analysis = await ai_worker._analyze_section_structure(section_data)
        
        assert analysis["content_type"] in ["technical", "example", "overview", "general"]
        assert analysis["complexity_level"] in ["simple", "moderate", "complex"]
        assert isinstance(analysis["key_concepts"], list)
        assert analysis["paragraph_count"] == 2
        assert isinstance(analysis["estimated_reading_time"], int)
        assert isinstance(analysis["recommended_formats"], list)
        
    @pytest.mark.asyncio
    async def test_generate_article(self, ai_worker):
        """記事生成のテスト."""
        paragraph_data = {
            "content": "テストコンテンツです。",
            "index": 0
        }
        section_data = {
            "title": "テストセクション"
        }
        
        result = await ai_worker._generate_article(paragraph_data, section_data)
        
        assert result is not None
        assert result["type"] == "article"
        assert "title" in result
        assert "content" in result
        assert "word_count" in result
        assert result["format"] == "markdown"
        
    @pytest.mark.asyncio
    async def test_generate_script(self, ai_worker):
        """台本生成のテスト."""
        paragraph_data = {
            "content": "テストコンテンツです。",
            "index": 0
        }
        section_data = {
            "title": "テストセクション"
        }
        
        result = await ai_worker._generate_script(paragraph_data, section_data)
        
        assert result is not None
        assert result["type"] == "script"
        assert "title" in result
        assert "content" in result
        assert "estimated_duration" in result
        assert result["format"] == "text"
        
    @pytest.mark.asyncio
    async def test_generate_script_json(self, ai_worker):
        """JSON台本生成のテスト."""
        paragraph_data = {
            "content": "テストコンテンツです。",
            "index": 0
        }
        section_data = {
            "title": "テストセクション"
        }
        
        result = await ai_worker._generate_script_json(paragraph_data, section_data)
        
        assert result is not None
        assert result["type"] == "script_json"
        assert "title" in result
        assert "content" in result
        assert "scenes" in result["content"]
        assert "total_duration" in result["content"]
        assert result["format"] == "json"
        
    @pytest.mark.asyncio
    async def test_generate_tweet(self, ai_worker):
        """ツイート生成のテスト."""
        paragraph_data = {
            "content": "テストコンテンツです。",
            "index": 0
        }
        section_data = {
            "title": "テストセクション"
        }
        
        result = await ai_worker._generate_tweet(paragraph_data, section_data)
        
        assert result is not None
        assert result["type"] == "tweet"
        assert "content" in result
        assert result["character_count"] <= 280  # Twitter文字制限
        assert "hashtags" in result
        assert result["format"] == "text"
        
    @pytest.mark.asyncio
    async def test_generate_description(self, ai_worker):
        """説明文生成のテスト."""
        paragraph_data = {
            "content": "テストコンテンツです。",
            "index": 0
        }
        section_data = {
            "title": "テストセクション"
        }
        
        result = await ai_worker._generate_description(paragraph_data, section_data)
        
        assert result is not None
        assert result["type"] == "description"
        assert "title" in result
        assert "content" in result
        assert "summary" in result
        assert result["format"] == "markdown"
        
    @pytest.mark.asyncio
    async def test_generate_chapter_metadata(self, ai_worker):
        """チャプターメタデータ生成のテスト."""
        chapter_data = {
            "title": "第1章 テスト",
            "content": "チャプター内容です。",
            "sections": [
                {
                    "title": "セクション1",
                    "paragraphs": [{"content": "パラグラフ1"}, {"content": "パラグラフ2"}]
                },
                {
                    "title": "セクション2",
                    "paragraphs": [{"content": "パラグラフ3"}]
                }
            ]
        }
        
        metadata = await ai_worker._generate_chapter_metadata(chapter_data)
        
        assert metadata["title"] == "第1章 テスト"
        assert metadata["section_count"] == 2
        assert metadata["total_paragraphs"] == 3
        assert isinstance(metadata["estimated_reading_time"], int)
        assert "difficulty_level" in metadata
        assert "generated_at" in metadata
        
    @pytest.mark.asyncio
    async def test_generate_thumbnail(self, ai_worker):
        """サムネイル生成のテスト."""
        chapter_data = {
            "title": "第1章 テスト"
        }
        
        thumbnail_data = await ai_worker._generate_thumbnail(chapter_data)
        
        assert thumbnail_data is not None
        assert thumbnail_data["type"] == "thumbnail"
        assert thumbnail_data["title"] == "第1章 テスト"
        assert "style" in thumbnail_data
        assert "dimensions" in thumbnail_data
        assert thumbnail_data["format"] == "png"
        
    def test_classify_content_type(self, ai_worker):
        """コンテンツタイプ分類のテスト."""
        test_cases = [
            ("This explains about API functionality.", "technical"),
            ("```python\nprint('hello')\n```", "technical"),
            ("Here is an example of usage.", "example"), 
            ("This is an overview of the system.", "overview"),
            ("一般的な内容です。", "general")
        ]
        
        for content, expected_type in test_cases:
            result = ai_worker._classify_content_type(content)
            assert result == expected_type, f"Failed for content: {content}"
            
    def test_assess_complexity(self, ai_worker):
        """複雑さ評価のテスト."""
        test_cases = [
            ("短い", "simple"),
            ("This is a moderate length text with multiple words and sentences to reach the moderate complexity level. " * 3, "moderate"),
            ("This is a very long text that contains many words and sentences. " * 20, "complex")
        ]
        
        for content, expected_complexity in test_cases:
            result = ai_worker._assess_complexity(content)
            assert result == expected_complexity, f"Failed for content length: {len(content.split())}"
            
    def test_extract_key_concepts(self, ai_worker):
        """キーコンセプト抽出のテスト."""
        content = "このAPIはdatabaseからデータを取得し、serverに送信します。algorithmを使用してclientに返します。"
        
        concepts = ai_worker._extract_key_concepts(content)
        
        assert isinstance(concepts, list)
        assert len(concepts) <= 5
        expected_concepts = ["API", "database", "server", "algorithm", "client"]
        for concept in concepts:
            assert concept in expected_concepts
            
    def test_estimate_reading_time(self, ai_worker):
        """読書時間推定のテスト."""
        test_cases = [
            ("短いテキスト", 1),  # 最小値
            ("単語 " * 100, 1),   # 100単語
            ("単語 " * 400, 2),   # 400単語
        ]
        
        for content, expected_time in test_cases:
            result = ai_worker._estimate_reading_time(content)
            assert result == expected_time
            
    def test_recommend_formats(self, ai_worker):
        """推奨フォーマット決定のテスト."""
        test_cases = [
            ("APIについて説明します。", ["technical"]),
            ("概要を説明します。", ["overview"]),
            ("一般的な内容です。", ["general"])
        ]
        
        for content, expected_types in test_cases:
            formats = ai_worker._recommend_formats(content)
            assert isinstance(formats, list)
            assert len(formats) >= 2  # 基本的に['article', 'description']は含まれる
            
    @pytest.mark.asyncio
    async def test_content_generation_error_handling(self, ai_worker, event_bus):
        """コンテンツ生成エラーハンドリングのテスト."""
        ai_worker.event_bus = event_bus
        
        # _generate_articleメソッドをモックしてエラーを発生させる
        with patch.object(ai_worker, '_generate_article', side_effect=Exception("Test error")):
            paragraph_data = {"content": "test", "index": 0}
            section_data = {"title": "test"}
            
            # エラーが発生してもプロセス全体は続行される
            await ai_worker._handle_paragraph_parsed(Event(
                event_type=EventType.PARAGRAPH_PARSED,
                workflow_id="test",
                data={"paragraph": paragraph_data, "section": section_data}
            ))
            
            # 他の生成タスクは正常に実行され、イベントが発行される
            assert event_bus.publish.call_count >= 3  # エラーが1つあっても他は成功
            
    @pytest.mark.asyncio
    async def test_generation_request_structure(self):
        """GenerationRequestデータ構造のテスト."""
        request = GenerationRequest(
            content_type="article",
            input_data={"content": "test"},
            context={"section": "test"}
        )
        
        assert request.content_type == "article"
        assert request.input_data["content"] == "test"
        assert request.context["section"] == "test"
        assert request.options is None
        
        # オプション付き
        request_with_options = GenerationRequest(
            content_type="script",
            input_data={"content": "test"},
            context={"section": "test"},
            options={"duration": 120}
        )
        
        assert request_with_options.options["duration"] == 120 