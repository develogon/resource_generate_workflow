"""Workers Base クラスのテスト."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock

from src.workers.base import BaseWorker, Event, EventType
from src.config import Config


class MockWorker(BaseWorker):
    """テスト用ワーカー."""
    
    def __init__(self, config: Config, worker_id: str):
        super().__init__(config, worker_id)
        self.processed_events = []
        
    def get_subscriptions(self) -> set[str]:
        """購読するイベントタイプを返す."""
        return {EventType.CONTENT_GENERATED, EventType.IMAGE_PROCESSED}
        
    async def process(self, event: Event) -> None:
        """イベントを処理."""
        self.processed_events.append(event)
        
        # テスト用の処理時間をシミュレート
        await asyncio.sleep(0.01)
        
        # 特定の条件でエラーを発生させる
        if event.data.get("should_fail"):
            raise ValueError("Test error")


@pytest.fixture
def config():
    """テスト用設定."""
    config = Config()
    config.workers.max_concurrent_tasks = 2
    config.max_retries = 3
    return config


@pytest.fixture
def worker(config):
    """テスト用ワーカー."""
    return MockWorker(config, "test-worker-1")


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
def sample_event():
    """テスト用イベント."""
    return Event(
        event_type=EventType.CONTENT_GENERATED,
        workflow_id="test-workflow-1",
        data={"content": "test content"},
        trace_id="trace-123"
    )


class TestBaseWorker:
    """BaseWorker のテスト."""
    
    def test_init(self, worker, config):
        """初期化のテスト."""
        assert worker.config == config
        assert worker.worker_id == "test-worker-1"
        assert worker.semaphore._value == config.workers.max_concurrent_tasks
        assert worker.running is False
        
    def test_get_subscriptions(self, worker):
        """購読イベントタイプのテスト."""
        subscriptions = worker.get_subscriptions()
        assert EventType.CONTENT_GENERATED in subscriptions
        assert EventType.IMAGE_PROCESSED in subscriptions
        
    @pytest.mark.asyncio
    async def test_start(self, worker, event_bus, state_manager, metrics):
        """ワーカー起動のテスト."""
        await worker.start(event_bus, state_manager, metrics)
        
        assert worker.running is True
        assert worker.event_bus == event_bus
        assert worker.state_manager == state_manager
        assert worker.metrics == metrics
        
        # 購読が正しく行われたかチェック
        assert event_bus.subscribe.call_count == 2
        
    @pytest.mark.asyncio
    async def test_stop(self, worker):
        """ワーカー停止のテスト."""
        worker.running = True
        await worker.stop()
        assert worker.running is False
        
    @pytest.mark.asyncio
    async def test_process_success(self, worker, sample_event):
        """イベント処理成功のテスト."""
        await worker.process(sample_event)
        assert len(worker.processed_events) == 1
        assert worker.processed_events[0] == sample_event
        
    @pytest.mark.asyncio
    async def test_handle_event_success(self, worker, event_bus, state_manager, metrics, sample_event):
        """イベントハンドリング成功のテスト."""
        await worker.start(event_bus, state_manager, metrics)
        await worker.handle_event(sample_event)
        
        # イベントが処理されたかチェック
        assert len(worker.processed_events) == 1
        
        # チェックポイントが保存されたかチェック
        assert state_manager.save_checkpoint.call_count == 2  # started, completed
        
        # メトリクスが記録されたかチェック
        assert metrics.record_processing_time.call_count == 1
        
    @pytest.mark.asyncio
    async def test_handle_event_error(self, worker, event_bus, state_manager, metrics):
        """イベントハンドリングエラーのテスト."""
        await worker.start(event_bus, state_manager, metrics)
        
        # エラーを発生させるイベント
        error_event = Event(
            event_type=EventType.CONTENT_GENERATED,
            workflow_id="test-workflow-1",
            data={"should_fail": True}
        )
        
        await worker.handle_event(error_event)
        
        # エラーチェックポイントが保存されたかチェック
        assert state_manager.save_checkpoint.call_count >= 2  # started, failed
        
        # エラーメトリクスが記録されたかチェック
        assert metrics.record_error.call_count == 1
        
    @pytest.mark.asyncio
    async def test_handle_event_not_running(self, worker, sample_event):
        """停止中のワーカーでのイベントハンドリングテスト."""
        # ワーカーが停止状態
        worker.running = False
        
        await worker.handle_event(sample_event)
        
        # イベントが処理されないことを確認
        assert len(worker.processed_events) == 0
        
    @pytest.mark.asyncio
    async def test_save_checkpoint(self, worker, state_manager, sample_event):
        """チェックポイント保存のテスト."""
        worker.state_manager = state_manager
        
        await worker.save_checkpoint(sample_event, "started")
        
        state_manager.save_checkpoint.assert_called_once()
        args = state_manager.save_checkpoint.call_args
        assert args[0][0] == sample_event.workflow_id
        assert args[0][1] == "test-worker-1_started"
        
    def test_should_retry_max_retries(self, worker):
        """最大リトライ回数に達した場合のテスト."""
        event = Event(
            event_type=EventType.CONTENT_GENERATED,
            workflow_id="test",
            data={},
            retry_count=3  # max_retries と同じ
        )
        
        assert worker.should_retry(ValueError("test"), event) is False
        
    def test_should_retry_non_retryable_error(self, worker):
        """リトライ不可エラーのテスト."""
        event = Event(
            event_type=EventType.CONTENT_GENERATED,
            workflow_id="test",
            data={},
            retry_count=0
        )
        
        # ValueError はリトライ不可
        assert worker.should_retry(ValueError("test"), event) is False
        
        # TypeError もリトライ不可
        assert worker.should_retry(TypeError("test"), event) is False
        
    def test_should_retry_retryable_error(self, worker):
        """リトライ可能エラーのテスト."""
        event = Event(
            event_type=EventType.CONTENT_GENERATED,
            workflow_id="test",
            data={},
            retry_count=0
        )
        
        # RuntimeError はリトライ可能
        assert worker.should_retry(RuntimeError("test"), event) is True
        
    @pytest.mark.asyncio
    async def test_retry_event(self, worker, event_bus):
        """イベントリトライのテスト."""
        worker.event_bus = event_bus
        
        event = Event(
            event_type=EventType.CONTENT_GENERATED,
            workflow_id="test",
            data={},
            retry_count=1
        )
        
        await worker.retry_event(event)
        
        # リトライイベントが発行されたかチェック
        event_bus.publish.assert_called_once()
        retry_event = event_bus.publish.call_args[0][0]
        assert retry_event.retry_count == 2
        
    @pytest.mark.asyncio
    async def test_fail_event(self, worker, event_bus):
        """イベント失敗処理のテスト."""
        worker.event_bus = event_bus
        
        event = Event(
            event_type=EventType.CONTENT_GENERATED,
            workflow_id="test",
            data={}
        )
        
        await worker.fail_event(event, ValueError("test error"))
        
        # 失敗イベントが発行されたかチェック
        event_bus.publish.assert_called_once()
        failure_event = event_bus.publish.call_args[0][0]
        assert failure_event.type == EventType.WORKFLOW_FAILED
        
    def test_validate_event_valid(self, worker, sample_event):
        """有効なイベントの検証テスト."""
        assert worker.validate_event(sample_event) is True
        
    def test_validate_event_invalid_empty(self, worker):
        """無効なイベント（空）の検証テスト."""
        assert worker.validate_event(None) is False
        
    def test_validate_event_invalid_no_type(self, worker):
        """無効なイベント（タイプなし）の検証テスト."""
        event = Event(
            event_type="",
            workflow_id="test",
            data={}
        )
        assert worker.validate_event(event) is False
        
    def test_validate_event_invalid_no_workflow_id(self, worker):
        """無効なイベント（ワークフローIDなし）の検証テスト."""
        event = Event(
            event_type=EventType.CONTENT_GENERATED,
            workflow_id="",
            data={}
        )
        assert worker.validate_event(event) is False
        
    def test_validate_event_invalid_unsubscribed_type(self, worker):
        """無効なイベント（未購読タイプ）の検証テスト."""
        event = Event(
            event_type=EventType.WORKFLOW_STARTED,  # 購読していないタイプ
            workflow_id="test",
            data={}
        )
        assert worker.validate_event(event) is False
        
    @pytest.mark.asyncio
    async def test_concurrent_event_handling(self, worker, event_bus, state_manager, metrics):
        """並行イベント処理のテスト."""
        await worker.start(event_bus, state_manager, metrics)
        
        # 複数のイベントを並行処理
        events = [
            Event(
                event_type=EventType.CONTENT_GENERATED,
                workflow_id=f"test-{i}",
                data={"content": f"content-{i}"}
            )
            for i in range(5)
        ]
        
        tasks = [worker.handle_event(event) for event in events]
        await asyncio.gather(*tasks)
        
        # すべてのイベントが処理されたかチェック
        assert len(worker.processed_events) == 5
        
    def test_abstract_methods(self):
        """抽象メソッドのテスト."""
        with pytest.raises(TypeError):
            BaseWorker(Config(), "test") 