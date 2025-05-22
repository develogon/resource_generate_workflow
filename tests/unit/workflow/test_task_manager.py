import pytest
from unittest.mock import patch, MagicMock
import uuid

# テスト対象のモジュールをインポート
from app.workflow.task_manager import TaskManager, Task, TaskStatus, TaskType

class TestTaskManager:
    """タスク管理システムのテストクラス"""
    
    @pytest.fixture
    def task_manager(self):
        """テスト用のタスク管理システムインスタンスを作成"""
        return TaskManager()
    
    def test_register_task(self, task_manager, sample_task_data):
        """タスク登録のテスト"""
        task_id = task_manager.register_task(sample_task_data)
        
        # タスクIDが返されることを確認
        assert task_id is not None
        assert isinstance(task_id, str)
        
        # タスクが登録されていることを確認
        tasks = task_manager.get_all_tasks()
        assert len(tasks) == 1
        assert tasks[0].id == task_id
        assert tasks[0].status == TaskStatus.PENDING
    
    def test_get_next_executable_task(self, task_manager):
        """実行可能なタスクの取得テスト"""
        # タスクを複数登録
        task1 = {
            "type": TaskType.FILE_OPERATION, 
            "params": {"operation": "READ"},
            "dependencies": []
        }
        task2 = {
            "type": TaskType.API_CALL, 
            "params": {"api": "TEST"},
            "dependencies": []
        }
        task3 = {
            "type": TaskType.FILE_OPERATION,
            "params": {"operation": "WRITE"},
            "dependencies": ["task-002"]
        }
        
        task_id1 = task_manager.register_task(task1)
        task_id2 = task_manager.register_task(task2)
        task_id3 = task_manager.register_task(task3)
        
        # 次の実行可能タスクを取得
        task = task_manager.get_next_executable_task()
        
        # 実行可能なタスクが返されることを確認
        assert task is not None
        assert "id" in task
        assert "type" in task
        assert task["status"] == "PENDING"
        
        # 依存関係がないタスクが先に返されることを確認
        assert task["id"] in [task_id1, task_id2]
    
    def test_mark_task_completed(self, task_manager):
        """タスク完了処理のテスト"""
        # タスクを登録
        task_id = task_manager.register_task({
            "type": TaskType.FILE_OPERATION, 
            "params": {"operation": "READ"},
            "dependencies": []
        })
        
        # タスクを完了としてマーク
        result = {"success": True, "path": "/path/to/file.txt"}
        task_manager.mark_as_completed(task_id, result)
        
        # タスクが完了としてマークされていることを確認
        task = task_manager.get_task(task_id)
        assert task.status == TaskStatus.COMPLETED
        assert task.result == result
    
    def test_mark_task_failed(self, task_manager):
        """タスク失敗処理のテスト"""
        # タスクを登録
        task_id = task_manager.register_task({
            "type": TaskType.API_CALL, 
            "params": {"api": "TEST"},
            "dependencies": []
        })
        
        # タスクを失敗としてマーク
        error = Exception("API呼び出しエラー")
        task_manager.mark_as_failed(task_id, error)
        
        # タスクが失敗としてマークされていることを確認
        task = task_manager.get_task(task_id)
        assert task.status == TaskStatus.FAILED
        assert task.error == str(error)
    
    def test_task_retry(self, task_manager):
        """タスク再試行のテスト"""
        # タスクを登録（再試行回数を設定）
        task_id = task_manager.register_task({
            "type": TaskType.API_CALL, 
            "params": {"api": "TEST"},
            "dependencies": [],
            "max_retries": 3
        })
        
        # タスクを失敗としてマーク
        error = Exception("一時的なAPI障害")
        task_manager.mark_as_failed(task_id, error)
        
        # タスクの再試行
        result = task_manager.retry_task(task_id)
        
        # 再試行が成功することを確認
        assert result is True
        
        # タスクの状態を確認
        task = task_manager.get_task(task_id)
        assert task.status == TaskStatus.PENDING  # 再試行のため状態がPENDINGに戻る
        assert task.retry_count == 1  # 再試行回数が増加
    
    def test_task_dependencies(self, task_manager):
        """タスク依存関係の処理テスト"""
        # 依存関係のあるタスクを登録
        task_id1 = task_manager.register_task({
            "type": TaskType.FILE_OPERATION, 
            "params": {"operation": "READ"},
            "dependencies": []
        })
        task_id2 = task_manager.register_task({
            "type": TaskType.API_CALL, 
            "params": {"api": "TEST"},
            "dependencies": [task_id1]
        })
        
        # 最初の実行可能タスクを取得
        task = task_manager.get_next_executable_task()
        
        # 依存関係のないタスクが先に返されることを確認
        assert task is not None
        assert task["id"] == task_id1
        
        # 最初のタスクを完了としてマーク
        task_manager.mark_as_completed(task_id1, {"success": True})
        
        # 次の実行可能タスクを取得
        task = task_manager.get_next_executable_task()
        
        # 依存関係が解決されたタスクが返されることを確認
        assert task is not None
        assert task["id"] == task_id2 