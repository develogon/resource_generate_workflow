"""タスクモデルのテスト."""

import time
import uuid

import pytest

from src.models.task import Task, TaskResult, TaskStatus


class TestTaskStatus:
    """TaskStatusのテスト."""
    
    def test_enum_values(self):
        """Enumの値が正しいことを確認."""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.CANCELLED.value == "cancelled"


class TestTaskResult:
    """TaskResultのテスト."""
    
    def test_success_result(self):
        """成功結果のテスト."""
        data = {"output": "test_output"}
        metadata = {"duration": 1.5}
        
        result = TaskResult(
            success=True,
            data=data,
            metadata=metadata
        )
        
        assert result.success is True
        assert result.data == data
        assert result.error_message is None
        assert result.metadata == metadata
    
    def test_failure_result(self):
        """失敗結果のテスト."""
        result = TaskResult(
            success=False,
            error_message="テストエラー"
        )
        
        assert result.success is False
        assert result.data is None
        assert result.error_message == "テストエラー"
        assert result.metadata == {}
    
    def test_to_dict(self):
        """辞書変換のテスト."""
        result = TaskResult(
            success=True,
            data={"key": "value"},
            error_message=None,
            metadata={"duration": 2.0}
        )
        
        data = result.to_dict()
        
        expected = {
            "success": True,
            "data": {"key": "value"},
            "error_message": None,
            "metadata": {"duration": 2.0}
        }
        assert data == expected
    
    def test_from_dict(self):
        """辞書からの復元のテスト."""
        data = {
            "success": False,
            "data": None,
            "error_message": "エラー",
            "metadata": {"retry_count": 1}
        }
        
        result = TaskResult.from_dict(data)
        
        assert result.success is False
        assert result.data is None
        assert result.error_message == "エラー"
        assert result.metadata == {"retry_count": 1}


