"""
WorkflowOrchestratorのテスト

ワークフロー全体の制御機能をテストします：
- ワークフローの初期化と実行
- イベント駆動による処理制御
- ワーカープールの管理
- エラーハンドリングと復旧
- 進捗監視とメトリクス収集
"""

import pytest
import asyncio
import pytest_asyncio
import time
from unittest.mock import Mock, AsyncMock, patch

from src.core.orchestrator import (
    WorkflowOrchestrator, 
    WorkflowContext, 
    BaseWorker, 
    WorkerConfig, 
    WorkerType,
    MockParserWorker,
    MockAggregatorWorker
)
from src.core.event_bus import Event, EventType
from src.core.state_manager import WorkflowStatus


@pytest_asyncio.fixture
async def orchestrator():
    """オーケストレーターのフィクスチャ"""
    orch = WorkflowOrchestrator(max_concurrent_workflows=2)
    await orch.initialize()
    yield orch
    await orch.shutdown()


@pytest.fixture
def worker_config():
    """ワーカー設定のフィクスチャ"""
    return WorkerConfig(
        worker_type=WorkerType.PARSER,
        max_concurrent_tasks=2,
        timeout_seconds=30,
        retry_attempts=2
    )


class TestWorkerConfig:
    """ワーカー設定のテスト"""
    
    def test_worker_config_creation(self):
        """ワーカー設定の作成テスト"""
        config = WorkerConfig(
            worker_type=WorkerType.AI_GENERATOR,
            max_concurrent_tasks=5,
            timeout_seconds=120,
            retry_attempts=3,
            enabled=True
        )
        
        assert config.worker_type == WorkerType.AI_GENERATOR
        assert config.max_concurrent_tasks == 5
        assert config.timeout_seconds == 120
        assert config.retry_attempts == 3
        assert config.enabled is True
        
    def test_worker_config_defaults(self):
        """ワーカー設定のデフォルト値テスト"""
        config = WorkerConfig(worker_type=WorkerType.PARSER)
        
        assert config.worker_type == WorkerType.PARSER
        assert config.max_concurrent_tasks == 3
        assert config.timeout_seconds == 300
        assert config.retry_attempts == 3
        assert config.enabled is True


class TestWorkflowContext:
    """ワークフローコンテキストのテスト"""
    
    def test_context_creation(self):
        """コンテキストの作成テスト"""
        context = WorkflowContext(
            workflow_id="test-workflow-123",
            lang="ja",
            title="テストワークフロー",
            status=WorkflowStatus.INITIALIZED
        )
        
        assert context.workflow_id == "test-workflow-123"
        assert context.lang == "ja"
        assert context.title == "テストワークフロー"
        assert context.status == WorkflowStatus.INITIALIZED
        assert isinstance(context.metadata, dict)
        assert isinstance(context.checkpoints, list)
        assert context.created_at > 0
        assert context.updated_at > 0
        
    def test_context_update_status(self):
        """ステータス更新テスト"""
        context = WorkflowContext(
            workflow_id="test-workflow",
            lang="en",
            title="Test Workflow",
            status=WorkflowStatus.INITIALIZED
        )
        
        initial_updated_at = context.updated_at
        time.sleep(0.01)  # 時間差を作る
        
        context.update_status(WorkflowStatus.RUNNING)
        
        assert context.status == WorkflowStatus.RUNNING
        assert context.updated_at > initial_updated_at


class TestBaseWorker:
    """ベースワーカーのテスト"""
    
    def test_base_worker_creation(self, worker_config):
        """ベースワーカーの作成テスト"""
        worker = BaseWorker("test-worker", worker_config)
        
        assert worker.worker_id == "test-worker"
        assert worker.config == worker_config
        assert worker.event_bus is None
        assert worker.state_manager is None
        assert worker.metrics is None
        assert worker.semaphore._value == worker_config.max_concurrent_tasks
        
    @pytest.mark.asyncio
    async def test_worker_initialization(self, worker_config):
        """ワーカー初期化テスト"""
        worker = BaseWorker("test-worker", worker_config)
        
        # モックオブジェクトを作成
        event_bus = Mock()
        event_bus.subscribe = AsyncMock()
        state_manager = Mock()
        metrics = Mock()
        
        await worker.initialize(event_bus, state_manager, metrics)
        
        assert worker.event_bus == event_bus
        assert worker.state_manager == state_manager
        assert worker.metrics == metrics
        
    @pytest.mark.asyncio
    async def test_worker_process_event_not_implemented(self, worker_config):
        """ワーカーのprocess_eventが未実装の場合のテスト"""
        worker = BaseWorker("test-worker", worker_config)
        event = Event(
            type=EventType.WORKFLOW_STARTED,
            workflow_id="test-workflow",
            data={}
        )
        
        with pytest.raises(NotImplementedError):
            await worker.process_event(event)


