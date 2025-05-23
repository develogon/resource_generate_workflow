"""ワーカープール管理システム."""

import asyncio
import logging
from typing import Dict, List, Optional, Type
from enum import Enum

from .base import BaseWorker
from .parser import ParserWorker
from .ai import AIWorker
from .media import MediaWorker
from .aggregator import AggregatorWorker

logger = logging.getLogger(__name__)


class WorkerType(Enum):
    """ワーカータイプ."""
    PARSER = "parser"
    AI = "ai"
    MEDIA = "media"
    AGGREGATOR = "aggregator"


class WorkerPool:
    """ワーカープール管理システム."""
    
    def __init__(self, config):
        """初期化."""
        self.config = config
        self.workers: Dict[WorkerType, List[BaseWorker]] = {}
        self.worker_classes: Dict[WorkerType, Type[BaseWorker]] = {
            WorkerType.PARSER: ParserWorker,
            WorkerType.AI: AIWorker,
            WorkerType.MEDIA: MediaWorker,
            WorkerType.AGGREGATOR: AggregatorWorker
        }
        self.event_bus = None
        self.state_manager = None
        self._initialized = False
        
    async def initialize(self, event_bus, state_manager):
        """ワーカープールの初期化."""
        if self._initialized:
            return
            
        self.event_bus = event_bus
        self.state_manager = state_manager
        
        # 各タイプのワーカーを作成
        for worker_type in WorkerType:
            await self._create_workers(worker_type)
            
        self._initialized = True
        logger.info("WorkerPool initialized")
        
    async def _create_workers(self, worker_type: WorkerType):
        """指定タイプのワーカーを作成."""
        worker_class = self.worker_classes[worker_type]
        worker_count = self._get_worker_count(worker_type)
        
        workers = []
        for i in range(worker_count):
            worker_id = f"{worker_type.value}-{i+1}"
            worker = worker_class(self.config, worker_id)
            workers.append(worker)
            
        self.workers[worker_type] = workers
        logger.info(f"Created {worker_count} {worker_type.value} workers")
        
    def _get_worker_count(self, worker_type: WorkerType) -> int:
        """ワーカータイプ別の初期ワーカー数を取得."""
        # 設定から取得、デフォルト値を設定
        worker_counts = getattr(self.config, 'worker_counts', {})
        defaults = {
            WorkerType.PARSER: 2,
            WorkerType.AI: 3,
            WorkerType.MEDIA: 2,
            WorkerType.AGGREGATOR: 1
        }
        return worker_counts.get(worker_type.value, defaults[worker_type])
        
    async def start(self):
        """ワーカープールの開始."""
        if not self._initialized:
            raise RuntimeError("WorkerPool not initialized")
            
        # 全ワーカーを開始
        for worker_type, worker_list in self.workers.items():
            for worker in worker_list:
                await worker.start(self.event_bus, self.state_manager)
                
        logger.info("All workers started")
        
    async def stop(self):
        """ワーカープールの停止."""
        # 全ワーカーを停止
        for worker_type, worker_list in self.workers.items():
            for worker in worker_list:
                try:
                    await worker.stop()
                except Exception as e:
                    logger.error(f"Error stopping worker {worker.worker_id}: {e}")
                    
        logger.info("All workers stopped")
        
    async def shutdown(self):
        """ワーカープールのシャットダウン."""
        await self.stop()
        self.workers.clear()
        self._initialized = False
        logger.info("WorkerPool shutdown completed")
        
    def get_worker(self, worker_type: WorkerType) -> Optional[BaseWorker]:
        """指定タイプの利用可能なワーカーを取得."""
        workers = self.workers.get(worker_type, [])
        if not workers:
            return None
            
        # 最初の利用可能なワーカーを返す
        # TODO: より高度な負荷分散アルゴリズムを実装
        return workers[0] if workers else None
        
    def get_workers(self, worker_type: WorkerType) -> List[BaseWorker]:
        """指定タイプの全ワーカーを取得."""
        return self.workers.get(worker_type, []).copy()
        
    async def scale_workers(self, worker_type: WorkerType, target_count: int):
        """ワーカー数をスケーリング."""
        current_workers = self.workers.get(worker_type, [])
        current_count = len(current_workers)
        
        if target_count == current_count:
            return
            
        if target_count > current_count:
            # ワーカーを追加
            await self._add_workers(worker_type, target_count - current_count)
        else:
            # ワーカーを削除
            await self._remove_workers(worker_type, current_count - target_count)
            
        logger.info(f"Scaled {worker_type.value} workers from {current_count} to {target_count}")
        
    async def _add_workers(self, worker_type: WorkerType, count: int):
        """ワーカーを追加."""
        worker_class = self.worker_classes[worker_type]
        current_workers = self.workers.get(worker_type, [])
        current_count = len(current_workers)
        
        new_workers = []
        for i in range(count):
            worker_id = f"{worker_type.value}-{current_count + i + 1}"
            worker = worker_class(self.config, worker_id)
            
            # ワーカーを開始
            if self.event_bus and self.state_manager:
                await worker.start(self.event_bus, self.state_manager)
                
            new_workers.append(worker)
            
        current_workers.extend(new_workers)
        self.workers[worker_type] = current_workers
        
    async def _remove_workers(self, worker_type: WorkerType, count: int):
        """ワーカーを削除."""
        current_workers = self.workers.get(worker_type, [])
        
        # 後ろから削除
        workers_to_remove = current_workers[-count:]
        remaining_workers = current_workers[:-count]
        
        # ワーカーを停止
        for worker in workers_to_remove:
            try:
                await worker.stop()
            except Exception as e:
                logger.error(f"Error stopping worker {worker.worker_id}: {e}")
                
        self.workers[worker_type] = remaining_workers
        
    def get_worker_stats(self) -> Dict[str, Dict[str, int]]:
        """ワーカー統計情報を取得."""
        stats = {}
        
        for worker_type, worker_list in self.workers.items():
            stats[worker_type.value] = {
                "total": len(worker_list),
                "active": sum(1 for w in worker_list if getattr(w, '_running', False)),
                "idle": sum(1 for w in worker_list if not getattr(w, '_running', False))
            }
            
        return stats
        
    async def get_worker_health(self) -> Dict[str, Dict[str, bool]]:
        """ワーカーヘルス状態を取得."""
        health = {}
        
        for worker_type, worker_list in self.workers.items():
            worker_health = {}
            
            for worker in worker_list:
                try:
                    # ワーカーのヘルスチェック
                    is_healthy = await self._check_worker_health(worker)
                    worker_health[worker.worker_id] = is_healthy
                except Exception as e:
                    logger.error(f"Health check failed for {worker.worker_id}: {e}")
                    worker_health[worker.worker_id] = False
                    
            health[worker_type.value] = worker_health
            
        return health
        
    async def _check_worker_health(self, worker: BaseWorker) -> bool:
        """個別ワーカーのヘルスチェック."""
        # 基本的なヘルスチェック
        return hasattr(worker, 'worker_id') and worker.worker_id is not None 