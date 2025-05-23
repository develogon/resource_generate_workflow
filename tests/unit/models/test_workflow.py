"""ワークフローモデルのテスト."""

import time
import uuid
from unittest.mock import patch

import pytest

from src.models.workflow import WorkflowContext, WorkflowStatus


class TestWorkflowStatus:
    """WorkflowStatusのテスト."""
    
    def test_enum_values(self):
        """Enumの値が正しいことを確認."""
        assert WorkflowStatus.INITIALIZED.value == "initialized"
        assert WorkflowStatus.RUNNING.value == "running"
        assert WorkflowStatus.COMPLETED.value == "completed"
        assert WorkflowStatus.FAILED.value == "failed"
        assert WorkflowStatus.SUSPENDED.value == "suspended"


class TestWorkflowContext:
    """WorkflowContextのテスト."""
    
    def test_default_initialization(self):
        """デフォルト値での初期化テスト."""
        context = WorkflowContext()
        
        # UUIDが生成されていることを確認
        assert isinstance(context.workflow_id, str)
        assert len(context.workflow_id) == 36  # UUID形式
        
        # デフォルト値の確認
        assert context.lang == ""
        assert context.title == ""
        assert context.status == WorkflowStatus.INITIALIZED
        assert isinstance(context.created_at, float)
        assert isinstance(context.updated_at, float)
        assert context.metadata == {}
        assert context.checkpoints == []
        assert context.error_message is None
    
    def test_custom_initialization(self):
        """カスタム値での初期化テスト."""
        workflow_id = str(uuid.uuid4())
        context = WorkflowContext(
            workflow_id=workflow_id,
            lang="ja",
            title="テストタイトル",
            status=WorkflowStatus.RUNNING
        )
        
        assert context.workflow_id == workflow_id
        assert context.lang == "ja"
        assert context.title == "テストタイトル"
        assert context.status == WorkflowStatus.RUNNING
    
    def test_update_status(self):
        """ステータス更新のテスト."""
        context = WorkflowContext()
        original_updated_at = context.updated_at
        
        # 少し待ってから更新
        time.sleep(0.01)
        context.update_status(WorkflowStatus.RUNNING)
        
        assert context.status == WorkflowStatus.RUNNING
        assert context.updated_at > original_updated_at
        assert context.error_message is None
    
    def test_update_status_with_error(self):
        """エラーメッセージ付きステータス更新のテスト."""
        context = WorkflowContext()
        error_msg = "テストエラー"
        
        context.update_status(WorkflowStatus.FAILED, error_msg)
        
        assert context.status == WorkflowStatus.FAILED
        assert context.error_message == error_msg
    
    def test_add_checkpoint(self):
        """チェックポイント追加のテスト."""
        context = WorkflowContext()
        original_updated_at = context.updated_at
        
        time.sleep(0.01)
        context.add_checkpoint("test_checkpoint")
        
        assert "test_checkpoint" in context.checkpoints
        assert len(context.checkpoints) == 1
        assert context.updated_at > original_updated_at
    
    def test_to_dict(self):
        """辞書変換のテスト."""
        context = WorkflowContext(
            lang="ja",
            title="テスト",
            status=WorkflowStatus.RUNNING
        )
        context.add_checkpoint("checkpoint1")
        context.update_status(WorkflowStatus.FAILED, "エラー")
        
        data = context.to_dict()
        
        assert data["workflow_id"] == context.workflow_id
        assert data["lang"] == "ja"
        assert data["title"] == "テスト"
        assert data["status"] == "failed"
        assert isinstance(data["created_at"], float)
        assert isinstance(data["updated_at"], float)
        assert data["metadata"] == {}
        assert data["checkpoints"] == ["checkpoint1"]
        assert data["error_message"] == "エラー"
    
    def test_from_dict(self):
        """辞書からの復元のテスト."""
        original_context = WorkflowContext(
            lang="ja",
            title="テスト",
            status=WorkflowStatus.COMPLETED
        )
        original_context.add_checkpoint("checkpoint1")
        original_context.metadata["key"] = "value"
        
        data = original_context.to_dict()
        restored_context = WorkflowContext.from_dict(data)
        
        assert restored_context.workflow_id == original_context.workflow_id
        assert restored_context.lang == original_context.lang
        assert restored_context.title == original_context.title
        assert restored_context.status == original_context.status
        assert restored_context.created_at == original_context.created_at
        assert restored_context.updated_at == original_context.updated_at
        assert restored_context.metadata == original_context.metadata
        assert restored_context.checkpoints == original_context.checkpoints
        assert restored_context.error_message == original_context.error_message
    
    def test_from_dict_minimal(self):
        """最小限のデータからの復元テスト."""
        minimal_data = {
            "workflow_id": str(uuid.uuid4()),
            "lang": "en",
            "title": "Test",
            "status": "initialized",
            "created_at": time.time(),
            "updated_at": time.time(),
        }
        
        context = WorkflowContext.from_dict(minimal_data)
        
        assert context.workflow_id == minimal_data["workflow_id"]
        assert context.lang == "en"
        assert context.title == "Test"
        assert context.status == WorkflowStatus.INITIALIZED
        assert context.metadata == {}
        assert context.checkpoints == []
        assert context.error_message is None 