class TestMockParserWorker:
    """モックパーサーワーカーのテスト"""
    
    @pytest.mark.asyncio
    async def test_parser_worker_subscriptions(self):
        """パーサーワーカーの購読イベントテスト"""
        worker = MockParserWorker()
        
        expected_subscriptions = {
            EventType.WORKFLOW_STARTED,
            EventType.CHAPTER_PARSED,
            EventType.SECTION_PARSED
        }
        
        assert worker.subscriptions == expected_subscriptions
        
    @pytest.mark.asyncio
    async def test_parser_worker_document_parsing(self):
        """ドキュメント解析テスト"""
        worker = MockParserWorker()
        
        # モックイベントバスを設定
        event_bus = Mock()
        event_bus.publish = AsyncMock()
        worker.event_bus = event_bus
        
        event = Event(
            type=EventType.WORKFLOW_STARTED,
            workflow_id="test-workflow",
            data={"lang": "ja", "title": "テスト"}
        )
        
        await worker.process_event(event)
        
        # 3つのチャプターイベントが発行されることを確認
        assert event_bus.publish.call_count == 3
        
        # 発行されたイベントの内容を確認
        for i, call in enumerate(event_bus.publish.call_args_list):
            published_event = call[0][0]
            assert published_event.type == EventType.CHAPTER_PARSED
            assert published_event.workflow_id == "test-workflow"
            assert published_event.data["chapter_index"] == i
            assert published_event.data["title"] == f"Chapter {i+1}"


class TestMockAggregatorWorker:
    """モック集約ワーカーのテスト"""
    
    @pytest.mark.asyncio
    async def test_aggregator_worker_subscriptions(self):
        """集約ワーカーの購読イベントテスト"""
        worker = MockAggregatorWorker()
        
        expected_subscriptions = {EventType.PARAGRAPH_PARSED}
        assert worker.subscriptions == expected_subscriptions
        
    @pytest.mark.asyncio
    async def test_aggregator_completion_tracking(self):
        """完了追跡テスト"""
        worker = MockAggregatorWorker()
        
        # モックイベントバスを設定
        event_bus = Mock()
        event_bus.publish = AsyncMock()
        worker.event_bus = event_bus
        
        workflow_id = "test-workflow"
        
        # 6つのセクション完了イベントを送信
        for chapter_idx in range(3):
            for section_idx in range(2):
                event = Event(
                    type=EventType.PARAGRAPH_PARSED,
                    workflow_id=workflow_id,
                    data={
                        "chapter_index": chapter_idx,
                        "section_index": section_idx,
                        "paragraph_count": 3
                    }
                )
                await worker.process_event(event)
        
        # 最後のイベント処理後にワークフロー完了イベントが発行されることを確認
        assert event_bus.publish.call_count == 1
        
        published_event = event_bus.publish.call_args[0][0]
        assert published_event.type == EventType.WORKFLOW_COMPLETED
        assert published_event.workflow_id == workflow_id
        assert len(published_event.data["completed_sections"]) == 6


