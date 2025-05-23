"""イベント駆動システムのコアコンポーネント."""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Callable, List, Set
from enum import Enum

logger = logging.getLogger(__name__)


class EventType(Enum):
    """イベントタイプ."""
    # ワークフローイベント
    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_COMPLETED = "workflow.completed"
    WORKFLOW_FAILED = "workflow.failed"
    
    # タスクイベント
    TASK_FAILED = "task.failed"
    
    # 解析イベント
    CHAPTER_PARSED = "chapter.parsed"
    SECTION_PARSED = "section.parsed"
    PARAGRAPH_PARSED = "paragraph.parsed"
    STRUCTURE_ANALYZED = "structure.analyzed"
    
    # 生成イベント
    CONTENT_GENERATED = "content.generated"
    IMAGE_PROCESSED = "image.processed"
    THUMBNAIL_GENERATED = "thumbnail.generated"
    
    # 集約イベント
    SECTION_AGGREGATED = "section.aggregated"
    CHAPTER_AGGREGATED = "chapter.aggregated"
    METADATA_GENERATED = "metadata.generated"


@dataclass
class Event:
    """イベントデータ構造."""
    type: EventType
    workflow_id: str
    data: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    retry_count: int = 0
    priority: int = 0
    trace_id: Optional[str] = None
    
    def __lt__(self, other):
        """比較演算子（優先度付きキューで使用）."""
        if not isinstance(other, Event):
            return NotImplemented
        return self.priority < other.priority
        
    def __le__(self, other):
        """比較演算子（優先度付きキューで使用）."""
        if not isinstance(other, Event):
            return NotImplemented
        return self.priority <= other.priority
        
    def __gt__(self, other):
        """比較演算子（優先度付きキューで使用）."""
        if not isinstance(other, Event):
            return NotImplemented
        return self.priority > other.priority
        
    def __ge__(self, other):
        """比較演算子（優先度付きキューで使用）."""
        if not isinstance(other, Event):
            return NotImplemented
        return self.priority >= other.priority


