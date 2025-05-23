"""ParserWorker のテスト."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path

from src.workers.parser import ParserWorker
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
def parser_worker(config):
    """テスト用パーサーワーカー."""
    return ParserWorker(config, "parser-test-1")


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
def workflow_started_event():
    """ワークフロー開始イベント."""
    return Event(
        event_type=EventType.WORKFLOW_STARTED,
        workflow_id="test-workflow-1",
        data={
            "content": {
                "title": "テストドキュメント",
                "text": """# 第1章 はじめに

これは第1章の内容です。

## 1.1 概要

第1章の1節です。

これは最初のパラグラフです。

これは2番目のパラグラフです。

## 1.2 詳細

第1章の2節です。

### 1.2.1 サブセクション

サブセクション内容。

# 第2章 応用

これは第2章の内容です。

## 2.1 基本応用

第2章の1節です。"""
            }
        },
        trace_id="trace-123"
    )


@pytest.fixture
def chapter_parsed_event():
    """チャプター解析済みイベント."""
    return Event(
        event_type=EventType.CHAPTER_PARSED,
        workflow_id="test-workflow-1",
        data={
            "chapter": {
                "title": "第1章 はじめに",
                "level": 1,
                "content": """## 1.1 概要

第1章の1節です。

これは最初のパラグラフです。

これは2番目のパラグラフです。

## 1.2 詳細

第1章の2節です。""",
                "sections": [
                    {
                        "title": "概要",
                        "level": 2,
                        "content": "第1章の1節です。\n\nこれは最初のパラグラフです。\n\nこれは2番目のパラグラフです。"
                    }
                ]
            }
        },
        trace_id="trace-123"
    )


@pytest.fixture
def section_parsed_event():
    """セクション解析済みイベント."""
    return Event(
        event_type=EventType.SECTION_PARSED,
        workflow_id="test-workflow-1",
        data={
            "section": {
                "title": "概要",
                "level": 2,
                "content": "第1章の1節です。\n\nこれは最初のパラグラフです。\n\nこれは2番目のパラグラフです。",
                "paragraphs": [
                    {
                        "index": 0,
                        "content": "第1章の1節です。",
                        "type": "paragraph",
                        "word_count": 6
                    },
                    {
                        "index": 1,
                        "content": "これは最初のパラグラフです。",
                        "type": "paragraph",
                        "word_count": 9
                    }
                ]
            },
            "chapter": {
                "title": "第1章 はじめに",
                "level": 1
            }
        },
        trace_id="trace-123"
    )


class TestParserWorker:
    """ParserWorker のテスト."""
    
    def test_init(self, parser_worker, config):
        """初期化のテスト."""
        assert parser_worker.config == config
        assert parser_worker.worker_id == "parser-test-1"
        assert parser_worker.semaphore._value == config.workers.max_concurrent_tasks
        assert parser_worker.running is False
        
    def test_get_subscriptions(self, parser_worker):
        """購読イベントタイプのテスト."""
        subscriptions = parser_worker.get_subscriptions()
        expected_subscriptions = {
            EventType.WORKFLOW_STARTED,
            EventType.CHAPTER_PARSED,
            EventType.SECTION_PARSED
        }
        assert subscriptions == expected_subscriptions
        
    @pytest.mark.asyncio
    async def test_start(self, parser_worker, event_bus, state_manager, metrics):
        """ワーカー起動のテスト."""
        await parser_worker.start(event_bus, state_manager, metrics)
        
        assert parser_worker.running is True
        assert parser_worker.event_bus == event_bus
        assert parser_worker.state_manager == state_manager
        assert parser_worker.metrics == metrics
        
        # 購読が正しく行われたかチェック
        assert event_bus.subscribe.call_count == 3
        
    @pytest.mark.asyncio
    async def test_process_workflow_started(self, parser_worker, workflow_started_event, event_bus):
        """ワークフロー開始イベント処理のテスト."""
        parser_worker.event_bus = event_bus
        
        await parser_worker.process(workflow_started_event)
        
        # 構造解析完了イベントが発行されたかチェック
        assert event_bus.publish.call_count >= 1
        
        # チャプター解析イベントが発行されたかチェック（2章分）
        calls = [call for call in event_bus.publish.call_args_list 
                if call[0][0].type == EventType.CHAPTER_PARSED]
        assert len(calls) == 2
        
    @pytest.mark.asyncio
    async def test_process_chapter_parsed(self, parser_worker, chapter_parsed_event, event_bus):
        """チャプター解析イベント処理のテスト."""
        parser_worker.event_bus = event_bus
        
        await parser_worker.process(chapter_parsed_event)
        
        # セクション解析イベントが発行されたかチェック
        calls = [call for call in event_bus.publish.call_args_list 
                if call[0][0].type == EventType.SECTION_PARSED]
        assert len(calls) >= 1
        
    @pytest.mark.asyncio
    async def test_process_section_parsed(self, parser_worker, section_parsed_event, event_bus):
        """セクション解析イベント処理のテスト."""
        parser_worker.event_bus = event_bus
        
        await parser_worker.process(section_parsed_event)
        
        # パラグラフ解析イベントが発行されたかチェック
        calls = [call for call in event_bus.publish.call_args_list 
                if call[0][0].type == EventType.PARAGRAPH_PARSED]
        assert len(calls) >= 1
        
    @pytest.mark.asyncio
    async def test_process_unknown_event(self, parser_worker):
        """未知のイベントタイプ処理のテスト."""
        unknown_event = Event(
            event_type="unknown.event",
            workflow_id="test-workflow-1",
            data={}
        )
        
        # エラーが発生しないことを確認
        await parser_worker.process(unknown_event)
        
    @pytest.mark.asyncio
    async def test_handle_workflow_started_no_content(self, parser_worker):
        """コンテンツデータなしのワークフロー開始イベント処理のテスト."""
        event = Event(
            event_type=EventType.WORKFLOW_STARTED,
            workflow_id="test-workflow-1",
            data={}  # content データなし
        )
        
        with pytest.raises(ValueError, match="No content data provided"):
            await parser_worker._handle_workflow_started(event)
            
    @pytest.mark.asyncio
    async def test_handle_chapter_parsed_no_chapter(self, parser_worker):
        """チャプターデータなしのチャプター解析イベント処理のテスト."""
        event = Event(
            event_type=EventType.CHAPTER_PARSED,
            workflow_id="test-workflow-1",
            data={}  # chapter データなし
        )
        
        with pytest.raises(ValueError, match="No chapter data provided"):
            await parser_worker._handle_chapter_parsed(event)
            
    @pytest.mark.asyncio
    async def test_handle_section_parsed_no_section(self, parser_worker):
        """セクションデータなしのセクション解析イベント処理のテスト."""
        event = Event(
            event_type=EventType.SECTION_PARSED,
            workflow_id="test-workflow-1",
            data={}  # section データなし
        )
        
        with pytest.raises(ValueError, match="No section data provided"):
            await parser_worker._handle_section_parsed(event)
            
    def test_analyze_content_structure(self, parser_worker):
        """コンテンツ構造解析のテスト."""
        content_data = {
            "title": "テストドキュメント",
            "text": """# 第1章 はじめに

