"""ワークフロー実行エンジンのテスト."""

import time
from unittest.mock import Mock

import pytest

from src.config.constants import EventType, TaskType
from src.models.workflow import WorkflowStatus
from src.workflow.definition import (
    DependencyResolution,
    WorkflowDefinition,
    WorkflowStep,
    WorkflowStepType,
)
from src.workflow.engine import (
    ExecutionMode,
    StepExecution,
    StepExecutionStatus,
    WorkflowEngine,
    WorkflowExecution,
)


class TestStepExecution:
    """StepExecutionのテスト."""
    
    def test_initialization(self):
        """初期化のテスト."""
        step_execution = StepExecution(step_id="step1")
        
        assert step_execution.step_id == "step1"
        assert step_execution.status == StepExecutionStatus.PENDING
        assert step_execution.start_time is None
        assert step_execution.end_time is None
        assert step_execution.result is None
        assert step_execution.error is None
        assert step_execution.retry_count == 0
        assert not step_execution.is_finished
        assert step_execution.duration is None
    
    def test_lifecycle(self):
        """ライフサイクルのテスト."""
        step_execution = StepExecution(step_id="step1")
        
        # 開始
        step_execution.start()
        assert step_execution.status == StepExecutionStatus.RUNNING
        assert step_execution.start_time is not None
        assert not step_execution.is_finished
        
        # 完了
        result = {"output": "test result"}
        step_execution.complete(result)
        assert step_execution.status == StepExecutionStatus.COMPLETED
        assert step_execution.end_time is not None
        assert step_execution.result == result
        assert step_execution.is_finished
        assert step_execution.duration is not None
    
    def test_failure(self):
        """失敗のテスト."""
        step_execution = StepExecution(step_id="step1")
        
        step_execution.start()
        step_execution.fail("Test error")
        
        assert step_execution.status == StepExecutionStatus.FAILED
        assert step_execution.error == "Test error"
        assert step_execution.is_finished
    
    def test_skip(self):
        """スキップのテスト."""
        step_execution = StepExecution(step_id="step1")
        
        step_execution.skip("Conditions not met")
        
        assert step_execution.status == StepExecutionStatus.SKIPPED
        assert step_execution.metadata["skip_reason"] == "Conditions not met"
        assert step_execution.is_finished
    
    def test_cancel(self):
        """キャンセルのテスト."""
        step_execution = StepExecution(step_id="step1")
        
        step_execution.start()
        step_execution.cancel()
        
        assert step_execution.status == StepExecutionStatus.CANCELLED
        assert step_execution.is_finished


class TestWorkflowExecution:
    """WorkflowExecutionのテスト."""
    
    def test_initialization(self):
        """初期化のテスト."""
        execution = WorkflowExecution(
            id="exec1",
            workflow_id="workflow1"
        )
        
        assert execution.id == "exec1"
        assert execution.workflow_id == "workflow1"
        assert execution.status == WorkflowStatus.INITIALIZED
        assert execution.mode == ExecutionMode.SYNC
        assert len(execution.step_executions) == 0
        assert len(execution.completed_steps) == 0
        assert len(execution.failed_steps) == 0
    
    def test_auto_id_generation(self):
        """自動ID生成のテスト."""
        execution = WorkflowExecution(
            id="",
            workflow_id="workflow1"
        )
        
        assert execution.id != ""
        assert len(execution.id) == 36  # UUID形式
    
    def test_execution_summary(self):
        """実行概要のテスト."""
        execution = WorkflowExecution(
            id="exec1",
            workflow_id="workflow1"
        )
        
        # ステップ実行状態を追加
        execution.step_executions["step1"] = StepExecution(step_id="step1")
        execution.step_executions["step1"].complete({"result": "test"})
        
        execution.step_executions["step2"] = StepExecution(step_id="step2")
        execution.step_executions["step2"].fail("Test error")
        
        execution.step_executions["step3"] = StepExecution(step_id="step3")
        execution.step_executions["step3"].start()
        
        summary = execution.get_execution_summary()
        
        assert summary["id"] == "exec1"
        assert summary["workflow_id"] == "workflow1"
        assert summary["progress"]["total_steps"] == 3
        assert summary["progress"]["completed"] == 1
        assert summary["progress"]["failed"] == 1
        assert summary["progress"]["running"] == 1
        assert summary["progress"]["completion_rate"] == 1/3