class TestTask:
    """Taskのテスト."""
    
    def test_default_initialization(self):
        """デフォルト値での初期化テスト."""
        task = Task()
        
        # UUIDが生成されていることを確認
        assert isinstance(task.task_id, str)
        assert len(task.task_id) == 36  # UUID形式
        
        # デフォルト値の確認
        assert task.task_type == ""
        assert task.workflow_id == ""
        assert task.status == TaskStatus.PENDING
        assert isinstance(task.created_at, float)
        assert task.started_at is None
        assert task.completed_at is None
        assert task.priority == 0
        assert task.retry_count == 0
        assert task.max_retries == 3
        assert task.input_data == {}
        assert task.result is None
    
    def test_custom_initialization(self):
        """カスタム値での初期化テスト."""
        task_id = str(uuid.uuid4())
        workflow_id = str(uuid.uuid4())
        input_data = {"input": "test"}
        
        task = Task(
            task_id=task_id,
            task_type="test_task",
            workflow_id=workflow_id,
            priority=5,
            max_retries=5,
            input_data=input_data
        )
        
        assert task.task_id == task_id
        assert task.task_type == "test_task"
        assert task.workflow_id == workflow_id
        assert task.priority == 5
        assert task.max_retries == 5
        assert task.input_data == input_data
    
    def test_start(self):
        """タスク開始のテスト."""
        task = Task()
        assert task.status == TaskStatus.PENDING
        assert task.started_at is None
        
        task.start()
        
        assert task.status == TaskStatus.RUNNING
        assert isinstance(task.started_at, float)
        assert task.started_at > task.created_at
    
    def test_complete(self):
        """タスク完了のテスト."""
        task = Task()
        task.start()
        
        result = TaskResult(success=True, data={"output": "test"})
        task.complete(result)
        
        assert task.status == TaskStatus.COMPLETED
        assert isinstance(task.completed_at, float)
        assert task.completed_at >= task.started_at
        assert task.result == result
    
    def test_fail(self):
        """タスク失敗のテスト."""
        task = Task()
        task.start()
        
        error_message = "テストエラー"
        task.fail(error_message)
        
        assert task.status == TaskStatus.FAILED
        assert isinstance(task.completed_at, float)
        assert task.result is not None
        assert task.result.success is False
        assert task.result.error_message == error_message
    
    def test_can_retry(self):
        """リトライ可能性のテスト."""
        task = Task(max_retries=3)
        
        # 初期状態ではリトライ可能
        assert task.can_retry() is True
        
        # リトライ回数が最大に達するまで
        for i in range(3):
            task.increment_retry()
            if i < 2:
                assert task.can_retry() is True
            else:
                assert task.can_retry() is False
    
    def test_increment_retry(self):
        """リトライ回数インクリメントのテスト."""
        task = Task()
        task.start()
        task.fail("エラー")
        
        original_retry_count = task.retry_count
        
        task.increment_retry()
        
        assert task.retry_count == original_retry_count + 1
        assert task.status == TaskStatus.PENDING
        assert task.started_at is None
        assert task.completed_at is None
        assert task.result is None
    
    def test_duration_property(self):
        """実行時間プロパティのテスト."""
        task = Task()
        
        # 未実行時はNone
        assert task.duration is None
        
        # 開始のみではNone
        task.start()
        assert task.duration is None
        
        # 少し待って完了
        time.sleep(0.01)
        result = TaskResult(success=True)
        task.complete(result)
        
        # 実行時間が計算されている
        assert task.duration is not None
        assert task.duration > 0
        assert task.duration < 1  # 短い時間のはず
    
    def test_to_dict(self):
        """辞書変換のテスト."""
        task = Task(
            task_type="test_task",
            workflow_id="test_workflow",
            priority=5,
            input_data={"input": "test"}
        )
        task.start()
        
        result = TaskResult(success=True, data={"output": "test"})
        task.complete(result)
        
        data = task.to_dict()
        
        assert data["task_id"] == task.task_id
        assert data["task_type"] == "test_task"
        assert data["workflow_id"] == "test_workflow"
        assert data["status"] == "completed"
        assert data["priority"] == 5
        assert data["input_data"] == {"input": "test"}
        assert data["result"]["success"] is True
        assert isinstance(data["created_at"], float)
        assert isinstance(data["started_at"], float)
        assert isinstance(data["completed_at"], float)
    
    def test_from_dict(self):
        """辞書からの復元のテスト."""
        original_task = Task(
            task_type="test_task",
            workflow_id="test_workflow",
            priority=3,
            input_data={"test": "data"}
        )
        original_task.start()
        
        result = TaskResult(success=True, data={"output": "result"})
        original_task.complete(result)
        
        data = original_task.to_dict()
        restored_task = Task.from_dict(data)
        
        assert restored_task.task_id == original_task.task_id
        assert restored_task.task_type == original_task.task_type
        assert restored_task.workflow_id == original_task.workflow_id
        assert restored_task.status == original_task.status
        assert restored_task.created_at == original_task.created_at
        assert restored_task.started_at == original_task.started_at
        assert restored_task.completed_at == original_task.completed_at
        assert restored_task.priority == original_task.priority
        assert restored_task.retry_count == original_task.retry_count
        assert restored_task.max_retries == original_task.max_retries
        assert restored_task.input_data == original_task.input_data
        assert restored_task.result.success == original_task.result.success
        assert restored_task.result.data == original_task.result.data
    
    def test_from_dict_minimal(self):
        """最小限のデータからの復元テスト."""
        minimal_data = {
            "task_id": str(uuid.uuid4()),
            "task_type": "test",
            "workflow_id": "workflow",
            "status": "pending",
            "created_at": time.time(),
            "result": None
        }
        
        task = Task.from_dict(minimal_data)
        
        assert task.task_id == minimal_data["task_id"]
        assert task.task_type == "test"
        assert task.workflow_id == "workflow"
        assert task.status == TaskStatus.PENDING
        assert task.started_at is None
        assert task.completed_at is None
        assert task.priority == 0
        assert task.retry_count == 0
        assert task.max_retries == 3
        assert task.input_data == {}
        assert task.result is None 