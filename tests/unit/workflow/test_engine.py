import pytest
import os
from unittest.mock import patch, MagicMock

# テスト対象のモジュールをインポート
from app.workflow.engine import WorkflowEngine
from app.workflow.task_manager import TaskManager, TaskType

class TestWorkflowEngine:
    """ワークフローエンジンのテストクラス"""
    
    @pytest.fixture
    def workflow_engine(self, tmp_path):
        """テスト用のワークフローエンジンインスタンスを作成"""
        config = {
            "checkpoint_dir": str(tmp_path / "checkpoints"),
        }
        engine = WorkflowEngine(config)
        return engine
    
    def test_workflow_initialization(self, workflow_engine):
        """ワークフローエンジンの初期化をテスト"""
        # ワークフローエンジンが正しく初期化されていることを確認
        assert workflow_engine is not None
        assert workflow_engine.task_manager is not None
        assert workflow_engine.checkpoint_manager is not None
        
        # 設定が反映されていることを確認
        assert "checkpoint_dir" in workflow_engine.config
    
    @patch('os.path.exists')
    def test_start_workflow(self, mock_exists, workflow_engine, tmp_path):
        """ワークフローの開始処理をテスト"""
        # モックの設定
        mock_exists.return_value = True
        
        # タスク管理システムのモック
        mock_task_manager = MagicMock()
        workflow_engine.task_manager = mock_task_manager
        
        # チェックポイント管理システムのモック
        mock_checkpoint_manager = MagicMock()
        workflow_engine.checkpoint_manager = mock_checkpoint_manager
        
        # execute_task_loopをモックに置き換え
        workflow_engine.execute_task_loop = MagicMock(return_value=True)
        
        # ワークフローを開始
        input_path = str(tmp_path / "input.md")
        result = workflow_engine.start(input_path)
        
        # 結果の確認
        assert result is True
        mock_task_manager.register_task.assert_called()
        mock_checkpoint_manager.save_checkpoint.assert_called_with("INITIAL", {
            "input_path": input_path,
            "stage": "INITIALIZED"
        })
        workflow_engine.execute_task_loop.assert_called_once()
    
    @patch('app.workflow.checkpoint.CheckpointManager.load_checkpoint')
    @patch('app.workflow.checkpoint.CheckpointManager.restore_from_checkpoint')
    def test_resume_workflow(self, mock_restore, mock_load, workflow_engine):
        """ワークフローの再開処理をテスト"""
        # モックの設定
        mock_load.return_value = {
            "id": "checkpoint-001",
            "state": {"current_task": "task-003"}
        }
        mock_restore.return_value = True
        
        # execute_task_loopをモックに置き換え
        workflow_engine.execute_task_loop = MagicMock(return_value=True)
        
        # ワークフローを再開
        result = workflow_engine.resume("checkpoint-001")
        
        # 結果の確認
        assert result is True
        mock_load.assert_called_once_with("checkpoint-001")
        mock_restore.assert_called_once()
        workflow_engine.execute_task_loop.assert_called_once()
    
    @patch('app.workflow.task_manager.TaskManager.get_next_executable_task')
    @patch('app.workflow.task_manager.TaskManager.mark_as_completed')
    def test_execute_task_loop(self, mock_mark_completed, mock_get_task, workflow_engine):
        """タスク実行ループをテスト"""
        # モックの設定
        mock_get_task.side_effect = [
            {"id": "task-001", "type": "FILE_OPERATION", "params": {"operation": "READ"}},
            {"id": "task-002", "type": "API_CALL", "params": {"api": "TEST"}},
            None  # タスクがなくなったらNoneを返す
        ]
        
        # チェックポイント管理システムのモック
        mock_checkpoint_manager = MagicMock()
        workflow_engine.checkpoint_manager = mock_checkpoint_manager
        
        # タスク実行メソッドをモックに置き換え
        workflow_engine._execute_task = MagicMock(return_value={"success": True})
        
        # タスク実行ループを実行
        result = workflow_engine.execute_task_loop()
        
        # 結果の確認
        assert result is True
        assert mock_get_task.call_count == 3
        assert mock_mark_completed.call_count == 2
        assert workflow_engine._execute_task.call_count == 2
        assert mock_checkpoint_manager.save_checkpoint.call_count == 2
    
    def test_handle_error(self, workflow_engine):
        """エラー処理をテスト"""
        # チェックポイント管理システムのモック
        mock_checkpoint_manager = MagicMock()
        workflow_engine.checkpoint_manager = mock_checkpoint_manager
        
        # エラーハンドリングを実行
        error = Exception("テストエラー")
        context = {"task_id": "task-003"}
        result = workflow_engine.handle_error(error, context)
        
        # 結果の確認
        assert result is False
        mock_checkpoint_manager.save_checkpoint.assert_called_with("ERROR", {
            "error": str(error),
            "context": context
        }) 