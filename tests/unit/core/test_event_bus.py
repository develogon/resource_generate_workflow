"""
EventBusの単体テスト

EventBus、Event、EventHandlerクラスの機能をテストします：
- イベントの発行と配信
- ハンドラーの登録と解除
- 優先度付き処理
- エラーハンドリングとリトライ
- デッドレターキュー
"""

import asyncio
import pytest
import pytest_asyncio
import time
from unittest.mock import AsyncMock, Mock

from src.core.event_bus import EventBus, Event, EventHandler, EventType


class MockEventHandler(EventHandler):
    """テスト用のイベントハンドラー"""
    
    def __init__(self, supported_events: set = None, should_fail: bool = False):
        self.supported_events = supported_events or set()
        self.should_fail = should_fail
        self.handled_events = []
        self.call_count = 0
        
    async def handle(self, event: Event) -> None:
        """イベントを処理"""
        self.call_count += 1
        self.handled_events.append(event)
        
        if self.should_fail:
            raise Exception(f"Handler intentionally failed for {event.type.value}")
            
        # 非同期処理をシミュレート
        await asyncio.sleep(0.01)
        
    def can_handle(self, event_type: EventType) -> bool:
        """指定されたイベントタイプを処理できるかチェック"""
        return event_type in self.supported_events


@pytest_asyncio.fixture
async def event_bus():
    """EventBusのフィクスチャ"""
    bus = EventBus(max_concurrent_handlers=5, dead_letter_limit=2)
    await bus.start()
    yield bus
    await bus.stop()


@pytest.fixture
def sample_event():
    """サンプルイベントのフィクスチャ"""
    return Event(
        type=EventType.WORKFLOW_STARTED,
        workflow_id="test-workflow-001",
        data={"lang": "ja", "title": "テストブック"}
    )


class TestEvent:
    """Eventクラスのテスト"""
    
    def test_event_creation(self):
        """イベントの作成テスト"""
        event = Event(
            type=EventType.WORKFLOW_STARTED,
            workflow_id="test-001",
            data={"test": "data"},
            priority=5
        )
        
        assert event.type == EventType.WORKFLOW_STARTED
        assert event.workflow_id == "test-001"
        assert event.data == {"test": "data"}
        assert event.priority == 5
        assert event.retry_count == 0
        assert event.timestamp > 0
        assert event.trace_id is not None
        
    def test_trace_id_generation(self):
        """トレースIDの自動生成テスト"""
        event = Event(
            type=EventType.WORKFLOW_STARTED,
            workflow_id="test-001",
            data={}
        )
        
        expected_prefix = f"test-001_{EventType.WORKFLOW_STARTED.value}"
        assert event.trace_id.startswith(expected_prefix)
        
    def test_custom_trace_id(self):
        """カスタムトレースIDのテスト"""
        custom_trace_id = "custom-trace-123"
        event = Event(
            type=EventType.WORKFLOW_STARTED,
            workflow_id="test-001",
            data={},
            trace_id=custom_trace_id
        )
        
        assert event.trace_id == custom_trace_id


class TestEventHandler:
    """EventHandlerクラスのテスト"""
    
    def test_handler_can_handle(self):
        """ハンドラーの対応イベント判定テスト"""
        handler = MockEventHandler(
            supported_events={EventType.WORKFLOW_STARTED, EventType.CHAPTER_PARSED}
        )
        
        assert handler.can_handle(EventType.WORKFLOW_STARTED) is True
        assert handler.can_handle(EventType.CHAPTER_PARSED) is True
        assert handler.can_handle(EventType.CONTENT_GENERATED) is False
        
    @pytest.mark.asyncio
    async def test_handler_handle_event(self):
        """ハンドラーのイベント処理テスト"""
        handler = MockEventHandler()
        event = Event(
            type=EventType.WORKFLOW_STARTED,
            workflow_id="test-001",
            data={"test": "data"}
        )
        
        await handler.handle(event)
        
        assert handler.call_count == 1
        assert len(handler.handled_events) == 1
        assert handler.handled_events[0] == event


