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

from .event_bus import EventBus, Event, EventType, EventHandler
from .state_manager import StateManager, WorkflowStatus
from .metrics import MetricsCollector, WorkflowMetrics

logger = logging.getLogger(__name__)


class WorkerType(Enum):
    """ワーカータイプ"""
    PARSER = "parser"
    AI_GENERATOR = "ai_generator"
    MEDIA_PROCESSOR = "media_processor"
    AGGREGATOR = "aggregator"


@dataclass
class WorkflowContext:
    """ワークフロー実行コンテキスト"""
    workflow_id: str
    lang: str
    title: str
    status: WorkflowStatus
    metadata: Dict[str, Any] = field(default_factory=dict)
    checkpoints: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    
    def update_status(self, status: WorkflowStatus):
        """ステータスを更新"""
        self.status = status
        self.updated_at = time.time()


@dataclass
class WorkerConfig:
    """ワーカー設定"""
    worker_type: WorkerType
    max_concurrent_tasks: int = 3
    timeout_seconds: int = 300
    retry_attempts: int = 3
    enabled: bool = True


class BaseWorker(EventHandler):
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
        """EventHandlerインターフェースの実装"""
        await self.handle_event(event)
        
    async def initialize(self, event_bus: EventBus, state_manager: StateManager, 
                        metrics: MetricsCollector):
        """ワーカーの初期化"""
        self.event_bus = event_bus
        self.state_manager = state_manager
        self.metrics = metrics
        
        # イベント購読（EventHandlerとして登録）
        await self.event_bus.subscribe(self)
            
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


class WorkflowCompletionHandler(EventHandler):
    """ワークフロー完了ハンドラー"""
    
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        
    def can_handle(self, event_type: EventType) -> bool:
        """処理可能なイベントタイプをチェック"""
        return event_type in {EventType.WORKFLOW_COMPLETED, EventType.WORKFLOW_FAILED}
        
    async def handle(self, event: Event) -> None:
        """イベント処理"""
        if event.type == EventType.WORKFLOW_COMPLETED:
            await self.orchestrator._handle_workflow_completion(event)
        elif event.type == EventType.WORKFLOW_FAILED:
            await self.orchestrator._handle_workflow_failure(event)


class WorkflowOrchestrator:
    """ワークフロー全体を制御するオーケストレーター"""
    
    def __init__(self, max_concurrent_workflows: int = 5):
        self.max_concurrent_workflows = max_concurrent_workflows
        self.event_bus = EventBus()
        self.state_manager = StateManager()
        self.metrics = MetricsCollector()
        self.workflow_metrics = WorkflowMetrics(self.metrics)
        
        # ワーカープール
        self.workers: List[BaseWorker] = []
        self.active_workflows: Dict[str, WorkflowContext] = {}
        self.completion_events: Dict[str, asyncio.Event] = {}
        self.workflow_start_times: Dict[str, float] = {}  # ワークフロー開始時間を保存
        
        # セマフォで同時実行数を制限
        self.workflow_semaphore = asyncio.Semaphore(max_concurrent_workflows)
        
        # 完了ハンドラー
        self.completion_handler = WorkflowCompletionHandler(self)
        
    async def initialize(self):
        """オーケストレーターの初期化"""
        # イベントバス開始
        await self.event_bus.start()
        
        # ワーカーの初期化
        self.workers = [
            MockParserWorker(),
            MockAggregatorWorker()
        ]
        
        for worker in self.workers:
            await worker.initialize(self.event_bus, self.state_manager, self.metrics)
            
        # 完了イベントの購読
        await self.event_bus.subscribe(self.completion_handler)
        
        logger.info("WorkflowOrchestrator initialized")
        
    async def shutdown(self):
        """オーケストレーターの終了"""
        await self.event_bus.stop()
        logger.info("WorkflowOrchestrator shutdown")
        
    async def execute_workflow(self, lang: str, title: str, 
                             metadata: Optional[Dict[str, Any]] = None) -> WorkflowContext:
        """ワークフローの実行"""
        async with self.workflow_semaphore:
            workflow_id = str(uuid.uuid4())
            start_time = time.time()  # 開始時間を記録
            
            # ワークフローコンテキストの作成
            context = WorkflowContext(
                workflow_id=workflow_id,
                lang=lang,
                title=title,
                status=WorkflowStatus.INITIALIZED,
                metadata=metadata or {}
            )
            
            # 完了イベントの準備
            completion_event = asyncio.Event()
            self.completion_events[workflow_id] = completion_event
            self.active_workflows[workflow_id] = context
            self.workflow_start_times[workflow_id] = start_time  # 開始時間を保存
            
            try:
                # 状態管理に登録
                await self.state_manager.create_workflow(
                    workflow_id, lang, title, metadata
                )
                
                # メトリクス記録
                self.workflow_metrics.record_workflow_started(workflow_id)
                self.workflow_metrics.set_active_workflows(len(self.active_workflows))
                
                # ワークフロー開始
                context.update_status(WorkflowStatus.RUNNING)
                await self.state_manager.update_workflow_state(workflow_id, status=WorkflowStatus.RUNNING)
                
                # 初期イベント発行
                start_event = Event(
                    type=EventType.WORKFLOW_STARTED,
                    workflow_id=workflow_id,
                    data={"lang": lang, "title": title, "metadata": metadata}
                )
                await self.event_bus.publish(start_event)
                
                logger.info(f"Started workflow {workflow_id}: {title}")
                
                # 完了待機（タイムアウト付き）
                try:
                    await asyncio.wait_for(completion_event.wait(), timeout=300.0)
                except asyncio.TimeoutError:
                    context.update_status(WorkflowStatus.FAILED)
                    await self.state_manager.update_workflow_state(workflow_id, status=WorkflowStatus.FAILED)
                    self.workflow_metrics.record_workflow_failed(workflow_id, "timeout")
                    raise TimeoutError(f"Workflow {workflow_id} timed out")
                
                return context
                
            except Exception as e:
                context.update_status(WorkflowStatus.FAILED)
                await self.state_manager.update_workflow_state(workflow_id, status=WorkflowStatus.FAILED)
                self.workflow_metrics.record_workflow_failed(workflow_id, str(e))
                logger.error(f"Workflow {workflow_id} failed: {e}")
                raise
                
            finally:
                # クリーンアップ
                if workflow_id in self.completion_events:
                    del self.completion_events[workflow_id]
                if workflow_id in self.active_workflows:
                    del self.active_workflows[workflow_id]
                if workflow_id in self.workflow_start_times:
                    del self.workflow_start_times[workflow_id]
                self.workflow_metrics.set_active_workflows(len(self.active_workflows))
                
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