第1章の内容です。

## 1.1 概要

概要セクションです。

# 第2章 応用

第2章の内容です。"""
        }
        
        structure = asyncio.run(parser_worker._analyze_content_structure(content_data))
        
        assert structure["type"] == "document"
        assert structure["title"] == "テストドキュメント"
        assert len(structure["chapters"]) == 2
        assert structure["chapters"][0]["title"] == "第1章 はじめに"
        assert structure["chapters"][1]["title"] == "第2章 応用"
        assert structure["metadata"]["estimated_chapters"] == 2
        
    def test_extract_chapters(self, parser_worker):
        """チャプター抽出のテスト."""
        content = """# 第1章 はじめに

第1章の内容です。

## 1.1 概要

概要です。

# 第2章 応用

第2章の内容です。

## 2.1 基本

基本です。"""
        
        chapters = parser_worker._extract_chapters(content)
        
        assert len(chapters) == 2
        assert chapters[0]["title"] == "第1章 はじめに"
        assert chapters[0]["level"] == 1
        assert chapters[1]["title"] == "第2章 応用"
        assert chapters[1]["level"] == 1
        
        # セクションも抽出されていることを確認
        assert len(chapters[0]["sections"]) >= 1
        assert chapters[0]["sections"][0]["title"] == "1.1 概要"
        
    def test_extract_chapters_no_headers(self, parser_worker):
        """見出しなしのコンテンツでのチャプター抽出のテスト."""
        content = "これは普通のテキストです。見出しはありません。"
        
        chapters = parser_worker._extract_chapters(content)
        
        # デフォルトの1チャプターが作成されることを確認
        assert len(chapters) == 1
        assert chapters[0]["title"] == "Main Content"
        assert chapters[0]["level"] == 1
        assert chapters[0]["content"] == content
        
    def test_extract_sections(self, parser_worker):
        """セクション抽出のテスト."""
        content = """## 1.1 概要