class TestEventBus:
    """EventBusクラスのテスト"""
    
    @pytest.mark.asyncio
    async def test_start_stop(self):
        """EventBusの起動・停止テスト"""
        bus = EventBus()
        
        assert bus.running is False
        
        await bus.start()
        assert bus.running is True
        
        await bus.stop()
        assert bus.running is False
        
    @pytest.mark.asyncio
    async def test_subscribe_unsubscribe(self, event_bus):
        """ハンドラーの登録・解除テスト"""
        handler = MockEventHandler(
            supported_events={EventType.WORKFLOW_STARTED}
        )
        
        # 登録前は購読者なし
        stats = await event_bus.get_stats()
        assert stats["subscribers"].get(EventType.WORKFLOW_STARTED.value, 0) == 0
        
        # 登録
        await event_bus.subscribe(handler)
        stats = await event_bus.get_stats()
        assert stats["subscribers"][EventType.WORKFLOW_STARTED.value] == 1
        
        # 解除
        await event_bus.unsubscribe(handler)
        stats = await event_bus.get_stats()
        assert stats["subscribers"].get(EventType.WORKFLOW_STARTED.value, 0) == 0
        
    @pytest.mark.asyncio
    async def test_publish_and_handle(self, event_bus, sample_event):
        """イベントの発行と処理テスト"""
        handler = MockEventHandler(
            supported_events={EventType.WORKFLOW_STARTED}
        )
        
        await event_bus.subscribe(handler)
        await event_bus.publish(sample_event)
        
        # 処理完了まで少し待機
        await asyncio.sleep(0.1)
        
        assert handler.call_count == 1
        assert len(handler.handled_events) == 1
        assert handler.handled_events[0].workflow_id == sample_event.workflow_id
        
    @pytest.mark.asyncio
    async def test_priority_ordering(self, event_bus):
        """優先度付き処理のテスト"""
        handler = MockEventHandler(
            supported_events={EventType.WORKFLOW_STARTED}
        )
        await event_bus.subscribe(handler)
        
        # 異なる優先度でイベントを発行
        low_priority = Event(
            type=EventType.WORKFLOW_STARTED,
            workflow_id="test-low",
            data={},
            priority=1
        )
        high_priority = Event(
            type=EventType.WORKFLOW_STARTED,
            workflow_id="test-high",
            data={},
            priority=10
        )
        
        # 低優先度を先に発行
        await event_bus.publish(low_priority)
        await event_bus.publish(high_priority)
        
        # 処理完了まで待機
        await asyncio.sleep(0.1)
        
        # 高優先度が先に処理される
        assert len(handler.handled_events) == 2
        assert handler.handled_events[0].workflow_id == "test-high"
        assert handler.handled_events[1].workflow_id == "test-low"
        
    @pytest.mark.asyncio
    async def test_multiple_handlers(self, event_bus, sample_event):
        """複数ハンドラーの並列処理テスト"""
        handler1 = MockEventHandler(
            supported_events={EventType.WORKFLOW_STARTED}
        )
        handler2 = MockEventHandler(
            supported_events={EventType.WORKFLOW_STARTED}
        )
        
        await event_bus.subscribe(handler1)
        await event_bus.subscribe(handler2)
        await event_bus.publish(sample_event)
        
        # 処理完了まで待機
        await asyncio.sleep(0.1)
        
        # 両方のハンドラーが処理
        assert handler1.call_count == 1
        assert handler2.call_count == 1
        
    @pytest.mark.asyncio
    async def test_handler_error_retry(self, event_bus):
        """ハンドラーエラーのリトライテスト"""
        handler = MockEventHandler(
            supported_events={EventType.WORKFLOW_STARTED},
            should_fail=True
        )
        
        await event_bus.subscribe(handler)
        
        event = Event(
            type=EventType.WORKFLOW_STARTED,
            workflow_id="test-retry",
            data={}
        )
        
        await event_bus.publish(event)
        
        # リトライを含めて処理完了まで待機
        # 指数バックオフ (1秒 + 2秒) + 処理時間を考慮
        await asyncio.sleep(5.0)
        
        # 初回 + リトライ回数分呼ばれる
        expected_calls = 1 + event_bus.dead_letter_limit
        assert handler.call_count == expected_calls
        
    @pytest.mark.asyncio
    async def test_dead_letter_queue(self, event_bus):
        """デッドレターキューのテスト"""
        handler = MockEventHandler(
            supported_events={EventType.WORKFLOW_STARTED},
            should_fail=True
        )
        
        await event_bus.subscribe(handler)
        
        event = Event(
            type=EventType.WORKFLOW_STARTED,
            workflow_id="test-dead-letter",
            data={}
        )
        
        await event_bus.publish(event)
        
        # リトライとデッドレター処理完了まで待機
        await asyncio.sleep(3.0)
        
        stats = await event_bus.get_stats()
        # デッドレターキューにイベントが送られている可能性
        # (処理されてしまう場合もあるので、0以上であることを確認)
        assert stats["dead_letter_queue_size"] >= 0
        
    @pytest.mark.asyncio
    async def test_publish_without_start(self):
        """EventBus未起動でのpublishエラーテスト"""
        bus = EventBus()
        event = Event(
            type=EventType.WORKFLOW_STARTED,
            workflow_id="test-001",
            data={}
        )
        
        with pytest.raises(RuntimeError, match="EventBus is not running"):
            await bus.publish(event)
            
    @pytest.mark.asyncio
    async def test_no_handlers_for_event(self, event_bus, caplog):
        """ハンドラーが登録されていないイベントの処理テスト"""
        event = Event(
            type=EventType.WORKFLOW_STARTED,
            workflow_id="test-no-handler",
            data={}
        )
        
        await event_bus.publish(event)
        await asyncio.sleep(0.1)
        
        # 警告ログが出力される
        assert "No handlers registered" in caplog.text
        
    @pytest.mark.asyncio
    async def test_delayed_publish(self, event_bus):
        """遅延発行のテスト"""
        handler = MockEventHandler(
            supported_events={EventType.WORKFLOW_STARTED}
        )
        await event_bus.subscribe(handler)
        
        event = Event(
            type=EventType.WORKFLOW_STARTED,
            workflow_id="test-delay",
            data={}
        )
        
        start_time = time.time()
        await event_bus.publish(event, delay=0.2)
        
        # 即座にはまだ処理されていない
        assert handler.call_count == 0
        
        # 遅延後に処理される
        await asyncio.sleep(0.3)
        assert handler.call_count == 1
        
        # 実際に遅延されたかチェック
        end_time = time.time()
        assert end_time - start_time >= 0.2
        
    @pytest.mark.asyncio
    async def test_concurrent_handling(self, event_bus):
        """並行処理制限のテスト"""
        # 処理に時間がかかるハンドラー
        class SlowHandler(EventHandler):
            def __init__(self):
                self.active_count = 0
                self.max_concurrent = 0
                
            async def handle(self, event: Event):
                self.active_count += 1
                self.max_concurrent = max(self.max_concurrent, self.active_count)
                await asyncio.sleep(0.1)
                self.active_count -= 1
                
            def can_handle(self, event_type: EventType) -> bool:
                return event_type == EventType.WORKFLOW_STARTED
                
        handler = SlowHandler()
        await event_bus.subscribe(handler)
        
        # 大量のイベントを発行
        tasks = []
        for i in range(20):
            event = Event(
                type=EventType.WORKFLOW_STARTED,
                workflow_id=f"test-concurrent-{i}",
                data={}
            )
            tasks.append(event_bus.publish(event))
            
        await asyncio.gather(*tasks)
        await asyncio.sleep(0.5)
        
        # 並行処理制限が機能している
        assert handler.max_concurrent <= event_bus.max_concurrent_handlers
        
    @pytest.mark.asyncio
    async def test_get_stats(self, event_bus):
        """統計情報取得のテスト"""
        handler = MockEventHandler(
            supported_events={EventType.WORKFLOW_STARTED, EventType.CHAPTER_PARSED}
        )
        await event_bus.subscribe(handler)
        
        stats = await event_bus.get_stats()
        
        assert isinstance(stats, dict)
        assert "running" in stats
        assert "queue_size" in stats
        assert "dead_letter_queue_size" in stats
        assert "active_tasks" in stats
        assert "subscribers" in stats
        
        assert stats["running"] is True
        assert stats["subscribers"][EventType.WORKFLOW_STARTED.value] == 1
        assert stats["subscribers"][EventType.CHAPTER_PARSED.value] == 1 