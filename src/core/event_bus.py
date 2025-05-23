"""
イベント駆動アーキテクチャのコア - EventBus

このモジュールはワークフローエンジンの中核となるイベントシステムを提供します。
非同期イベント処理、優先度付きキュー、エラーハンドリング、デッドレターキューを実装。
"""

import asyncio
import time
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, Callable, List, Set, Awaitable

logger = logging.getLogger(__name__)


class EventType(Enum):
    """イベントタイプ定義"""
    # ワークフローイベント
    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_COMPLETED = "workflow.completed"
    WORKFLOW_FAILED = "workflow.failed"
    WORKFLOW_SUSPENDED = "workflow.suspended"
    
    # タスクイベント
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
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
    """イベントデータ構造"""
    type: EventType
    workflow_id: str
    data: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    retry_count: int = 0
    priority: int = 0
    trace_id: Optional[str] = None
    
    def __post_init__(self):
        """イベント生成後の初期化処理"""
        if self.trace_id is None:
            self.trace_id = f"{self.workflow_id}_{self.type.value}_{int(self.timestamp)}"


class EventHandler(ABC):
    """イベントハンドラーの抽象基底クラス"""
    
    @abstractmethod
    async def handle(self, event: Event) -> None:
        """イベントを処理する"""
        pass
    
    @abstractmethod
    def can_handle(self, event_type: EventType) -> bool:
        """指定されたイベントタイプを処理できるかチェック"""
        pass


