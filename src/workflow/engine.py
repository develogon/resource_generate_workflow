"""ワークフロー実行エンジン."""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

from ..config.constants import EventType
from ..models.task import Task, TaskStatus
from ..models.workflow import WorkflowContext, WorkflowStatus
from ..utils.logger import get_logger, PerformanceLogger
from .definition import WorkflowDefinition, WorkflowStep


class ExecutionMode(Enum):
    """実行モード."""
    
    SYNC = "sync"  # 同期実行
    ASYNC = "async"  # 非同期実行
    DRY_RUN = "dry_run"  # ドライラン


class StepExecutionStatus(Enum):
    """ステップ実行ステータス."""
    
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


@dataclass
class StepExecution:
    """ステップ実行状態."""
    
    step_id: str
    task_id: Optional[str] = None
    status: StepExecutionStatus = StepExecutionStatus.PENDING
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration(self) -> Optional[float]:
        """実行時間."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None
    
    @property
    def is_finished(self) -> bool:
        """完了状態かどうか."""
        return self.status in {
            StepExecutionStatus.COMPLETED,
            StepExecutionStatus.FAILED,
            StepExecutionStatus.SKIPPED,
            StepExecutionStatus.CANCELLED
        }
    
    def start(self) -> None:
        """実行開始."""
        self.status = StepExecutionStatus.RUNNING
        self.start_time = time.time()
    
    def complete(self, result: Dict[str, Any]) -> None:
        """実行完了."""
        self.status = StepExecutionStatus.COMPLETED
        self.end_time = time.time()
        self.result = result
    
    def fail(self, error: str) -> None:
        """実行失敗."""
        self.status = StepExecutionStatus.FAILED
        self.end_time = time.time()
        self.error = error
    
    def skip(self, reason: str) -> None:
        """実行スキップ."""
        self.status = StepExecutionStatus.SKIPPED
        self.end_time = time.time()
        self.metadata["skip_reason"] = reason
    
    def cancel(self) -> None:
        """実行キャンセル."""
        self.status = StepExecutionStatus.CANCELLED
        self.end_time = time.time()


@dataclass
class WorkflowExecution:
    """ワークフロー実行状態."""
    
    id: str
    workflow_id: str
    status: WorkflowStatus = WorkflowStatus.INITIALIZED
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    step_executions: Dict[str, StepExecution] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    mode: ExecutionMode = ExecutionMode.SYNC
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """初期化後の処理."""
        if not self.id:
            self.id = str(uuid.uuid4())
    
    @property
    def duration(self) -> Optional[float]:
        """実行時間."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None
    
    @property
    def completed_steps(self) -> Set[str]:
        """完了済みステップID."""
        return {
            step_id for step_id, execution in self.step_executions.items()
            if execution.status == StepExecutionStatus.COMPLETED
        }
    
    @property
    def failed_steps(self) -> Set[str]:
        """失敗ステップID."""
        return {
            step_id for step_id, execution in self.step_executions.items()
            if execution.status == StepExecutionStatus.FAILED
        }
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """実行概要を取得."""
        total_steps = len(self.step_executions)
        completed = len(self.completed_steps)
        failed = len(self.failed_steps)
        running = len([
            ex for ex in self.step_executions.values()
            if ex.status == StepExecutionStatus.RUNNING
        ])
        
        return {
            "id": self.id,
            "workflow_id": self.workflow_id,
            "status": self.status.value,
            "duration": self.duration,
            "progress": {
                "total_steps": total_steps,
                "completed": completed,
                "failed": failed,
                "running": running,
                "completion_rate": completed / total_steps if total_steps > 0 else 0
            },
            "mode": self.mode.value
        }


