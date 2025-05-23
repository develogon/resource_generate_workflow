"""
ワークフローオーケストレーター - WorkflowOrchestrator

このモジュールはワークフロー全体の制御を担当します：
- ワークフローの初期化と実行
- イベント駆動による処理制御
- ワーカープールの管理
- エラーハンドリングと復旧
- 進捗監視とメトリクス収集
"""

import asyncio
import time
import uuid
import logging
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, field
from enum import Enum

from .events import EventBus, Event, EventType
from .state import StateManager, WorkflowContext, WorkflowStatus
from .metrics import MetricsCollector
from ..workers.pool import WorkerPool
from ..config.settings import Config

logger = logging.getLogger(__name__)


class WorkerType(Enum):
    """ワーカータイプ"""
    PARSER = "parser"
    AI_GENERATOR = "ai_generator"
    MEDIA_PROCESSOR = "media_processor"
    AGGREGATOR = "aggregator"


@dataclass
class WorkerConfig:
    """ワーカー設定"""
    worker_type: WorkerType
    max_concurrent_tasks: int = 3
    timeout_seconds: int = 300
    retry_attempts: int = 3
    enabled: bool = True


class BaseWorker:
    """ワーカーの基底クラス"""
    
    def __init__(self, worker_id: str, config: WorkerConfig):
        self.worker_id = worker_id
        self.config = config
        self.event_bus: Optional[EventBus] = None
        self.state_manager: Optional[StateManager] = None
        self.metrics: Optional[MetricsCollector] = None
        self.semaphore = asyncio.Semaphore(config.max_concurrent_tasks)
        self.subscriptions: Set[EventType] = set()
        
    def get_subscriptions(self) -> Set[EventType]:
        """購読するイベントタイプを返す"""
        return self.subscriptions
        
    def can_handle(self, event_type: EventType) -> bool:
        """指定されたイベントタイプを処理できるかチェック"""
        return event_type in self.subscriptions
        
    async def handle(self, event: Event) -> None:
        """イベントハンドラーインターフェース"""
        await self.handle_event(event)
        
    async def initialize(self, event_bus: EventBus, state_manager: StateManager, 
                        metrics: MetricsCollector):
        """ワーカーの初期化"""
        self.event_bus = event_bus
        self.state_manager = state_manager
        self.metrics = metrics
        
        # イベント購読
        for event_type in self.subscriptions:
            await self.event_bus.subscribe(event_type, self.handle)
            
        logger.info(f"Worker {self.worker_id} initialized")
        
    async def handle_event(self, event: Event) -> None:
        """イベントハンドリング"""
        if not self.config.enabled:
            return
            
        # 購読していないイベントは無視
        if not self.can_handle(event.type):
            return
            
        async with self.semaphore:
            start_time = time.time()
            
            try:
                # メトリクス記録開始
                self.metrics.increment_counter(
                    f"worker.{self.config.worker_type.value}.events_processed"
                )
                
                # 処理実行
                await self.process_event(event)
                
                # 成功メトリクス
                duration = time.time() - start_time
                self.metrics.record_timer(
                    f"worker.{self.config.worker_type.value}.processing_time",
                    duration
                )
                
                logger.debug(f"Worker {self.worker_id} processed event {event.type.value}")
                
            except Exception as e:
                # エラーメトリクス
                self.metrics.increment_counter(
                    f"worker.{self.config.worker_type.value}.errors"
                )
                
                logger.error(f"Worker {self.worker_id} failed to process event: {e}")
                
                # エラーイベントを発行
                await self._publish_error_event(event, e)
                
    async def process_event(self, event: Event) -> None:
        """イベント処理（サブクラスで実装）"""
        raise NotImplementedError
        
    async def _publish_error_event(self, original_event: Event, error: Exception):
        """エラーイベントを発行"""
        if self.event_bus:
            error_event = Event(
                type=EventType.TASK_FAILED,
                workflow_id=original_event.workflow_id,
                data={
                    "worker_id": self.worker_id,
                    "original_event_type": original_event.type.value,
                    "error": str(error),
                    "timestamp": time.time()
                }
            )
            await self.event_bus.publish(error_event)