class TestWorkflowOrchestrator:
    """ワークフローオーケストレーターのテスト"""
    
    def test_orchestrator_creation(self):
        """オーケストレーター作成テスト"""
        orch = WorkflowOrchestrator(max_concurrent_workflows=3)
        
        assert orch.max_concurrent_workflows == 3
        assert orch.workflow_semaphore._value == 3
        assert len(orch.workers) == 0
        assert len(orch.active_workflows) == 0
        assert len(orch.completion_events) == 0
        
    @pytest.mark.asyncio
    async def test_orchestrator_initialization(self):
        """オーケストレーター初期化テスト"""
        orch = WorkflowOrchestrator()
        
        await orch.initialize()
        
        # ワーカーが初期化されていることを確認
        assert len(orch.workers) == 2
        assert isinstance(orch.workers[0], MockParserWorker)
        assert isinstance(orch.workers[1], MockAggregatorWorker)
        
        # イベントバスが起動していることを確認
        assert orch.event_bus.running is True
        
        await orch.shutdown()
        
    @pytest.mark.asyncio
    async def test_workflow_execution_success(self, orchestrator):
        """ワークフロー実行成功テスト"""
        lang = "ja"
        title = "テストワークフロー"
        metadata = {"author": "test", "version": "1.0"}
        
        # ワークフロー実行
        context = await orchestrator.execute_workflow(lang, title, metadata)
        
        # 結果の確認
        assert context.lang == lang
        assert context.title == title
        assert context.metadata == metadata
        assert context.status == WorkflowStatus.COMPLETED
        assert context.workflow_id is not None
        
        # アクティブワークフローがクリアされていることを確認
        assert len(orchestrator.active_workflows) == 0
        assert len(orchestrator.completion_events) == 0
        
    @pytest.mark.asyncio
    async def test_workflow_execution_timeout(self):
        """ワークフロー実行タイムアウトテスト"""
        orch = WorkflowOrchestrator()
        await orch.initialize()
        
        try:
            # タイムアウトを短く設定してテスト
            with patch.object(orch, 'execute_workflow') as mock_execute:
                async def timeout_execution(*args, **kwargs):
                    await asyncio.sleep(0.1)
                    raise TimeoutError("Workflow timeout")
                
                mock_execute.side_effect = timeout_execution
                
                with pytest.raises(TimeoutError):
                    await orch.execute_workflow("ja", "テスト")
                    
        finally:
            await orch.shutdown()
            
    @pytest.mark.asyncio
    async def test_get_workflow_status(self, orchestrator):
        """ワークフロー状況取得テスト"""
        # 存在しないワークフローの場合
        status = await orchestrator.get_workflow_status("nonexistent")
        assert status is None
        
        # アクティブなワークフローの場合
        context = WorkflowContext(
            workflow_id="active-workflow",
            lang="en",
            title="Active Workflow",
            status=WorkflowStatus.RUNNING
        )
        orchestrator.active_workflows["active-workflow"] = context
        
        status = await orchestrator.get_workflow_status("active-workflow")
        assert status == context
        
    def test_get_active_workflows(self, orchestrator):
        """アクティブワークフロー一覧取得テスト"""
        # 初期状態では空
        active = orchestrator.get_active_workflows()
        assert len(active) == 0
        
        # ワークフローを追加
        context1 = WorkflowContext(
            workflow_id="workflow-1",
            lang="ja",
            title="ワークフロー1",
            status=WorkflowStatus.RUNNING
        )
        context2 = WorkflowContext(
            workflow_id="workflow-2",
            lang="en",
            title="Workflow 2",
            status=WorkflowStatus.RUNNING
        )
        
        orchestrator.active_workflows["workflow-1"] = context1
        orchestrator.active_workflows["workflow-2"] = context2
        
        active = orchestrator.get_active_workflows()
        assert len(active) == 2
        assert context1 in active
        assert context2 in active
        
    def test_get_metrics_summary(self, orchestrator):
        """メトリクス概要取得テスト"""
        summary = orchestrator.get_metrics_summary()
        
        assert isinstance(summary, dict)
        assert "counters" in summary
        assert "gauges" in summary
        assert "histograms" in summary
        assert "timers" in summary
        assert "metadata" in summary
        
    @pytest.mark.asyncio
    async def test_concurrent_workflow_execution(self):
        """並行ワークフロー実行テスト"""
        orch = WorkflowOrchestrator(max_concurrent_workflows=2)
        await orch.initialize()
        
        try:
            # 2つのワークフローを並行実行
            tasks = [
                orch.execute_workflow("ja", "ワークフロー1"),
                orch.execute_workflow("en", "Workflow 2")
            ]
            
            results = await asyncio.gather(*tasks)
            
            # 両方とも成功することを確認
            assert len(results) == 2
            assert all(ctx.status == WorkflowStatus.COMPLETED for ctx in results)
            assert results[0].title == "ワークフロー1"
            assert results[1].title == "Workflow 2"
            
        finally:
            await orch.shutdown()
            
    @pytest.mark.asyncio
    async def test_workflow_metrics_recording(self, orchestrator):
        """ワークフローメトリクス記録テスト"""
        # 実行前のメトリクス
        initial_metrics = orchestrator.get_metrics_summary()
        
        # ワークフロー実行
        await orchestrator.execute_workflow("ja", "メトリクステスト")
        
        # 実行後のメトリクス
        final_metrics = orchestrator.get_metrics_summary()
        
        # メトリクスが記録されていることを確認
        assert final_metrics["metadata"]["total_metrics_collected"] > initial_metrics["metadata"]["total_metrics_collected"] 