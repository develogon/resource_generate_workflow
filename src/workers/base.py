"""ワーカーの基底クラス."""

from abc import ABC, abstractmethod
from typing import Optional, Set, Dict, Any
import asyncio
import logging
import time

from ..config import Config
from ..models import Task, TaskStatus, TaskResult

logger = logging.getLogger(__name__)


class EventType:
    """イベントタイプ定数."""
    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_COMPLETED = "workflow.completed"
    WORKFLOW_FAILED = "workflow.failed"
    CHAPTER_PARSED = "chapter.parsed"
    SECTION_PARSED = "section.parsed"
    PARAGRAPH_PARSED = "paragraph.parsed"
    STRUCTURE_ANALYZED = "structure.analyzed"
    CONTENT_GENERATED = "content.generated"
    IMAGE_PROCESSED = "image.processed"
    THUMBNAIL_GENERATED = "thumbnail.generated"
    SECTION_AGGREGATED = "section.aggregated"
    CHAPTER_AGGREGATED = "chapter.aggregated"
    METADATA_GENERATED = "metadata.generated"
    REPORT_GENERATED = "report.generated"
    INTERMEDIATE_AGGREGATED = "intermediate.aggregated"


class Event:
    """イベントデータ構造."""
    
    def __init__(self, event_type: str, workflow_id: str, data: Dict[str, Any], 
                 timestamp: float = None, retry_count: int = 0, priority: int = 0,
                 trace_id: Optional[str] = None):
        self.type = event_type
        self.workflow_id = workflow_id
        self.data = data
        self.timestamp = timestamp or time.time()
        self.retry_count = retry_count
        self.priority = priority
        self.trace_id = trace_id


class BaseWorker(ABC):
    """ワーカーの基底クラス."""
    
    def __init__(self, config: Config, worker_id: str):
        """初期化."""
        self.config = config
        self.worker_id = worker_id
        self.event_bus: Optional[object] = None
        self.state_manager: Optional[object] = None
        self.metrics: Optional[object] = None
        self.subscriptions: Set[str] = set()
        self.semaphore = asyncio.Semaphore(config.workers.max_concurrent_tasks)
        self.running = False
        
    @abstractmethod
    def get_subscriptions(self) -> Set[str]:
        """購読するイベントタイプを返す."""
        pass
        
    @abstractmethod
    async def process(self, event: Event) -> None:
        """イベントを処理."""
        pass
        
    async def start(self, event_bus: object, state_manager: object = None, 
                   metrics: object = None) -> None:
        """ワーカーの起動."""
        self.event_bus = event_bus
        self.state_manager = state_manager
        self.metrics = metrics
        self.running = True
        
        # イベント購読
        for event_type in self.get_subscriptions():
            await self.event_bus.subscribe(event_type, self.handle_event)
            
        logger.info(f"Worker {self.worker_id} started")
        
    async def stop(self) -> None:
        """ワーカーの停止."""
        self.running = False
        logger.info(f"Worker {self.worker_id} stopped")
        
    async def handle_event(self, event: Event) -> None:
        """イベントハンドリング."""
        if not self.running:
            logger.warning(f"Worker {self.worker_id} received event while stopped")
            return
            
        async with self.semaphore:
            try:
                # 処理前チェックポイント
                await self.save_checkpoint(event, "started")
                
                # メトリクス記録開始
                start_time = time.time()
                
                # イベント処理
                await self.process(event)
                
                # メトリクス記録終了
                if self.metrics:
                    processing_time = time.time() - start_time
                    self.metrics.record_processing_time(
                        worker_type=self.__class__.__name__,
                        event_type=event.type,
                        duration=processing_time
                    )
                
                # 処理後チェックポイント
                await self.save_checkpoint(event, "completed")
                
            except Exception as e:
                await self.handle_error(event, e)
                
    async def save_checkpoint(self, event: Event, status: str) -> None:
        """チェックポイントの保存."""
        if self.state_manager:
            checkpoint_data = {
                "worker_id": self.worker_id,
                "event_type": event.type,
                "event_data": event.data,
                "status": status,
                "timestamp": time.time()
            }
            await self.state_manager.save_checkpoint(
                event.workflow_id, 
                f"{self.worker_id}_{status}",
                checkpoint_data
            )
            
    async def handle_error(self, event: Event, error: Exception) -> None:
        """エラーハンドリング."""
        logger.error(f"Worker {self.worker_id} error processing event {event.type}: {error}")
        
        # エラーチェックポイント保存
        await self.save_checkpoint(event, "failed")
        
        # メトリクス記録
        if self.metrics:
            self.metrics.record_error(
                worker_type=self.__class__.__name__,
                event_type=event.type,
                error_type=type(error).__name__
            )
            
        # エラーの重要度に応じた処理
        if self.should_retry(error, event):
            await self.retry_event(event)
        else:
            await self.fail_event(event, error)
            
    def should_retry(self, error: Exception, event: Event) -> bool:
        """リトライ判定."""
        # 基本的なリトライ判定ロジック
        if event.retry_count >= self.config.max_retries:
            return False
            
        # 特定のエラータイプはリトライしない
        non_retryable_errors = (ValueError, TypeError)
        if isinstance(error, non_retryable_errors):
            return False
            
        return True
        
    async def retry_event(self, event: Event) -> None:
        """イベントのリトライ."""
        if self.event_bus:
            retry_event = Event(
                event_type=event.type,
                workflow_id=event.workflow_id,
                data=event.data,
                retry_count=event.retry_count + 1,
                priority=event.priority,
                trace_id=event.trace_id
            )
            
            # 指数バックオフでリトライ
            delay = min(2 ** event.retry_count, 60)  # 最大60秒
            await self.event_bus.publish(retry_event, delay=delay)
            
    async def fail_event(self, event: Event, error: Exception) -> None:
        """イベントの失敗処理."""
        if self.event_bus:
            # 失敗イベントの発行
            failure_event = Event(
                event_type=EventType.WORKFLOW_FAILED,
                workflow_id=event.workflow_id,
                data={
                    "original_event": event.type,
                    "error": str(error),
                    "worker_id": self.worker_id
                }
            )
            await self.event_bus.publish(failure_event)
            
    def validate_event(self, event: Event) -> bool:
        """イベントの検証."""
        if not event or not event.type or not event.workflow_id:
            return False
        if event.type not in self.get_subscriptions():
            return False
        return True 