class MockParserWorker(BaseWorker):
    """パーサーワーカー（モック実装）"""
    
    def __init__(self, worker_id: str = "parser_worker"):
        config = WorkerConfig(worker_type=WorkerType.PARSER)
        super().__init__(worker_id, config)
        self.subscriptions = {
            EventType.WORKFLOW_STARTED,
            EventType.CHAPTER_PARSED,
            EventType.SECTION_PARSED
        }
        
    async def process_event(self, event: Event) -> None:
        """イベント処理"""
        if event.type == EventType.WORKFLOW_STARTED:
            await self._parse_document(event)
        elif event.type == EventType.CHAPTER_PARSED:
            await self._parse_sections(event)
        elif event.type == EventType.SECTION_PARSED:
            await self._parse_paragraphs(event)
            
    async def _parse_document(self, event: Event):
        """ドキュメントをチャプターに分割"""
        await asyncio.sleep(0.1)  # 処理時間をシミュレート
        
        # モックデータ：3つのチャプターを生成
        for i in range(3):
            chapter_event = Event(
                type=EventType.CHAPTER_PARSED,
                workflow_id=event.workflow_id,
                data={
                    "chapter_index": i,
                    "title": f"Chapter {i+1}",
                    "content": f"Content of chapter {i+1}"
                }
            )
            await self.event_bus.publish(chapter_event)
            
    async def _parse_sections(self, event: Event):
        """チャプターをセクションに分割"""
        await asyncio.sleep(0.05)
        
        chapter_index = event.data.get("chapter_index", 0)
        
        # モックデータ：各チャプターに2つのセクション
        for i in range(2):
            section_event = Event(
                type=EventType.SECTION_PARSED,
                workflow_id=event.workflow_id,
                data={
                    "chapter_index": chapter_index,
                    "section_index": i,
                    "title": f"Section {chapter_index+1}.{i+1}",
                    "content": f"Content of section {chapter_index+1}.{i+1}"
                }
            )
            await self.event_bus.publish(section_event)
            
    async def _parse_paragraphs(self, event: Event):
        """セクションをパラグラフに分割"""
        await asyncio.sleep(0.02)
        
        # パラグラフ解析完了イベント
        paragraph_event = Event(
            type=EventType.PARAGRAPH_PARSED,
            workflow_id=event.workflow_id,
            data={
                "chapter_index": event.data.get("chapter_index"),
                "section_index": event.data.get("section_index"),
                "paragraph_count": 3
            }
        )
        await self.event_bus.publish(paragraph_event)


class MockAggregatorWorker(BaseWorker):
    """集約ワーカー（モック実装）"""
    
    def __init__(self, worker_id: str = "aggregator_worker"):
        config = WorkerConfig(worker_type=WorkerType.AGGREGATOR)
        super().__init__(worker_id, config)
        self.subscriptions = {EventType.PARAGRAPH_PARSED}
        self.completion_tracker: Dict[str, Set[str]] = {}
        
    async def process_event(self, event: Event) -> None:
        """イベント処理"""
        if event.type == EventType.PARAGRAPH_PARSED:
            await self._track_completion(event)
            
    async def _track_completion(self, event: Event):
        """完了状況を追跡"""
        workflow_id = event.workflow_id
        
        if workflow_id not in self.completion_tracker:
            self.completion_tracker[workflow_id] = set()
            
        # セクション完了をマーク
        section_key = f"{event.data.get('chapter_index')}.{event.data.get('section_index')}"
        self.completion_tracker[workflow_id].add(section_key)
        
        # 全セクション完了チェック（3チャプター × 2セクション = 6セクション）
        if len(self.completion_tracker[workflow_id]) >= 6:
            completion_event = Event(
                type=EventType.WORKFLOW_COMPLETED,
                workflow_id=workflow_id,
                data={"completed_sections": list(self.completion_tracker[workflow_id])}
            )
            await self.event_bus.publish(completion_event)
            
            # トラッカーをクリア
            del self.completion_tracker[workflow_id]


