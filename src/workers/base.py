"""ワーカーの基底クラス."""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Optional, Set
from ..core.events import Event, EventType

logger = logging.getLogger(__name__)


class BaseWorker(ABC):
    """ワーカーの基底クラス."""
    
    def __init__(self, config, worker_id: str):
        """初期化."""
        self.config = config
        self.worker_id = worker_id
        self.event_bus = None
        self.state_manager = None
        self.metrics = None
        self.subscriptions: Set[EventType] = set()
        
        # 並行処理制御
        max_concurrent = getattr(config, 'max_concurrent_tasks', 10)
        self.semaphore = asyncio.Semaphore(max_concurrent)
        
        # 実行状態
        self._running = False
        self._processing_count = 0
        
    @abstractmethod
    def get_subscriptions(self) -> Set[EventType]:
        """購読するイベントタイプを返す."""
        pass
        
    @abstractmethod
    async def process(self, event: Event) -> None:
        """イベントを処理."""
        pass
        
    async def start(self, event_bus, state_manager):
        """ワーカーの起動."""
        self.event_bus = event_bus
        self.state_manager = state_manager
        
        # メトリクス取得（利用可能な場合）
        if hasattr(event_bus, 'metrics'):
            self.metrics = event_bus.metrics
            
        # イベント購読
        self.subscriptions = self.get_subscriptions()
        for event_type in self.subscriptions:
            await self.event_bus.subscribe(event_type, self.handle_event)
            
        self._running = True
        logger.info(f"Worker {self.worker_id} started")
        
    async def stop(self):
        """ワーカーの停止."""
        self._running = False
        
        # イベント購読解除
        if self.event_bus:
            for event_type in self.subscriptions:
                try:
                    await self.event_bus.unsubscribe(event_type, self.handle_event)
                except Exception as e:
                    logger.warning(f"Failed to unsubscribe from {event_type}: {e}")
                    
        # 実行中のタスクの完了を待機
        while self._processing_count > 0:
            await asyncio.sleep(0.1)
            
        logger.info(f"Worker {self.worker_id} stopped")
        
    async def handle_event(self, event: Event):
        """イベントハンドリング."""
        if not self._running:
            return
            
        async with self.semaphore:
            self._processing_count += 1
            try:
                # 処理前チェックポイント
                await self._save_checkpoint(event, "started")
                
                # メトリクス記録
                start_time = asyncio.get_event_loop().time()
                
                # イベント処理
                await self.process(event)
                
                # 処理時間の記録
                if self.metrics:
                    duration = asyncio.get_event_loop().time() - start_time
                    self.metrics.record_api_call(
                        api_name=self.__class__.__name__,
                        endpoint="process",
                        response_time=duration
                    )
                
                # 処理後チェックポイント
                await self._save_checkpoint(event, "completed")
                
                logger.debug(f"Worker {self.worker_id} processed event {event.type.value}")
                
            except Exception as e:
                await self._handle_error(event, e)
            finally:
                self._processing_count -= 1
                
    async def _save_checkpoint(self, event: Event, status: str):
        """チェックポイントの保存."""
        if self.state_manager:
            try:
                await self.state_manager.save_checkpoint(
                    workflow_id=event.workflow_id,
                    checkpoint_type=f"{self.worker_id}_{status}",
                    data={
                        "worker_id": self.worker_id,
                        "event_type": event.type.value,
                        "status": status,
                        "data": event.data
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to save checkpoint: {e}")
                
    async def _handle_error(self, event: Event, error: Exception):
        """エラーハンドリング."""
        logger.error(f"Worker {self.worker_id} failed to process event {event.type.value}: {error}")
        
        # エラーメトリクスの記録
        if self.metrics:
            self.metrics.record_event_processed(event.type.value, "failed")
            
        # エラーチェックポイントの保存
        await self._save_checkpoint(event, "failed")
        
        # リトライ可能なエラーの場合、イベントを再発行
        if self._is_retryable_error(error) and event.retry_count < 3:
            event.retry_count += 1
            await asyncio.sleep(event.retry_count * 2)  # 指数バックオフ
            await self.event_bus.publish(event)
            
    def _is_retryable_error(self, error: Exception) -> bool:
        """リトライ可能なエラーかどうかを判定."""
        # ネットワークエラーやAPIエラーはリトライ可能
        retryable_types = (
            ConnectionError,
            TimeoutError,
            # HTTPエラーなど、必要に応じて追加
        )
        return isinstance(error, retryable_types)
        
    def get_status(self) -> dict:
        """ワーカーの状態を取得."""
        return {
            "worker_id": self.worker_id,
            "running": self._running,
            "processing_count": self._processing_count,
            "subscriptions": [event_type.value for event_type in self.subscriptions]
        } 