class TestWorkflowEngine:
    """WorkflowEngineのテスト."""
    
    def test_initialization(self):
        """初期化のテスト."""
        engine = WorkflowEngine(max_concurrent_tasks=3)
        
        assert engine.max_concurrent_tasks == 3
        assert len(engine.active_executions) == 0
        assert len(engine.task_handlers) == 0
        assert len(engine.event_handlers) > 0  # EventTypeの数だけ初期化される
    
    def test_register_task_handler(self):
        """タスクハンドラー登録のテスト."""
        engine = WorkflowEngine()
        
        def test_handler(step, parameters):
            return {"output": f"handled {step.name}"}
        
        engine.register_task_handler("test_task", test_handler)
        
        assert "test_task" in engine.task_handlers
        assert engine.task_handlers["test_task"] == test_handler
    
    def test_register_event_handler(self):
        """イベントハンドラー登録のテスト."""
        engine = WorkflowEngine()
        
        events_received = []
        
        def event_handler(event_type, data):
            events_received.append((event_type, data))
        
        engine.register_event_handler(EventType.WORKFLOW_STARTED, event_handler)
        
        assert event_handler in engine.event_handlers[EventType.WORKFLOW_STARTED]
    
    def test_simple_workflow_execution(self):
        """シンプルなワークフロー実行のテスト."""
        engine = WorkflowEngine()
        
        # テストハンドラーを登録
        def test_handler(step, parameters):
            return {"step_name": step.name, "processed": True}
        
        engine.register_task_handler(TaskType.PARSE_CHAPTER.value, test_handler)
        
        # ワークフローを作成
        workflow = WorkflowDefinition(
            id="test-workflow",
            name="テストワークフロー",
            description="テスト用"
        )
        
        step = WorkflowStep(
            id="step1",
            name="テストステップ",
            type=WorkflowStepType.PARSE,
            task_type=TaskType.PARSE_CHAPTER
        )
        
        workflow.add_step(step)
        
        # 実行
        execution = engine.execute_workflow(workflow)
        
        assert execution.status == WorkflowStatus.COMPLETED
        assert len(execution.completed_steps) == 1
        assert "step1" in execution.completed_steps
        assert execution.step_executions["step1"].result["step_name"] == "テストステップ"
    
    def test_workflow_with_dependencies(self):
        """依存関係のあるワークフロー実行のテスト."""
        engine = WorkflowEngine()
        
        # テストハンドラーを登録
        handlers_called = []
        
        def parse_handler(step, parameters):
            handlers_called.append(f"parse:{step.name}")
            return {"parsed_data": "test data"}
        
        def generate_handler(step, parameters):
            handlers_called.append(f"generate:{step.name}")
            # 前のステップの結果を確認
            assert "step_step1_result" in parameters
            return {"generated_content": "test content"}
        
        engine.register_task_handler(TaskType.PARSE_CHAPTER.value, parse_handler)
        engine.register_task_handler(TaskType.GENERATE_ARTICLE.value, generate_handler)
        
        # ワークフローを作成
        workflow = WorkflowDefinition(
            id="test-workflow",
            name="依存関係テスト",
            description="依存関係のあるワークフロー"
        )
        
        step1 = WorkflowStep(
            id="step1",
            name="パースステップ",
            type=WorkflowStepType.PARSE,
            task_type=TaskType.PARSE_CHAPTER
        )
        
        step2 = WorkflowStep(
            id="step2",
            name="生成ステップ",
            type=WorkflowStepType.GENERATE,
            task_type=TaskType.GENERATE_ARTICLE,
            dependencies=["step1"]
        )
        
        workflow.add_step(step1)
        workflow.add_step(step2)
        
        # 実行
        execution = engine.execute_workflow(workflow)
        
        assert execution.status == WorkflowStatus.COMPLETED
        assert len(execution.completed_steps) == 2
        assert handlers_called == ["parse:パースステップ", "generate:生成ステップ"]
    
    def test_workflow_with_conditions(self):
        """条件付きワークフロー実行のテスト."""
        engine = WorkflowEngine()
        
        def test_handler(step, parameters):
            return {"step_name": step.name}
        
        engine.register_task_handler(TaskType.PARSE_CHAPTER.value, test_handler)
        
        # ワークフローを作成
        workflow = WorkflowDefinition(
            id="test-workflow",
            name="条件テスト",
            description="条件付きワークフロー"
        )
        
        step = WorkflowStep(
            id="step1",
            name="条件付きステップ",
            type=WorkflowStepType.PARSE,
            task_type=TaskType.PARSE_CHAPTER,
            conditions={"enable_processing": True}
        )
        
        workflow.add_step(step)
        
        # 条件を満たす場合
        context = {"enable_processing": True}
        execution = engine.execute_workflow(workflow, context)
        
        assert execution.status == WorkflowStatus.COMPLETED
        assert "step1" in execution.completed_steps
        
        # 条件を満たさない場合
        context = {"enable_processing": False}
        execution = engine.execute_workflow(workflow, context)
        
        assert execution.status == WorkflowStatus.COMPLETED
        assert execution.step_executions["step1"].status == StepExecutionStatus.SKIPPED
    
    def test_dry_run_mode(self):
        """ドライランモードのテスト."""
        engine = WorkflowEngine()
        
        # ワークフローを作成
        workflow = WorkflowDefinition(
            id="test-workflow",
            name="ドライランテスト",
            description="ドライラン用"
        )
        
        step = WorkflowStep(
            id="step1",
            name="ドライランステップ",
            type=WorkflowStepType.PARSE,
            task_type=TaskType.PARSE_CHAPTER
        )
        
        workflow.add_step(step)
        
        # ドライラン実行
        execution = engine.execute_workflow(workflow, mode=ExecutionMode.DRY_RUN)
        
        assert execution.status == WorkflowStatus.COMPLETED
        assert execution.step_executions["step1"].result["dry_run"] is True
    
    def test_step_failure_handling(self):
        """ステップ失敗処理のテスト."""
        engine = WorkflowEngine()
        
        def failing_handler(step, parameters):
            raise Exception("Test failure")
        
        engine.register_task_handler(TaskType.PARSE_CHAPTER.value, failing_handler)
        
        # ワークフローを作成
        workflow = WorkflowDefinition(
            id="test-workflow",
            name="失敗テスト",
            description="失敗処理テスト"
        )
        
        step = WorkflowStep(
            id="step1",
            name="失敗ステップ",
            type=WorkflowStepType.PARSE,
            task_type=TaskType.PARSE_CHAPTER,
            retry_policy={"max_attempts": 1}  # リトライなし
        )
        
        workflow.add_step(step)
        
        # 実行
        execution = engine.execute_workflow(workflow)
        
        assert execution.status == WorkflowStatus.FAILED
        assert "step1" in execution.failed_steps
        assert execution.step_executions["step1"].error == "Test failure"
    
    def test_missing_handler_error(self):
        """ハンドラー未登録エラーのテスト."""
        engine = WorkflowEngine()
        
        # ワークフローを作成（ハンドラー未登録）
        workflow = WorkflowDefinition(
            id="test-workflow",
            name="ハンドラー未登録テスト",
            description="ハンドラー未登録"
        )
        
        step = WorkflowStep(
            id="step1",
            name="未登録ステップ",
            type=WorkflowStepType.PARSE,
            task_type=TaskType.PARSE_CHAPTER
        )
        
        workflow.add_step(step)
        
        # 実行
        execution = engine.execute_workflow(workflow)
        
        assert execution.status == WorkflowStatus.FAILED
        assert "step1" in execution.failed_steps
        assert "No handler registered" in execution.step_executions["step1"].error
    
    def test_workflow_validation_error(self):
        """ワークフロー検証エラーのテスト."""
        engine = WorkflowEngine()
        
        # 無効なワークフローを作成（循環依存）
        workflow = WorkflowDefinition(
            id="invalid-workflow",
            name="無効なワークフロー",
            description="循環依存テスト"
        )
        
        step1 = WorkflowStep(
            id="step1",
            name="ステップ1",
            type=WorkflowStepType.PARSE,
            task_type=TaskType.PARSE_CHAPTER,
            dependencies=["step2"]
        )
        
        step2 = WorkflowStep(
            id="step2",
            name="ステップ2",
            type=WorkflowStepType.GENERATE,
            task_type=TaskType.GENERATE_ARTICLE,
            dependencies=["step1"]
        )
        
        workflow.add_step(step1)
        workflow.add_step(step2)
        
        # 実行時にエラーが発生
        with pytest.raises(RuntimeError, match="Deadlock detected"):
            engine.execute_workflow(workflow)
    
    def test_get_execution_status(self):
        """実行状態取得のテスト."""
        engine = WorkflowEngine()
        
        # 存在しない実行
        assert engine.get_execution_status("nonexistent") is None
        
        # アクティブな実行をモック
        execution = WorkflowExecution(
            id="test-exec",
            workflow_id="test-workflow"
        )
        engine.active_executions["test-exec"] = execution
        
        status = engine.get_execution_status("test-exec")
        assert status is not None
        assert status["id"] == "test-exec"
    
    def test_cancel_execution(self):
        """実行キャンセルのテスト."""
        engine = WorkflowEngine()
        
        # 存在しない実行のキャンセル
        assert not engine.cancel_execution("nonexistent")
        
        # アクティブな実行をモック
        execution = WorkflowExecution(
            id="test-exec",
            workflow_id="test-workflow",
            status=WorkflowStatus.RUNNING
        )
        
        step_execution = StepExecution(step_id="step1")
        step_execution.start()
        execution.step_executions["step1"] = step_execution
        
        engine.active_executions["test-exec"] = execution
        
        # キャンセル実行
        assert engine.cancel_execution("test-exec")
        assert execution.status == WorkflowStatus.SUSPENDED
        assert execution.step_executions["step1"].status == StepExecutionStatus.CANCELLED
    
    def test_get_active_executions(self):
        """アクティブ実行一覧取得のテスト."""
        engine = WorkflowEngine()
        
        # 空の場合
        assert engine.get_active_executions() == []
        
        # 実行を追加
        execution1 = WorkflowExecution(id="exec1", workflow_id="workflow1")
        execution2 = WorkflowExecution(id="exec2", workflow_id="workflow2")
        
        engine.active_executions["exec1"] = execution1
        engine.active_executions["exec2"] = execution2
        
        active_list = engine.get_active_executions()
        assert len(active_list) == 2
        assert any(ex["id"] == "exec1" for ex in active_list)
        assert any(ex["id"] == "exec2" for ex in active_list)
    
    def test_event_emission(self):
        """イベント発火のテスト."""
        engine = WorkflowEngine()
        
        events_received = []
        
        def event_handler(event_type, data):
            events_received.append((event_type.value, data))
        
        engine.register_event_handler(EventType.WORKFLOW_STARTED, event_handler)
        engine.register_event_handler(EventType.WORKFLOW_COMPLETED, event_handler)
        
        def test_handler(step, parameters):
            return {"result": "success"}
        
        engine.register_task_handler(TaskType.PARSE_CHAPTER.value, test_handler)
        
        # ワークフローを作成・実行
        workflow = WorkflowDefinition(
            id="test-workflow",
            name="イベントテスト",
            description="イベント発火テスト"
        )
        
        step = WorkflowStep(
            id="step1",
            name="テストステップ",
            type=WorkflowStepType.PARSE,
            task_type=TaskType.PARSE_CHAPTER
        )
        
        workflow.add_step(step)
        
        execution = engine.execute_workflow(workflow)
        
        # イベントが発火されたことを確認
        assert len(events_received) >= 2
        assert any(event[0] == "workflow.started" for event in events_received)
        assert any(event[0] == "workflow.completed" for event in events_received) 