class WorkflowCompletionHandler:
    """ワークフロー完了ハンドラー"""
    
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        
    def can_handle(self, event_type: EventType) -> bool:
        """処理可能なイベントタイプかチェック"""
        return event_type in {EventType.WORKFLOW_COMPLETED, EventType.WORKFLOW_FAILED}
        
    async def handle(self, event: Event) -> None:
        """イベント処理"""
        if event.type == EventType.WORKFLOW_COMPLETED:
            await self.orchestrator._handle_workflow_completion(event)
        elif event.type == EventType.WORKFLOW_FAILED:
            await self.orchestrator._handle_workflow_failure(event)


class WorkflowOrchestrator:
    """ワークフロー全体を制御するオーケストレーター"""
    
    def __init__(self, config: Config):
        """初期化."""
        self.config = config
        self.event_bus = EventBus(config)
        self.state_manager = StateManager(config)
        self.metrics = MetricsCollector()
        self.worker_pool = WorkerPool(config)
        self._running = False
        
    async def initialize(self):
        """オーケストレーターの初期化."""
        logger.info("Initializing orchestrator...")
        
        # 状態管理の初期化
        await self.state_manager.initialize()
        
        # イベントバスの開始
        await self.event_bus.start()
        
        # ワーカープールの初期化
        await self.worker_pool.initialize(self.event_bus, self.state_manager)
        
        self._running = True
        logger.info("Orchestrator initialized successfully")
        
    async def shutdown(self):
        """オーケストレーターのシャットダウン."""
        logger.info("Shutting down orchestrator...")
        
        self._running = False
        
        # ワーカープールの停止
        await self.worker_pool.shutdown()
        
        # イベントバスの停止
        await self.event_bus.stop()
        
        # 状態管理の終了
        await self.state_manager.close()
        
        logger.info("Orchestrator shutdown completed")
        
    async def execute(self, lang: str, title: str, input_file: Optional[str] = None) -> WorkflowContext:
        """ワークフローの実行."""
        if not self._running:
            await self.initialize()
            
        # ワークフロー初期化
        context = await self._initialize_workflow(lang, title, input_file)
        
        try:
            logger.info(f"Starting workflow {context.workflow_id}")
            
            # メトリクス記録
            self.metrics.workflows_started.inc()
            
            # ワーカープールの起動
            await self.worker_pool.start()
            
            # 初期イベント発行
            await self.event_bus.publish(Event(
                type=EventType.WORKFLOW_STARTED,
                workflow_id=context.workflow_id,
                data={
                    "lang": lang,
                    "title": title,
                    "input_file": input_file
                }
            ))
            
            # ワークフロー完了待機
            await self._wait_for_completion(context)
            
            # 成功時の処理
            context.status = WorkflowStatus.COMPLETED
            await self.state_manager.save_workflow_state(context.workflow_id, {
                "status": context.status.value,
                "completed_at": time.time()
            })
            
            self.metrics.workflows_completed.inc()
            logger.info(f"Workflow {context.workflow_id} completed successfully")
            
            return context
            
        except Exception as e:
            logger.error(f"Workflow {context.workflow_id} failed: {e}")
            await self._handle_failure(context, e)
            raise
        finally:
            await self.worker_pool.stop()
    
    async def resume(self, workflow_id: str) -> WorkflowContext:
        """中断したワークフローの再開."""
        logger.info(f"Resuming workflow {workflow_id}")
        
        # 状態の復元
        context = await self.state_manager.load_context(workflow_id)
        if not context:
            raise ValueError(f"Workflow {workflow_id} not found")
            
        checkpoint = await self.state_manager.get_latest_checkpoint(workflow_id)
        
        # チェックポイントからイベントを再構築
        await self._replay_from_checkpoint(context, checkpoint)
        
        # 実行を継続
        return await self.execute(context.lang, context.title, context.input_file)
    
    async def _initialize_workflow(self, lang: str, title: str, input_file: Optional[str]) -> WorkflowContext:
        """ワークフローの初期化."""
        workflow_id = f"workflow-{uuid.uuid4().hex[:8]}"
        
        context = WorkflowContext(
            workflow_id=workflow_id,
            lang=lang,
            title=title,
            status=WorkflowStatus.INITIALIZED,
            metadata={
                "lang": lang,
                "title": title,
                "input_file": input_file,
                "created_at": time.time()
            },
            checkpoints=[],
            input_file=input_file
        )
        
        # 初期状態を保存
        await self.state_manager.save_workflow_state(workflow_id, {
            "status": context.status.value,
            "lang": lang,
            "title": title,
            "input_file": input_file,
            "created_at": context.created_at
        })
        
        return context
    
    async def _wait_for_completion(self, context: WorkflowContext, timeout: float = 3600):
        """ワークフロー完了の待機."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # 状態をチェック
            state = await self.state_manager.get_workflow_state(context.workflow_id)
            if state and state.get("status") == "completed":
                return
                
            # 少し待機
            await asyncio.sleep(1)
            
        raise TimeoutError(f"Workflow {context.workflow_id} timed out")
    
    async def _handle_failure(self, context: WorkflowContext, error: Exception):
        """失敗処理."""
        context.status = WorkflowStatus.FAILED
        
        await self.state_manager.save_workflow_state(context.workflow_id, {
            "status": context.status.value,
            "error": str(error),
            "failed_at": time.time()
        })
        
        self.metrics.workflows_failed.inc()
    
    async def _replay_from_checkpoint(self, context: WorkflowContext, checkpoint: Dict):
        """チェックポイントからのリプレイ."""
        logger.info(f"Replaying from checkpoint: {checkpoint.get('step', 'unknown') if checkpoint else 'none'}")
        # チェックポイントからの復元ロジックを実装
        # Phase 1では基本的な実装のみ
        pass
        
    async def _handle_workflow_completion(self, event: Event):
        """ワークフロー完了ハンドラー"""
        workflow_id = event.workflow_id
        
        if workflow_id in self.active_workflows:
            context = self.active_workflows[workflow_id]
            context.update_status(WorkflowStatus.COMPLETED)
            await self.state_manager.update_workflow_state(workflow_id, status=WorkflowStatus.COMPLETED)
            
            # 開始時間から経過時間を計算
            start_time = self.workflow_start_times.get(workflow_id, context.created_at)
            duration = time.time() - start_time
            
            # メトリクス記録
            self.workflow_metrics.record_workflow_completed(workflow_id, duration)
            
            logger.info(f"Workflow {workflow_id} completed successfully in {duration:.2f}s")
            
        # 完了イベントをセット
        if workflow_id in self.completion_events:
            self.completion_events[workflow_id].set()
            
    async def _handle_workflow_failure(self, event: Event):
        """ワークフロー失敗ハンドラー"""
        workflow_id = event.workflow_id
        error_msg = event.data.get("error", "Unknown error")
        
        if workflow_id in self.active_workflows:
            context = self.active_workflows[workflow_id]
            context.update_status(WorkflowStatus.FAILED)
            await self.state_manager.update_workflow_state(workflow_id, status=WorkflowStatus.FAILED)
            
            # メトリクス記録
            self.workflow_metrics.record_workflow_failed(workflow_id, error_msg)
            
            logger.error(f"Workflow {workflow_id} failed: {error_msg}")
            
        # 完了イベントをセット（失敗も完了として扱う）
        if workflow_id in self.completion_events:
            self.completion_events[workflow_id].set()
            
    async def get_workflow_status(self, workflow_id: str) -> Optional[WorkflowContext]:
        """ワークフロー状況を取得"""
        if workflow_id in self.active_workflows:
            return self.active_workflows[workflow_id]
            
        # 状態管理から取得
        state = await self.state_manager.get_workflow_state(workflow_id)
        if state:
            return WorkflowContext(
                workflow_id=workflow_id,
                lang=state.lang,
                title=state.title,
                status=state.status,
                metadata=state.metadata,
                created_at=state.created_at,
                updated_at=state.updated_at
            )
            
        return None
        
    def get_active_workflows(self) -> List[WorkflowContext]:
        """アクティブなワークフロー一覧を取得"""
        return list(self.active_workflows.values())
        
    def get_metrics_summary(self) -> Dict[str, Any]:
        """メトリクス概要を取得"""
        return self.metrics.get_all_metrics() 