class EventBus:
    """非同期イベントバス."""
    
    def __init__(self, config):
        """初期化."""
        self.config = config
        self.subscribers: Dict[EventType, List[Callable]] = {}
        self.queue = asyncio.PriorityQueue()
        self.dead_letter_queue = asyncio.Queue()
        self.running = False
        self._event_task: Optional[asyncio.Task] = None
        self._dead_letter_task: Optional[asyncio.Task] = None
        
    async def subscribe(self, event_type: EventType, handler: Callable):
        """イベントハンドラーの登録."""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(handler)
        logger.debug(f"Subscribed handler for {event_type.value}")
        
    async def unsubscribe(self, event_type: EventType, handler: Callable):
        """イベントハンドラーの登録解除."""
        if event_type in self.subscribers:
            try:
                self.subscribers[event_type].remove(handler)
                logger.debug(f"Unsubscribed handler for {event_type.value}")
            except ValueError:
                logger.warning(f"Handler not found for {event_type.value}")
                
    async def publish(self, event: Event, delay: float = 0):
        """イベントの発行."""
        if delay > 0:
            await asyncio.sleep(delay)
            
        # 優先度付きキューに追加
        priority_item = (-event.priority, event.timestamp, event)
        await self.queue.put(priority_item)
        
        logger.debug(f"Published event {event.type.value} for workflow {event.workflow_id}")
        
    async def start(self):
        """イベントバスの起動."""
        if self.running:
            return
            
        self.running = True
        
        # イベント処理タスクを開始
        self._event_task = asyncio.create_task(self._process_events())
        self._dead_letter_task = asyncio.create_task(self._process_dead_letters())
        
        logger.info("EventBus started")
        
    async def stop(self):
        """イベントバスの停止."""
        if not self.running:
            return
            
        self.running = False
        
        # タスクの停止
        if self._event_task:
            self._event_task.cancel()
            try:
                await self._event_task
            except asyncio.CancelledError:
                pass
                
        if self._dead_letter_task:
            self._dead_letter_task.cancel()
            try:
                await self._dead_letter_task
            except asyncio.CancelledError:
                pass
                
        logger.info("EventBus stopped")
        
    async def _process_events(self):
        """イベント処理ループ."""
        while self.running:
            try:
                # タイムアウト付きでイベントを取得
                priority_item = await asyncio.wait_for(
                    self.queue.get(),
                    timeout=1.0
                )
                _, _, event = priority_item
                
                await self._dispatch_event(event)
                
            except asyncio.TimeoutError:
                # タイムアウトは正常（継続）
                continue
            except Exception as e:
                logger.error(f"Event processing error: {e}")
                
    async def _dispatch_event(self, event: Event):
        """イベントをハンドラーにディスパッチ."""
        handlers = self.subscribers.get(event.type, [])
        
        if not handlers:
            logger.debug(f"No handlers for event {event.type.value}")
            return
            
        # ハンドラーを並列実行
        tasks = []
        for handler in handlers:
            task = asyncio.create_task(self._safe_handler_call(handler, event))
            tasks.append(task)
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # エラーハンドリング
        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Handler {idx} failed for event {event.type.value}: {result}")
                await self._handle_handler_error(event, result)
                
    async def _safe_handler_call(self, handler: Callable, event: Event):
        """安全なハンドラー呼び出し."""
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(event)
            else:
                handler(event)
        except Exception as e:
            logger.error(f"Handler execution failed: {e}")
            raise
            
    async def _handle_handler_error(self, event: Event, error: Exception):
        """ハンドラーエラーの処理."""
        # リトライ可能なエラーの場合
        if event.retry_count < 3:
            event.retry_count += 1
            # 少し遅延してリトライ
            await self.publish(event, delay=event.retry_count * 2)
        else:
            # デッドレターキューに送信
            await self.dead_letter_queue.put((event, error))
            
    async def _process_dead_letters(self):
        """デッドレターキューの処理."""
        while self.running:
            try:
                # タイムアウト付きでデッドレターを取得
                dead_letter = await asyncio.wait_for(
                    self.dead_letter_queue.get(),
                    timeout=1.0
                )
                event, error = dead_letter
                
                logger.error(f"Dead letter event {event.type.value}: {error}")
                # TODO: デッドレターの永続化や通知
                
            except asyncio.TimeoutError:
                # タイムアウトは正常（継続）
                continue
            except Exception as e:
                logger.error(f"Dead letter processing error: {e}")
                
    async def get_queue_size(self) -> int:
        """キューサイズの取得."""
        return self.queue.qsize()
        
    async def get_dead_letter_count(self) -> int:
        """デッドレターキューサイズの取得."""
        return self.dead_letter_queue.qsize()


class EventFilter:
    """イベントフィルター."""
    
    def __init__(self, 
                 event_types: Optional[Set[EventType]] = None,
                 workflow_ids: Optional[Set[str]] = None):
        """初期化."""
        self.event_types = event_types
        self.workflow_ids = workflow_ids
        
    def matches(self, event: Event) -> bool:
        """イベントがフィルターにマッチするかチェック."""
        if self.event_types and event.type not in self.event_types:
            return False
            
        if self.workflow_ids and event.workflow_id not in self.workflow_ids:
            return False
            
        return True


class EventCollector:
    """イベント収集器（テスト用）."""
    
    def __init__(self, event_filter: Optional[EventFilter] = None):
        """初期化."""
        self.events: List[Event] = []
        self.filter = event_filter
        
    async def collect(self, event: Event):
        """イベントの収集."""
        if not self.filter or self.filter.matches(event):
            self.events.append(event)
            
    def get_events(self, event_type: Optional[EventType] = None) -> List[Event]:
        """収集したイベントの取得."""
        if event_type:
            return [e for e in self.events if e.type == event_type]
        return self.events.copy()
        
    def clear(self):
        """収集したイベントのクリア."""
        self.events.clear() 