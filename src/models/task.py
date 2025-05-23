"""タスク関連のデータモデル."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class TaskStatus(Enum):
    """タスクの実行状態."""
    
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskResult:
    """タスク実行結果."""
    
    success: bool
    data: Optional[Any] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換."""
        return {
            "success": self.success,
            "data": self.data,
            "error_message": self.error_message,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TaskResult:
        """辞書からインスタンスを作成."""
        return cls(
            success=data["success"],
            data=data.get("data"),
            error_message=data.get("error_message"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class Task:
    """タスククラス."""
    
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_type: str = ""
    workflow_id: str = ""
    status: TaskStatus = TaskStatus.PENDING
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    priority: int = 0
    retry_count: int = 0
    max_retries: int = 3
    input_data: Dict[str, Any] = field(default_factory=dict)
    result: Optional[TaskResult] = None
    
    def start(self) -> None:
        """タスクを開始状態にする."""
        self.status = TaskStatus.RUNNING
        self.started_at = time.time()
    
    def complete(self, result: TaskResult) -> None:
        """タスクを完了状態にする."""
        self.status = TaskStatus.COMPLETED
        self.completed_at = time.time()
        self.result = result
    
    def fail(self, error_message: str) -> None:
        """タスクを失敗状態にする."""
        self.status = TaskStatus.FAILED
        self.completed_at = time.time()
        self.result = TaskResult(
            success=False,
            error_message=error_message
        )
    
    def can_retry(self) -> bool:
        """リトライ可能かどうか."""
        return self.retry_count < self.max_retries
    
    def increment_retry(self) -> None:
        """リトライ回数をインクリメント."""
        self.retry_count += 1
        self.status = TaskStatus.PENDING
        self.started_at = None
        self.completed_at = None
        self.result = None
    
    @property
    def duration(self) -> Optional[float]:
        """実行時間を取得."""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換."""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "workflow_id": self.workflow_id,
            "status": self.status.value,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "priority": self.priority,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "input_data": self.input_data,
            "result": self.result.to_dict() if self.result else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Task:
        """辞書からインスタンスを作成."""
        result = None
        if data.get("result"):
            result = TaskResult.from_dict(data["result"])
            
        return cls(
            task_id=data["task_id"],
            task_type=data["task_type"],
            workflow_id=data["workflow_id"],
            status=TaskStatus(data["status"]),
            created_at=data["created_at"],
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            priority=data.get("priority", 0),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
            input_data=data.get("input_data", {}),
            result=result,
        ) 