class EventBus:
    """非同期イベントバス
    
    イベント駆動アーキテクチャの中核として、
    イベントの発行、配信、順序制御を担当する。
    """
    
    def __init__(self, max_concurrent_handlers: int = 10, dead_letter_limit: int = 3):
        self.subscribers: Dict[EventType, List[EventHandler]] = {}
        self.queue = asyncio.PriorityQueue()
        self.dead_letter_queue = asyncio.Queue()
        self.running = False
        self.max_concurrent_handlers = max_concurrent_handlers
        self.dead_letter_limit = dead_letter_limit
        self._semaphore = asyncio.Semaphore(max_concurrent_handlers)
        self._tasks: Set[asyncio.Task] = set()
        
    async def subscribe(self, event_handler_or_type, handler_func=None) -> None:
        """イベントハンドラーの登録
        
        Args:
            event_handler_or_type: EventHandlerインスタンスまたはEventType
            handler_func: event_handler_or_typeがEventTypeの場合のハンドラー関数
        """
        if isinstance(event_handler_or_type, EventHandler):
            # 従来の方式：EventHandlerインスタンスを登録
            event_handler = event_handler_or_type
            for event_type in EventType:
                if event_handler.can_handle(event_type):
                    if event_type not in self.subscribers:
                        self.subscribers[event_type] = []
                    self.subscribers[event_type].append(event_handler)
                    logger.debug(f"Registered handler {event_handler.__class__.__name__} for {event_type.value}")
        
        elif isinstance(event_handler_or_type, EventType) and handler_func is not None:
            # 新しい方式：特定のイベントタイプとハンドラー関数を登録
            event_type = event_handler_or_type
            
            # ハンドラー関数をEventHandlerでラップ
            class FunctionHandler(EventHandler):
                def __init__(self, func, target_event_type):
                    self.func = func
                    self.target_event_type = target_event_type
                    
                async def handle(self, event: Event) -> None:
                    await self.func(event)
                    
                def can_handle(self, event_type: EventType) -> bool:
                    return event_type == self.target_event_type
            
            wrapped_handler = FunctionHandler(handler_func, event_type)
            
            if event_type not in self.subscribers:
                self.subscribers[event_type] = []
            self.subscribers[event_type].append(wrapped_handler)
            logger.debug(f"Registered function handler for {event_type.value}")
            
        else:
            raise ValueError("Invalid arguments: provide either EventHandler instance or (EventType, function)")
    
    async def unsubscribe(self, event_handler: EventHandler) -> None:
        """イベントハンドラーの登録解除"""
        for event_type, handlers in self.subscribers.items():
            if event_handler in handlers:
                handlers.remove(event_handler)
                logger.debug(f"Unregistered handler {event_handler.__class__.__name__} for {event_type.value}")
                
    async def publish(self, event: Event, delay: float = 0) -> None:
        """イベントの発行"""
        if not self.running:
            raise RuntimeError("EventBus is not running. Call start() first.")
            
        if delay > 0:
            await asyncio.sleep(delay)
            
        # 優先度付きキューに追加（優先度が高いほど先に処理）
        priority_score = -event.priority  # 負数にして高優先度を先に
        await self.queue.put((priority_score, event.timestamp, event))
        logger.debug(f"Published event {event.type.value} with priority {event.priority}")
        
    async def start(self) -> None:
        """イベントバスの起動"""
        if self.running:
            return
            
        self.running = True
        logger.info("Starting EventBus...")
        
        # イベント処理タスクを開始
        task = asyncio.create_task(self._process_events())
        self._tasks.add(task)
        
        # デッドレター処理タスクを開始
        dead_letter_task = asyncio.create_task(self._process_dead_letters())
        self._tasks.add(dead_letter_task)
        
        logger.info("EventBus started successfully")
        
    async def stop(self) -> None:
        """イベントバスの停止"""
        if not self.running:
            return
            
        logger.info("Stopping EventBus...")
        self.running = False
        
        # 実行中のタスクをキャンセル
        for task in self._tasks:
            task.cancel()
            
        # タスクの完了を待機
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        
        logger.info("EventBus stopped successfully")
        
    async def _process_events(self) -> None:
        """イベント処理メインループ"""
        while self.running:
            try:
                # タイムアウト付きでイベントを取得
                _, _, event = await asyncio.wait_for(
                    self.queue.get(), 
                    timeout=1.0
                )
                
                # イベントを非同期で処理
                task = asyncio.create_task(self._dispatch_event(event))
                self._tasks.add(task)
                
                # 完了したタスクをクリーンアップ
                self._cleanup_completed_tasks()
                
            except asyncio.TimeoutError:
                # タイムアウトは正常（定期的なクリーンアップのため）
                continue
            except Exception as e:
                logger.error(f"Error in event processing loop: {e}")
                
    async def _dispatch_event(self, event: Event) -> None:
        """イベントをハンドラーにディスパッチ"""
        async with self._semaphore:
            try:
                handlers = self.subscribers.get(event.type, [])
                
                if not handlers:
                    logger.warning(f"No handlers registered for event type: {event.type.value}")
                    return
                
                # 全ハンドラーに並列でイベントを送信
                tasks = []
                for handler in handlers:
                    task = asyncio.create_task(
                        self._safe_handler_call(handler, event)
                    )
                    tasks.append(task)
                
                # 全ハンドラーの完了を待機
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # エラーハンドリング
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        await self._handle_handler_error(event, result, handlers[i])
                        
                logger.debug(f"Successfully dispatched event {event.type.value} to {len(handlers)} handlers")
                
            except Exception as e:
                logger.error(f"Critical error in event dispatch: {e}")
                await self._send_to_dead_letter(event, str(e))
    
    async def _safe_handler_call(self, handler: EventHandler, event: Event) -> None:
        """ハンドラーの安全な呼び出し"""
        try:
            start_time = time.time()
            await handler.handle(event)
            duration = time.time() - start_time
            logger.debug(f"Handler {handler.__class__.__name__} processed event in {duration:.3f}s")
            
        except Exception as e:
            logger.error(f"Handler {handler.__class__.__name__} failed: {e}")
            raise
    
    async def _handle_handler_error(self, event: Event, error: Exception, handler: EventHandler) -> None:
        """ハンドラーエラーの処理"""
        logger.error(f"Handler {handler.__class__.__name__} failed for event {event.type.value}: {error}")
        
        # リトライ制限チェック
        if event.retry_count < self.dead_letter_limit:
            # リトライ用にイベントを再発行
            retry_event = Event(
                type=event.type,
                workflow_id=event.workflow_id,
                data=event.data,
                timestamp=time.time(),
                retry_count=event.retry_count + 1,
                priority=event.priority,
                trace_id=event.trace_id
            )
            
            # 少し遅延してからリトライ
            delay = min(2 ** event.retry_count, 30)  # 指数バックオフ（最大30秒）
            await self.publish(retry_event, delay=delay)
            logger.info(f"Scheduled retry {retry_event.retry_count} for event {event.type.value}")
            
        else:
            # デッドレターキューに送信
            await self._send_to_dead_letter(event, str(error))
    
    async def _send_to_dead_letter(self, event: Event, error_message: str) -> None:
        """デッドレターキューへの送信"""
        dead_letter_event = {
            "event": event,
            "error": error_message,
            "failed_at": time.time()
        }
        await self.dead_letter_queue.put(dead_letter_event)
        logger.error(f"Sent event {event.type.value} to dead letter queue: {error_message}")
    
    async def _process_dead_letters(self) -> None:
        """デッドレター処理ループ"""
        while self.running:
            try:
                dead_letter = await asyncio.wait_for(
                    self.dead_letter_queue.get(),
                    timeout=5.0
                )
                
                # デッドレターを記録（将来的にはアラート送信等）
                logger.critical(f"Dead letter processed: {dead_letter}")
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing dead letters: {e}")
    
    def _cleanup_completed_tasks(self) -> None:
        """完了済みタスクのクリーンアップ"""
        completed_tasks = {task for task in self._tasks if task.done()}
        for task in completed_tasks:
            self._tasks.discard(task)
            
    async def get_stats(self) -> Dict[str, Any]:
        """イベントバスの統計情報を取得"""
        return {
            "running": self.running,
            "queue_size": self.queue.qsize(),
            "dead_letter_queue_size": self.dead_letter_queue.qsize(),
            "active_tasks": len(self._tasks),
            "subscribers": {
                event_type.value: len(handlers) 
                for event_type, handlers in self.subscribers.items()
            }
        } 