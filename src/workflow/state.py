"""ワークフロー状態管理システム."""

from __future__ import annotations

import json
import pickle
import time
from abc import ABC, abstractmethod
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ..utils.logger import get_logger
from .engine import WorkflowExecution


class StateStore(ABC):
    """状態ストアの抽象基底クラス."""
    
    @abstractmethod
    async def save_execution(self, execution: WorkflowExecution) -> bool:
        """実行状態を保存."""
        pass
    
    @abstractmethod
    async def load_execution(self, execution_id: str) -> Optional[WorkflowExecution]:
        """実行状態を読み込み."""
        pass
    
    @abstractmethod
    async def delete_execution(self, execution_id: str) -> bool:
        """実行状態を削除."""
        pass
    
    @abstractmethod
    async def list_executions(
        self, 
        workflow_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """実行状態の一覧を取得."""
        pass
    
    @abstractmethod
    async def cleanup_old_executions(self, days_old: int = 30) -> int:
        """古い実行状態をクリーンアップ."""
        pass


class FileStateStore(StateStore):
    """ファイルベースの状態ストア."""
    
    def __init__(self, base_path: Union[str, Path]):
        """初期化."""
        self.base_path = Path(base_path)
        self.executions_path = self.base_path / "executions"
        self.logger = get_logger(__name__)
        
        # ディレクトリ作成
        self.executions_path.mkdir(parents=True, exist_ok=True)
    
    def _get_execution_file(self, execution_id: str) -> Path:
        """実行ファイルのパスを取得."""
        return self.executions_path / f"{execution_id}.json"
    
    async def save_execution(self, execution: WorkflowExecution) -> bool:
        """実行状態を保存."""
        try:
            file_path = self._get_execution_file(execution.id)
            
            # 実行状態を辞書に変換
            execution_data = {
                "id": execution.id,
                "workflow_id": execution.workflow_id,
                "status": execution.status.value,
                "start_time": execution.start_time,
                "end_time": execution.end_time,
                "context": execution.context,
                "mode": execution.mode.value,
                "metadata": execution.metadata,
                "step_executions": {},
                "saved_at": time.time()
            }
            
            # ステップ実行状態を変換
            for step_id, step_execution in execution.step_executions.items():
                execution_data["step_executions"][step_id] = {
                    "step_id": step_execution.step_id,
                    "task_id": step_execution.task_id,
                    "status": step_execution.status.value,
                    "start_time": step_execution.start_time,
                    "end_time": step_execution.end_time,
                    "result": step_execution.result,
                    "error": step_execution.error,
                    "retry_count": step_execution.retry_count,
                    "metadata": step_execution.metadata
                }
            
            # ファイルに保存
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(execution_data, f, indent=2, ensure_ascii=False)
            
            self.logger.debug(f"Saved execution state: {execution.id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save execution {execution.id}: {str(e)}")
            return False
    
    async def load_execution(self, execution_id: str) -> Optional[WorkflowExecution]:
        """実行状態を読み込み."""
        try:
            file_path = self._get_execution_file(execution_id)
            
            if not file_path.exists():
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                execution_data = json.load(f)
            
            # WorkflowExecutionを復元
            from .engine import WorkflowExecution, StepExecution, StepExecutionStatus, ExecutionMode
            from ..models.workflow import WorkflowStatus
            
            execution = WorkflowExecution(
                id=execution_data["id"],
                workflow_id=execution_data["workflow_id"],
                status=WorkflowStatus(execution_data["status"]),
                start_time=execution_data.get("start_time"),
                end_time=execution_data.get("end_time"),
                context=execution_data.get("context", {}),
                mode=ExecutionMode(execution_data.get("mode", "sync")),
                metadata=execution_data.get("metadata", {})
            )
            
            # ステップ実行状態を復元
            for step_id, step_data in execution_data.get("step_executions", {}).items():
                step_execution = StepExecution(
                    step_id=step_data["step_id"],
                    task_id=step_data.get("task_id"),
                    status=StepExecutionStatus(step_data["status"]),
                    start_time=step_data.get("start_time"),
                    end_time=step_data.get("end_time"),
                    result=step_data.get("result"),
                    error=step_data.get("error"),
                    retry_count=step_data.get("retry_count", 0),
                    metadata=step_data.get("metadata", {})
                )
                execution.step_executions[step_id] = step_execution
            
            self.logger.debug(f"Loaded execution state: {execution_id}")
            return execution
            
        except Exception as e:
            self.logger.error(f"Failed to load execution {execution_id}: {str(e)}")
            return None
    
    async def delete_execution(self, execution_id: str) -> bool:
        """実行状態を削除."""
        try:
            file_path = self._get_execution_file(execution_id)
            
            if file_path.exists():
                file_path.unlink()
                self.logger.debug(f"Deleted execution state: {execution_id}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to delete execution {execution_id}: {str(e)}")
            return False
    
    async def list_executions(
        self, 
        workflow_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """実行状態の一覧を取得."""
        try:
            executions = []
            
            for file_path in self.executions_path.glob("*.json"):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        execution_data = json.load(f)
                    
                    # フィルタリング
                    if workflow_id and execution_data.get("workflow_id") != workflow_id:
                        continue
                    
                    if status and execution_data.get("status") != status:
                        continue
                    
                    # 概要情報のみ追加
                    summary = {
                        "id": execution_data["id"],
                        "workflow_id": execution_data["workflow_id"],
                        "status": execution_data["status"],
                        "start_time": execution_data.get("start_time"),
                        "end_time": execution_data.get("end_time"),
                        "duration": (
                            execution_data.get("end_time", time.time()) - execution_data.get("start_time", 0)
                            if execution_data.get("start_time")
                            else None
                        ),
                        "step_count": len(execution_data.get("step_executions", {})),
                        "saved_at": execution_data.get("saved_at")
                    }
                    
                    executions.append(summary)
                    
                    if len(executions) >= limit:
                        break
                        
                except Exception as e:
                    self.logger.warning(f"Failed to read execution file {file_path}: {str(e)}")
                    continue
            
            # 開始時間でソート（新しい順）
            executions.sort(key=lambda x: x.get("start_time", 0), reverse=True)
            
            return executions
            
        except Exception as e:
            self.logger.error(f"Failed to list executions: {str(e)}")
            return []
    
    async def cleanup_old_executions(self, days_old: int = 30) -> int:
        """古い実行状態をクリーンアップ."""
        try:
            cutoff_time = time.time() - (days_old * 24 * 60 * 60)
            deleted_count = 0
            
            for file_path in self.executions_path.glob("*.json"):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        execution_data = json.load(f)
                    
                    saved_at = execution_data.get("saved_at", 0)
                    if saved_at < cutoff_time:
                        file_path.unlink()
                        deleted_count += 1
                        
                except Exception as e:
                    self.logger.warning(f"Failed to process file {file_path} during cleanup: {str(e)}")
                    continue
            
            self.logger.info(f"Cleaned up {deleted_count} old execution states")
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old executions: {str(e)}")
            return 0


class MemoryStateStore(StateStore):
    """メモリベースの状態ストア（開発・テスト用）."""
    
    def __init__(self):
        """初期化."""
        self.executions: Dict[str, WorkflowExecution] = {}
        self.logger = get_logger(__name__)
    
    async def save_execution(self, execution: WorkflowExecution) -> bool:
        """実行状態を保存."""
        try:
            # ディープコピーで保存
            import copy
            self.executions[execution.id] = copy.deepcopy(execution)
            
            self.logger.debug(f"Saved execution state to memory: {execution.id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save execution {execution.id} to memory: {str(e)}")
            return False
    
    async def load_execution(self, execution_id: str) -> Optional[WorkflowExecution]:
        """実行状態を読み込み."""
        try:
            execution = self.executions.get(execution_id)
            if execution:
                # ディープコピーで返す
                import copy
                self.logger.debug(f"Loaded execution state from memory: {execution_id}")
                return copy.deepcopy(execution)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to load execution {execution_id} from memory: {str(e)}")
            return None
    
    async def delete_execution(self, execution_id: str) -> bool:
        """実行状態を削除."""
        try:
            if execution_id in self.executions:
                del self.executions[execution_id]
                self.logger.debug(f"Deleted execution state from memory: {execution_id}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to delete execution {execution_id} from memory: {str(e)}")
            return False
    
    async def list_executions(
        self, 
        workflow_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """実行状態の一覧を取得."""
        try:
            executions = []
            
            for execution in self.executions.values():
                # フィルタリング
                if workflow_id and execution.workflow_id != workflow_id:
                    continue
                
                if status and execution.status.value != status:
                    continue
                
                # 概要情報を作成
                summary = execution.get_execution_summary()
                executions.append(summary)
                
                if len(executions) >= limit:
                    break
            
            # 開始時間でソート（新しい順）
            executions.sort(key=lambda x: x.get("start_time", 0), reverse=True)
            
            return executions
            
        except Exception as e:
            self.logger.error(f"Failed to list executions from memory: {str(e)}")
            return []
    
    async def cleanup_old_executions(self, days_old: int = 30) -> int:
        """古い実行状態をクリーンアップ."""
        try:
            cutoff_time = time.time() - (days_old * 24 * 60 * 60)
            deleted_count = 0
            
            execution_ids_to_delete = []
            
            for execution_id, execution in self.executions.items():
                if execution.start_time and execution.start_time < cutoff_time:
                    execution_ids_to_delete.append(execution_id)
            
            for execution_id in execution_ids_to_delete:
                del self.executions[execution_id]
                deleted_count += 1
            
            self.logger.info(f"Cleaned up {deleted_count} old execution states from memory")
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old executions from memory: {str(e)}")
            return 0


class StateManager:
    """状態管理マネージャー."""
    
    def __init__(self, store: StateStore):
        """初期化."""
        self.store = store
        self.logger = get_logger(__name__)
    
    async def save_execution_state(self, execution: WorkflowExecution) -> bool:
        """実行状態を保存."""
        return await self.store.save_execution(execution)
    
    async def restore_execution_state(self, execution_id: str) -> Optional[WorkflowExecution]:
        """実行状態を復元."""
        return await self.store.load_execution(execution_id)
    
    async def delete_execution_state(self, execution_id: str) -> bool:
        """実行状態を削除."""
        return await self.store.delete_execution(execution_id)
    
    async def get_execution_history(
        self, 
        workflow_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """実行履歴を取得."""
        return await self.store.list_executions(workflow_id, status, limit)
    
    async def cleanup_old_states(self, days_old: int = 30) -> int:
        """古い状態をクリーンアップ."""
        return await self.store.cleanup_old_executions(days_old)
    
    async def get_execution_statistics(self) -> Dict[str, Any]:
        """実行統計を取得."""
        try:
            all_executions = await self.store.list_executions(limit=1000)
            
            if not all_executions:
                return {
                    "total_executions": 0,
                    "status_distribution": {},
                    "average_duration": 0,
                    "success_rate": 0
                }
            
            # 統計計算
            total_executions = len(all_executions)
            status_counts = {}
            durations = []
            
            for execution in all_executions:
                status = execution.get("status", "unknown")
                status_counts[status] = status_counts.get(status, 0) + 1
                
                if execution.get("duration"):
                    durations.append(execution["duration"])
            
            # 成功率計算
            completed = status_counts.get("completed", 0)
            success_rate = completed / total_executions if total_executions > 0 else 0
            
            # 平均実行時間
            avg_duration = sum(durations) / len(durations) if durations else 0
            
            return {
                "total_executions": total_executions,
                "status_distribution": status_counts,
                "average_duration": avg_duration,
                "success_rate": success_rate,
                "total_duration": sum(durations)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get execution statistics: {str(e)}")
            return {
                "total_executions": 0,
                "status_distribution": {},
                "average_duration": 0,
                "success_rate": 0,
                "error": str(e)
            } 