class WorkflowEngine:
    """ワークフロー実行エンジン."""
    
    def __init__(self, max_concurrent_tasks: int = 5):
        """初期化."""
        self.logger = get_logger(__name__)
        self.max_concurrent_tasks = max_concurrent_tasks
        self.active_executions: Dict[str, WorkflowExecution] = {}
        self.task_handlers: Dict[str, callable] = {}
        
        # イベントハンドラー
        self.event_handlers: Dict[EventType, List[callable]] = {
            event_type: [] for event_type in EventType
        }
    
    def register_task_handler(self, task_type: str, handler: callable) -> None:
        """タスクハンドラーを登録."""
        self.task_handlers[task_type] = handler
        self.logger.info(f"Registered task handler for type: {task_type}")
    
    def register_event_handler(self, event_type: EventType, handler: callable) -> None:
        """イベントハンドラーを登録."""
        self.event_handlers[event_type].append(handler)
        self.logger.info(f"Registered event handler for: {event_type.value}")
    
    def execute_workflow(
        self, 
        workflow: WorkflowDefinition, 
        context: Optional[Dict[str, Any]] = None,
        mode: ExecutionMode = ExecutionMode.SYNC
    ) -> WorkflowExecution:
        """ワークフローを実行."""
        execution = WorkflowExecution(
            id=str(uuid.uuid4()),
            workflow_id=workflow.id,
            context=context or {},
            mode=mode
        )
        
        self.active_executions[execution.id] = execution
        
        try:
            if mode == ExecutionMode.ASYNC:
                return self._execute_async(workflow, execution)
            else:
                return self._execute_sync(workflow, execution)
        except Exception as e:
            self.logger.error(f"Workflow execution failed: {str(e)}")
            execution.status = WorkflowStatus.FAILED
            execution.end_time = time.time()
            self._emit_event(EventType.WORKFLOW_FAILED, execution.get_execution_summary())
            raise
        finally:
            if execution.id in self.active_executions:
                del self.active_executions[execution.id]
    
    def _execute_sync(self, workflow: WorkflowDefinition, execution: WorkflowExecution) -> WorkflowExecution:
        """同期実行."""
        with PerformanceLogger(self.logger, f"workflow execution: {workflow.name}"):
            self.logger.info(f"Starting sync execution of workflow: {workflow.name}")
            
            execution.status = WorkflowStatus.RUNNING
            execution.start_time = time.time()
            
            # ワークフロー開始イベント
            self._emit_event(EventType.WORKFLOW_STARTED, execution.get_execution_summary())
            
            # 依存関係の検証
            validation_result = workflow.validate_dependencies()
            if not validation_result["valid"]:
                raise ValueError(f"Workflow validation failed: {validation_result['errors']}")
            
            # 実行順序の取得
            try:
                execution_order = workflow.get_execution_order()
            except RuntimeError as e:
                execution.status = WorkflowStatus.FAILED
                execution.end_time = time.time()
                raise e
            
            # ステップ実行状態の初期化
            for step in workflow.steps:
                execution.step_executions[step.id] = StepExecution(step_id=step.id)
            
            # バッチごとの実行
            for batch in execution_order:
                self._execute_batch_sync(workflow, execution, batch)
                
                # 失敗したステップがある場合は中止
                failed_in_batch = [
                    step_id for step_id in batch
                    if execution.step_executions[step_id].status == StepExecutionStatus.FAILED
                ]
                
                if failed_in_batch:
                    self.logger.error(f"Batch execution failed, stopping workflow. Failed steps: {failed_in_batch}")
                    execution.status = WorkflowStatus.FAILED
                    execution.end_time = time.time()
                    self._emit_event(EventType.WORKFLOW_FAILED, execution.get_execution_summary())
                    return execution
            
            # 全ステップ完了
            execution.status = WorkflowStatus.COMPLETED
            execution.end_time = time.time()
            
            self.logger.info(f"Workflow execution completed: {workflow.name}")
            self._emit_event(EventType.WORKFLOW_COMPLETED, execution.get_execution_summary())
            
            return execution
    
    def _execute_batch_sync(
        self, 
        workflow: WorkflowDefinition, 
        execution: WorkflowExecution, 
        batch: List[str]
    ) -> None:
        """バッチ同期実行."""
        self.logger.info(f"Executing batch: {batch}")
        
        for step_id in batch:
            step = workflow.get_step(step_id)
            if not step:
                continue
            
            step_execution = execution.step_executions[step_id]
            
            # 条件評価
            if not step.evaluate_conditions(execution.context):
                step_execution.skip("Conditions not met")
                self.logger.info(f"Step {step_id} skipped: conditions not met")
                continue
            
            # ステップ実行
            self._execute_step(step, step_execution, execution.context, execution.mode)
    
    def _execute_step(
        self, 
        step: WorkflowStep, 
        step_execution: StepExecution, 
        context: Dict[str, Any],
        mode: ExecutionMode
    ) -> None:
        """ステップ実行."""
        self.logger.info(f"Executing step: {step.name} ({step.id})")
        
        step_execution.start()
        
        # ステップ開始イベント
        self._emit_event(EventType.TASK_STARTED, {
            "step_id": step.id,
            "step_name": step.name,
            "task_type": step.task_type.value
        })
        
        try:
            if mode == ExecutionMode.DRY_RUN:
                # ドライランの場合は実際の処理をスキップ
                result = {"dry_run": True, "step": step.name}
                step_execution.complete(result)
                self.logger.info(f"Step {step.id} dry run completed")
                return
            
            # タスクハンドラーの実行
            handler = self.task_handlers.get(step.task_type.value)
            if not handler:
                raise ValueError(f"No handler registered for task type: {step.task_type.value}")
            
            # パラメータの準備
            parameters = dict(step.parameters)
            parameters.update(context)
            
            # ハンドラー実行
            result = handler(step, parameters)
            
            # 結果をコンテキストに追加
            context[f"step_{step.id}_result"] = result
            
            step_execution.complete(result)
            
            self.logger.info(f"Step {step.id} completed successfully")
            self._emit_event(EventType.TASK_COMPLETED, {
                "step_id": step.id,
                "result": result
            })
            
        except Exception as e:
            error_msg = str(e)
            step_execution.fail(error_msg)
            
            self.logger.error(f"Step {step.id} failed: {error_msg}")
            self._emit_event(EventType.TASK_FAILED, {
                "step_id": step.id,
                "error": error_msg
            })
            
            # リトライロジック
            if step_execution.retry_count < step.retry_policy.get("max_attempts", 1) - 1:
                step_execution.retry_count += 1
                delay = step.retry_policy.get("initial_delay", 1) * (
                    step.retry_policy.get("backoff_multiplier", 2) ** step_execution.retry_count
                )
                
                self.logger.info(f"Retrying step {step.id} in {delay} seconds (attempt {step_execution.retry_count + 1})")
                time.sleep(delay)
                
                # リトライ実行
                step_execution.status = StepExecutionStatus.PENDING
                self._execute_step(step, step_execution, context, mode)
    
    async def _execute_async(self, workflow: WorkflowDefinition, execution: WorkflowExecution) -> WorkflowExecution:
        """非同期実行."""
        self.logger.info(f"Starting async execution of workflow: {workflow.name}")
        
        execution.status = WorkflowStatus.RUNNING
        execution.start_time = time.time()
        
        self._emit_event(EventType.WORKFLOW_STARTED, execution.get_execution_summary())
        
        # 非同期実行の実装（簡略版）
        try:
            # 同期版を非同期で実行
            await asyncio.get_event_loop().run_in_executor(
                None, self._execute_sync, workflow, execution
            )
        except Exception as e:
            execution.status = WorkflowStatus.FAILED
            execution.end_time = time.time()
            raise
        
        return execution
    
    def _emit_event(self, event_type: EventType, data: Dict[str, Any]) -> None:
        """イベントを発火."""
        handlers = self.event_handlers.get(event_type, [])
        
        for handler in handlers:
            try:
                handler(event_type, data)
            except Exception as e:
                self.logger.error(f"Event handler failed for {event_type.value}: {str(e)}")
    
    def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """実行状態を取得."""
        execution = self.active_executions.get(execution_id)
        if execution:
            return execution.get_execution_summary()
        return None
    
    def cancel_execution(self, execution_id: str) -> bool:
        """実行をキャンセル."""
        execution = self.active_executions.get(execution_id)
        if execution and execution.status == WorkflowStatus.RUNNING:
            execution.status = WorkflowStatus.SUSPENDED
            execution.end_time = time.time()
            
            # 実行中のステップをキャンセル
            for step_execution in execution.step_executions.values():
                if step_execution.status == StepExecutionStatus.RUNNING:
                    step_execution.cancel()
            
            self.logger.info(f"Workflow execution cancelled: {execution_id}")
            self._emit_event(EventType.WORKFLOW_SUSPENDED, execution.get_execution_summary())
            
            return True
        
        return False
    
    def get_active_executions(self) -> List[Dict[str, Any]]:
        """アクティブな実行の一覧を取得."""
        return [execution.get_execution_summary() for execution in self.active_executions.values()] 