概要セクションです。

段落1です。

段落2です。

## 1.2 詳細

詳細セクションです。

### 1.2.1 サブセクション

サブセクション内容。"""
        
        sections = parser_worker._extract_sections(content)
        
        assert len(sections) == 2
        assert sections[0]["title"] == "1.1 概要"
        assert sections[0]["level"] == 2
        assert sections[1]["title"] == "1.2 詳細"
        assert sections[1]["level"] == 2
        
        # パラグラフも抽出されていることを確認
        assert len(sections[0]["paragraphs"]) >= 2
        
    def test_extract_sections_no_headers(self, parser_worker):
        """見出しなしのコンテンツでのセクション抽出のテスト."""
        content = "これは普通のテキストです。見出しはありません。"
        
        sections = parser_worker._extract_sections(content)
        
        # デフォルトの1セクションが作成されることを確認
        assert len(sections) == 1
        assert sections[0]["title"] == "Main Section"
        assert sections[0]["level"] == 2
        assert sections[0]["content"] == content
        
    def test_extract_paragraphs(self, parser_worker):
        """パラグラフ抽出のテスト."""
        content = """第1パラグラフです。

第2パラグラフです。これは少し長いパラグラフになっています。

### サブ見出し

- リスト項目1
- リスト項目2

> 引用文です。

```python
code_block = "コードブロック"
```

短い文。"""
        
        paragraphs = parser_worker._extract_paragraphs(content)
        
        assert len(paragraphs) >= 5
        
        # 各パラグラフの基本構造を確認
        for i, para in enumerate(paragraphs):
            assert para["index"] == i
            assert "content" in para
            assert "type" in para
            assert "word_count" in para
            
    def test_classify_paragraph_type(self, parser_worker):
        """パラグラフタイプ分類のテスト."""
        test_cases = [
            ("### 見出し", "heading3"),
            ("- リスト項目", "list"),
            ("* リスト項目", "list"),
            ("> 引用文", "quote"),
            ("```\ncode\n```", "code"),
            ("短い", "short"),
            ("This is a normal paragraph with multiple words and sufficient length to be classified as paragraph type", "paragraph")
        ]
        
        for text, expected_type in test_cases:
            result = parser_worker._classify_paragraph_type(text)
            assert result == expected_type, f"Failed for text: {text}"
            
    @pytest.mark.asyncio
    async def test_parse_chapter_sections(self, parser_worker):
        """チャプターセクション解析のテスト."""
        chapter_data = {
            "sections": [
                {"title": "セクション1", "content": "内容1"},
                {"title": "セクション2", "content": "内容2"}
            ]
        }
        
        sections = await parser_worker._parse_chapter_sections(chapter_data)
        
        assert len(sections) == 2
        assert sections[0]["title"] == "セクション1"
        assert sections[1]["title"] == "セクション2"
        
    @pytest.mark.asyncio
    async def test_parse_section_paragraphs(self, parser_worker):
        """セクションパラグラフ解析のテスト."""
        section_data = {
            "paragraphs": [
                {"index": 0, "content": "パラグラフ1"},
                {"index": 1, "content": "パラグラフ2"}
            ]
        }
        
        paragraphs = await parser_worker._parse_section_paragraphs(section_data)
        
        assert len(paragraphs) == 2
        assert paragraphs[0]["content"] == "パラグラフ1"
        assert paragraphs[1]["content"] == "パラグラフ2"
        
    @pytest.mark.asyncio
    async def test_full_workflow_integration(self, parser_worker, event_bus):
        """フルワークフロー統合テスト."""
        parser_worker.event_bus = event_bus
        
        # ワークフロー開始イベントから開始
        workflow_event = Event(
            event_type=EventType.WORKFLOW_STARTED,
            workflow_id="integration-test",
            data={
                "content": {
                    "title": "統合テスト",
                    "text": """# 第1章 テスト

テスト内容です。

## 1.1 テストセクション

セクション内容です。

パラグラフ1です。

パラグラフ2です。"""
                }
            }
        )
        
        await parser_worker.process(workflow_event)
        
        # 複数のイベントが発行されたことを確認
        assert event_bus.publish.call_count >= 2  # 最低でも構造解析とチャプター解析
        
        # 発行されたイベントの種類を確認
        event_types = [call[0][0].type for call in event_bus.publish.call_args_list]
        assert EventType.STRUCTURE_ANALYZED in event_types
        assert EventType.CHAPTER_PARSED in event_types 