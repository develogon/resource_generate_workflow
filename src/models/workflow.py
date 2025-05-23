"""ワークフロー関連のデータモデル."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class WorkflowStatus(Enum):
    """ワークフローの実行状態."""
    
    INITIALIZED = "initialized"
    RUNNING = "running"  
    COMPLETED = "completed"
    FAILED = "failed"
    SUSPENDED = "suspended"


@dataclass
class WorkflowContext:
    """ワークフロー実行コンテキスト."""
    
    workflow_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    lang: str = ""
    title: str = ""
    status: WorkflowStatus = WorkflowStatus.INITIALIZED
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    checkpoints: List[str] = field(default_factory=list)
    error_message: Optional[str] = None
    
    def update_status(self, status: WorkflowStatus, error_message: Optional[str] = None) -> None:
        """ステータスを更新."""
        self.status = status
        self.updated_at = time.time()
        if error_message:
            self.error_message = error_message
    
    def add_checkpoint(self, checkpoint: str) -> None:
        """チェックポイントを追加."""
        self.checkpoints.append(checkpoint)
        self.updated_at = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換."""
        return {
            "workflow_id": self.workflow_id,
            "lang": self.lang,
            "title": self.title,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
            "checkpoints": self.checkpoints,
            "error_message": self.error_message,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> WorkflowContext:
        """辞書からインスタンスを作成."""
        return cls(
            workflow_id=data["workflow_id"],
            lang=data["lang"],
            title=data["title"],
            status=WorkflowStatus(data["status"]),
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            metadata=data.get("metadata", {}),
            checkpoints=data.get("checkpoints", []),
            error_message=data.get("error_message"),
        ) 