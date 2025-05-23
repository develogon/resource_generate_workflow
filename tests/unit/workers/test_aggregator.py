"""AggregatorWorker のテスト."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timedelta

from src.workers.aggregator import AggregatorWorker, AggregationResult, WorkflowState
from src.workers.base import Event, EventType
from src.workers.media import ProcessedImage, ImageType
from src.config import Config


@pytest.fixture
def config():
    """テスト用設定."""
    config = Config()
    config.workers.max_concurrent_tasks = 2
    config.max_retries = 3
    return config


@pytest.fixture
def aggregator_worker(config):
    """テスト用集約ワーカー."""
    return AggregatorWorker(config, "aggregator-test-1")


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
def structure_analyzed_event():
    """構造解析済みイベント."""
    return Event(
        event_type=EventType.STRUCTURE_ANALYZED,
        workflow_id="test-workflow-1",
        data={
            "structure": {
                "type": "document",
                "title": "テストドキュメント",
                "chapters": [
                    {
                        "title": "第1章 はじめに",
                        "level": 1,
                        "sections": [
                            {"title": "1.1 概要", "level": 2},
                            {"title": "1.2 詳細", "level": 2}
                        ]
                    },
                    {
                        "title": "第2章 応用",
                        "level": 1,
                        "sections": [
                            {"title": "2.1 基本応用", "level": 2}
                        ]
                    }
                ]
            }
        },
        trace_id="trace-123"
    )


@pytest.fixture
def content_generated_event():
    """コンテンツ生成済みイベント."""
    return Event(
        event_type=EventType.CONTENT_GENERATED,
        workflow_id="test-workflow-1",
        data={
            "content": {
                "type": "article",
                "title": "記事: テストセクション",
                "content": "これはテスト記事の内容です。",
                "word_count": 15,
                "format": "markdown"
            },
            "paragraph": {
                "index": 0,
                "content": "テストパラグラフ",
                "type": "paragraph",
                "word_count": 5
            },
            "section": {
                "title": "テストセクション",
                "level": 2
            }
        },
        trace_id="trace-123"
    )


@pytest.fixture
def image_processed_event():
    """画像処理済みイベント."""
    processed_image = ProcessedImage(
        original_type=ImageType.SVG,
        processed_data=b"fake_image_data",
        format="png",
        width=800,
        height=600,
        file_size=1024,
        metadata={
            "s3_url": "https://test-bucket.s3.amazonaws.com/image.png",
            "workflow_id": "test-workflow-1",
            "processed_at": datetime.now().timestamp()
        }
    )
    
    return Event(
        event_type=EventType.IMAGE_PROCESSED,
        workflow_id="test-workflow-1",
        data={
            "processed_images": [processed_image],
            "original_content": {
                "type": "article",
                "content": "テスト記事"
            }
        },
        trace_id="trace-123"
    )


@pytest.fixture
def metadata_generated_event():
    """メタデータ生成済みイベント."""
    return Event(
        event_type=EventType.METADATA_GENERATED,
        workflow_id="test-workflow-1",
        data={
            "metadata": {
                "title": "第1章 テスト",
                "section_count": 2,
                "total_paragraphs": 4,
                "difficulty_level": "intermediate",
                "generated_at": datetime.now().timestamp()
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
                "content": "テストパラグラフの内容です。",
                "type": "paragraph",
                "word_count": 8
            },
            "section": {
                "title": "テストセクション",
                "level": 2
            }
        },
        trace_id="trace-123"
    )


class TestAggregatorWorker:
    """AggregatorWorker のテスト."""
    
    def test_init(self, aggregator_worker, config):
        """初期化のテスト."""
        assert aggregator_worker.config == config
        assert aggregator_worker.worker_id == "aggregator-test-1"
        assert aggregator_worker.semaphore._value == config.workers.max_concurrent_tasks
        assert aggregator_worker.running is False
        assert isinstance(aggregator_worker.workflow_states, dict)
        assert len(aggregator_worker.workflow_states) == 0
        
        # 完了閾値の確認
        assert aggregator_worker.completion_thresholds['min_chapters'] == 1
        assert aggregator_worker.completion_thresholds['min_content_per_paragraph'] == 3
        
    def test_get_subscriptions(self, aggregator_worker):
        """購読イベントタイプのテスト."""
        subscriptions = aggregator_worker.get_subscriptions()
        expected_subscriptions = {
            EventType.STRUCTURE_ANALYZED,
            EventType.CONTENT_GENERATED,
            EventType.IMAGE_PROCESSED,
            EventType.METADATA_GENERATED,
            EventType.PARAGRAPH_PARSED,
            EventType.SECTION_PARSED,
            EventType.CHAPTER_PARSED
        }
        assert subscriptions == expected_subscriptions
        
    @pytest.mark.asyncio
    async def test_start(self, aggregator_worker, event_bus, state_manager, metrics):
        """ワーカー起動のテスト."""
        await aggregator_worker.start(event_bus, state_manager, metrics)
        
        assert aggregator_worker.running is True
        assert aggregator_worker.event_bus == event_bus
        assert aggregator_worker.state_manager == state_manager
        assert aggregator_worker.metrics == metrics
        
        # 購読が正しく行われたかチェック
        assert event_bus.subscribe.call_count == 7
        
    @pytest.mark.asyncio
    async def test_process_structure_analyzed(self, aggregator_worker, structure_analyzed_event):
        """構造解析イベント処理のテスト."""
        await aggregator_worker.process(structure_analyzed_event)
        
        # ワークフロー状態が作成されていることを確認
        assert "test-workflow-1" in aggregator_worker.workflow_states
        workflow_state = aggregator_worker.workflow_states["test-workflow-1"]
        
        # チャプターが記録されていることを確認
        assert len(workflow_state.chapters) == 2
        
        chapter_ids = list(workflow_state.chapters.keys())
        assert any("第1章_はじめに" in chapter_id for chapter_id in chapter_ids)
        assert any("第2章_応用" in chapter_id for chapter_id in chapter_ids)
        
    @pytest.mark.asyncio
    async def test_process_content_generated(self, aggregator_worker, content_generated_event):
        """コンテンツ生成イベント処理のテスト."""
        await aggregator_worker.process(content_generated_event)
        
        # ワークフロー状態が作成されていることを確認
        workflow_state = aggregator_worker.workflow_states["test-workflow-1"]
        
        # コンテンツアイテムが記録されていることを確認
        assert len(workflow_state.content_items) == 1
        
        content_key = list(workflow_state.content_items.keys())[0]
        content_item = workflow_state.content_items[content_key]
        
        assert content_item['content']['type'] == 'article'
        assert content_item['status'] == 'generated'
        assert content_item['paragraph']['index'] == 0
        
    @pytest.mark.asyncio
    async def test_process_image_processed(self, aggregator_worker, image_processed_event):
        """画像処理イベント処理のテスト."""
        await aggregator_worker.process(image_processed_event)
        
        # ワークフロー状態が作成されていることを確認
        workflow_state = aggregator_worker.workflow_states["test-workflow-1"]
        
        # 処理済み画像が記録されていることを確認
        assert len(workflow_state.processed_images) == 1
        
        image_id = list(workflow_state.processed_images.keys())[0]
        image_item = workflow_state.processed_images[image_id]
        
        assert image_item['image_data']['original_type'] == 'svg'
        assert image_item['image_data']['format'] == 'png'
        assert image_item['status'] == 'processed'
        
    @pytest.mark.asyncio
    async def test_process_metadata_generated(self, aggregator_worker, metadata_generated_event):
        """メタデータ生成イベント処理のテスト."""
        await aggregator_worker.process(metadata_generated_event)
        
        # ワークフロー状態が作成されていることを確認
        workflow_state = aggregator_worker.workflow_states["test-workflow-1"]
        
        # メタデータが記録されていることを確認
        assert len(workflow_state.metadata) == 1
        
        metadata_key = list(workflow_state.metadata.keys())[0]
        metadata_item = workflow_state.metadata[metadata_key]
        
        assert metadata_item['data']['title'] == '第1章 テスト'
        assert metadata_item['status'] == 'generated'
        
    @pytest.mark.asyncio
    async def test_process_paragraph_parsed(self, aggregator_worker, paragraph_parsed_event):
        """パラグラフ解析イベント処理のテスト."""
        await aggregator_worker.process(paragraph_parsed_event)
        
        # ワークフロー状態が作成されていることを確認
        workflow_state = aggregator_worker.workflow_states["test-workflow-1"]
        
        # パラグラフが記録されていることを確認
        assert len(workflow_state.paragraphs) == 1
        
        paragraph_id = list(workflow_state.paragraphs.keys())[0]
        paragraph_item = workflow_state.paragraphs[paragraph_id]
        
        assert paragraph_item['data']['index'] == 0
        assert paragraph_item['status'] == 'parsed'
        
    @pytest.mark.asyncio
    async def test_process_unknown_event(self, aggregator_worker):
        """未知のイベントタイプ処理のテスト."""
        unknown_event = Event(
            event_type="unknown.event",
            workflow_id="test-workflow-1",
            data={}
        )
        
        # エラーが発生しないことを確認
        await aggregator_worker.process(unknown_event)
        
    def test_get_or_create_workflow_state(self, aggregator_worker):
        """ワークフロー状態の取得・作成のテスト."""
        # 新しいワークフローIDで状態を作成
        workflow_id = "new-workflow"
        state = aggregator_worker._get_or_create_workflow_state(workflow_id)
        
        assert state.workflow_id == workflow_id
        assert state.status == "initialized"
        assert workflow_id in aggregator_worker.workflow_states
        
        # 既存のワークフローIDで同じ状態を取得
        same_state = aggregator_worker._get_or_create_workflow_state(workflow_id)
        assert same_state is state
        
    def test_assess_completion_status_incomplete(self, aggregator_worker):
        """完了状態評価のテスト（未完了）."""
        workflow_state = WorkflowState(workflow_id="test")
        
        # 基本的な状態を設定
        workflow_state.chapters = {"ch1": {"data": {}}}
        workflow_state.sections = {"sec1": {"data": {}}}
        workflow_state.paragraphs = {"para1": {"data": {}}}
        workflow_state.content_items = {}  # コンテンツがない
        
        status = aggregator_worker._assess_completion_status(workflow_state)
        
        assert not status['is_complete']
        assert status['progress'] == 0.0
        assert status['total_chapters'] == 1
        assert status['total_sections'] == 1
        assert status['total_paragraphs'] == 1
        assert status['total_content_items'] == 0
        
    def test_assess_completion_status_complete(self, aggregator_worker):
        """完了状態評価のテスト（完了）."""
        workflow_state = WorkflowState(workflow_id="test")
        
        # 完了状態を設定
        workflow_state.chapters = {"ch1": {"data": {}}}
        workflow_state.sections = {"sec1": {"data": {}}}
        workflow_state.paragraphs = {"para1": {"data": {}}}
        # 十分なコンテンツアイテム（3つ以上）
        workflow_state.content_items = {
            "item1": {"content": {"type": "article"}},
            "item2": {"content": {"type": "script"}},
            "item3": {"content": {"type": "tweet"}}
        }
        
        status = aggregator_worker._assess_completion_status(workflow_state)
        
        assert status['is_complete']
        assert status['progress'] == 1.0
        assert status['completion_percentage'] == 100.0
        
    def test_generate_content_summary(self, aggregator_worker):
        """コンテンツサマリー生成のテスト."""
        workflow_state = WorkflowState(workflow_id="test")
        
        # テストデータを設定
        workflow_state.chapters = {"ch1": {}}
        workflow_state.sections = {"sec1": {}, "sec2": {}}
        workflow_state.paragraphs = {"para1": {}, "para2": {}, "para3": {}}
        workflow_state.content_items = {
            "item1": {
                "content": {
                    "type": "article",
                    "title": "記事1",
                    "word_count": 100
                }
            },
            "item2": {
                "content": {
                    "type": "article",
                    "title": "記事2", 
                    "word_count": 150
                }
            },
            "item3": {
                "content": {
                    "type": "script",
                    "title": "台本1",
                    "word_count": 200
                }
            }
        }
        
        summary = aggregator_worker._generate_content_summary(workflow_state)
        
        assert summary['total_word_count'] == 450
        assert summary['total_chapters'] == 1
        assert summary['total_sections'] == 2
        assert summary['total_paragraphs'] == 3
        
        # コンテンツタイプ別の統計
        assert summary['content_types']['article']['count'] == 2
        assert summary['content_types']['article']['total_words'] == 250
        assert summary['content_types']['script']['count'] == 1
        assert summary['content_types']['script']['total_words'] == 200
        
    def test_calculate_processing_stats(self, aggregator_worker):
        """処理統計計算のテスト."""
        workflow_state = WorkflowState(workflow_id="test")
        
        # 過去の時刻を設定
        workflow_state.created_at = datetime.now() - timedelta(seconds=10)
        
        # テストデータを設定
        workflow_state.content_items = {"item1": {}, "item2": {}}
        workflow_state.processed_images = {
            "img1": {
                "image_data": {
                    "format": "png",
                    "file_size": 1024
                }
            },
            "img2": {
                "image_data": {
                    "format": "jpg",
                    "file_size": 2048
                }
            }
        }
        workflow_state.metadata = {"meta1": {}}
        
        stats = aggregator_worker._calculate_processing_stats(workflow_state)
        
        assert stats['processing_duration_seconds'] >= 10
        assert stats['items_per_second'] > 0
        assert stats['image_stats']['total_processed'] == 2
        assert stats['image_stats']['total_size'] == 3072
        assert stats['image_stats']['format_distribution']['png'] == 1
        assert stats['image_stats']['format_distribution']['jpg'] == 1
        assert stats['metadata_count'] == 1
        
    def test_generate_ids(self, aggregator_worker):
        """ID生成メソッドのテスト."""
        # チャプターID
        chapter = {"title": "第1章 はじめに", "level": 1}
        chapter_id = aggregator_worker._generate_chapter_id(chapter)
        assert chapter_id.startswith("chapter_1_")
        assert "第1章_はじめに" in chapter_id
        
        # セクションID
        section = {"title": "1.1 概要", "level": 2}
        section_id = aggregator_worker._generate_section_id(section)
        assert section_id.startswith("section_2_")
        assert "1.1_概要" in section_id
        
        # パラグラフID
        paragraph = {"index": 0, "content": "これはテストパラグラフです"}
        paragraph_id = aggregator_worker._generate_paragraph_id(paragraph)
        assert paragraph_id.startswith("paragraph_0_")
        assert "これはテストパラグラフです" in paragraph_id
        
    def test_serialize_workflow_state(self, aggregator_worker):
        """ワークフロー状態シリアライズのテスト."""
        workflow_state = WorkflowState(workflow_id="test")
        workflow_state.status = "in_progress"
        workflow_state.chapters = {"ch1": {}}
        workflow_state.sections = {"sec1": {}, "sec2": {}}
        
        serialized = aggregator_worker._serialize_workflow_state(workflow_state)
        
        assert serialized['workflow_id'] == "test"
        assert serialized['status'] == "in_progress"
        assert serialized['chapters_count'] == 1
        assert serialized['sections_count'] == 2
        assert 'created_at' in serialized
        assert 'updated_at' in serialized
        
    def test_get_workflow_status(self, aggregator_worker):
        """ワークフロー状態取得のテスト."""
        # 存在しないワークフローID
        status = aggregator_worker.get_workflow_status("nonexistent")
        assert status is None
        
        # 存在するワークフローID
        workflow_state = WorkflowState(workflow_id="test")
        aggregator_worker.workflow_states["test"] = workflow_state
        
        status = aggregator_worker.get_workflow_status("test")
        assert status is not None
        assert status['workflow_id'] == "test"
        
    def test_get_all_workflow_statuses(self, aggregator_worker):
        """全ワークフロー状態取得のテスト."""
        # 複数のワークフロー状態を作成
        for i in range(3):
            workflow_id = f"test-{i}"
            workflow_state = WorkflowState(workflow_id=workflow_id)
            aggregator_worker.workflow_states[workflow_id] = workflow_state
            
        all_statuses = aggregator_worker.get_all_workflow_statuses()
        
        assert len(all_statuses) == 3
        assert "test-0" in all_statuses
        assert "test-1" in all_statuses
        assert "test-2" in all_statuses
        
    def test_cleanup_completed_workflows(self, aggregator_worker):
        """完了ワークフロークリーンアップのテスト."""
        # 古い完了ワークフローを作成
        old_workflow = WorkflowState(workflow_id="old")
        old_workflow.status = "completed"
        old_workflow.updated_at = datetime.now() - timedelta(hours=25)
        aggregator_worker.workflow_states["old"] = old_workflow
        
        # 新しい完了ワークフローを作成
        new_workflow = WorkflowState(workflow_id="new")
        new_workflow.status = "completed"
        new_workflow.updated_at = datetime.now() - timedelta(hours=1)
        aggregator_worker.workflow_states["new"] = new_workflow
        
        # 進行中のワークフローを作成
        active_workflow = WorkflowState(workflow_id="active")
        active_workflow.status = "in_progress"
        active_workflow.updated_at = datetime.now() - timedelta(hours=25)
        aggregator_worker.workflow_states["active"] = active_workflow
        
        # クリーンアップを実行
        cleaned_count = aggregator_worker.cleanup_completed_workflows(24)
        
        assert cleaned_count == 1
        assert "old" not in aggregator_worker.workflow_states
        assert "new" in aggregator_worker.workflow_states  # 新しいので残る
        assert "active" in aggregator_worker.workflow_states  # 進行中なので残る
        
    @pytest.mark.asyncio
    async def test_check_completion_and_aggregate_incomplete(self, aggregator_worker, event_bus):
        """完了チェックと集約のテスト（未完了）."""
        aggregator_worker.event_bus = event_bus
        
        workflow_state = WorkflowState(workflow_id="test")
        # 未完了状態を設定
        workflow_state.chapters = {"ch1": {}}
        workflow_state.content_items = {}  # コンテンツ不足
        
        await aggregator_worker._check_completion_and_aggregate(workflow_state)
        
        # 完了イベントは発行されない
        assert event_bus.publish.call_count == 0
        assert workflow_state.status != "completed"
        
    @pytest.mark.asyncio
    async def test_check_completion_and_aggregate_complete(self, aggregator_worker, event_bus):
        """完了チェックと集約のテスト（完了）."""
        aggregator_worker.event_bus = event_bus
        
        workflow_state = WorkflowState(workflow_id="test")
        # 完了状態を設定
        workflow_state.chapters = {"ch1": {}}
        workflow_state.sections = {"sec1": {}}
        workflow_state.paragraphs = {"para1": {}}
        workflow_state.content_items = {
            "item1": {
                "content": {"type": "article"},
                "paragraph": {"index": 0},
                "section": {"title": "テストセクション"},
                "status": "generated",
                "received_at": datetime.now()
            },
            "item2": {
                "content": {"type": "script"},
                "paragraph": {"index": 1},
                "section": {"title": "テストセクション"},
                "status": "generated",
                "received_at": datetime.now()
            },
            "item3": {
                "content": {"type": "tweet"},
                "paragraph": {"index": 2},
                "section": {"title": "テストセクション"},
                "status": "generated",
                "received_at": datetime.now()
            }
        }
        
        await aggregator_worker._check_completion_and_aggregate(workflow_state)
        
        # 完了イベントとレポート生成イベントが発行される
        assert event_bus.publish.call_count == 2
        
        # 最初のイベント（完了イベント）を確認
        completion_event = event_bus.publish.call_args_list[0][0][0]
        assert completion_event.type == EventType.WORKFLOW_COMPLETED
        assert 'aggregation_result' in completion_event.data
        
        # 2番目のイベント（レポート生成イベント）を確認
        report_event = event_bus.publish.call_args_list[1][0][0]
        assert report_event.type == EventType.REPORT_GENERATED
        assert 'report' in report_event.data
        
        # ワークフロー状態が完了に更新される
        assert workflow_state.status == "completed"
        
    def test_aggregation_result_dataclass(self):
        """AggregationResultデータクラスのテスト."""
        result = AggregationResult(
            workflow_id="test",
            status="completed",
            total_content_items=10,
            processed_images=3,
            generated_thumbnails=1,
            metadata_entries=2,
            aggregated_at=datetime.now()
        )
        
        assert result.workflow_id == "test"
        assert result.status == "completed"
        assert result.total_content_items == 10
        assert result.processed_images == 3
        assert result.generated_thumbnails == 1
        assert result.metadata_entries == 2
        assert isinstance(result.aggregated_at, datetime)
        assert isinstance(result.content_summary, dict)
        assert isinstance(result.processing_stats, dict)
        assert isinstance(result.errors, list)
        
    def test_workflow_state_dataclass(self):
        """WorkflowStateデータクラスのテスト."""
        state = WorkflowState(workflow_id="test")
        
        assert state.workflow_id == "test"
        assert state.status == "initialized"
        assert isinstance(state.chapters, dict)
        assert isinstance(state.sections, dict)
        assert isinstance(state.paragraphs, dict)
        assert isinstance(state.content_items, dict)
        assert isinstance(state.processed_images, dict)
        assert isinstance(state.metadata, dict)
        assert isinstance(state.created_at, datetime)
        assert isinstance(state.updated_at, datetime) 