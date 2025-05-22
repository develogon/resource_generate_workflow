import pytest
from unittest.mock import Mock, AsyncMock, patch

pytest.importorskip("app.workflow.engine", reason="WorkflowEngine module is not yet implemented")

from app.workflow.engine import WorkflowEngine


def test_workflow_engine_initialization():
    """ワークフローエンジンが適切に初期化されることを確認"""
    engine = WorkflowEngine()
    assert engine is not None
    assert hasattr(engine, "task_manager")
    assert hasattr(engine, "checkpoint_manager")


def test_register_initial_tasks(monkeypatch):
    """初期タスクの登録が正しく行われるかテスト"""
    engine = WorkflowEngine()
    
    # タスク登録のモック
    registered_tasks = []
    def mock_register(task):
        registered_tasks.append(task)
        return task.id
    
    monkeypatch.setattr(engine.task_manager, "register_task", mock_register, raising=False)
    
    # 初期タスク登録を実行
    engine.register_initial_tasks(title="テスト", input_path="test/path/text.md")
    
    # 登録されたタスクを検証
    assert len(registered_tasks) > 0
    # 少なくとも1つの初期タスクが登録されていることを確認
    assert any(task.type == "split_chapters" for task in registered_tasks)


@pytest.mark.asyncio
async def test_run_workflow(monkeypatch):
    """ワークフロー実行プロセスが正しく動作するかテスト"""
    engine = WorkflowEngine()
    
    # タスク実行のモック
    executed_tasks = []
    async def mock_execute_task(task):
        executed_tasks.append(task.id)
        return {"status": "completed"}
    
    # タスク取得のモック - 2つのタスクを返した後にNoneを返す
    task_index = 0
    def mock_get_next_task():
        nonlocal task_index
        if task_index < 2:
            task = Mock()
            task.id = f"task_{task_index}"
            task_index += 1
            return task
        return None  # すべてのタスクが完了
    
    monkeypatch.setattr(engine, "execute_task", mock_execute_task, raising=False)
    monkeypatch.setattr(engine.task_manager, "get_next_executable_task", mock_get_next_task, raising=False)
    monkeypatch.setattr(engine.checkpoint_manager, "save_checkpoint", lambda type: f"{type}_checkpoint", raising=False)
    
    # ワークフロー実行
    result = await engine.run()
    
    # 両方のタスクが実行されたことを確認
    assert "task_0" in executed_tasks
    assert "task_1" in executed_tasks
    assert len(executed_tasks) == 2
    assert result["status"] == "completed"


def test_resume_workflow(monkeypatch):
    """ワークフローの再開が正しく動作するかテスト"""
    engine = WorkflowEngine()
    
    # チェックポイント復元のモック
    restore_called = False
    def mock_restore(checkpoint_id):
        nonlocal restore_called
        restore_called = True
    
    monkeypatch.setattr(engine.checkpoint_manager, "restore_from_checkpoint", mock_restore, raising=False)
    
    # ワークフロー再開
    engine.resume_workflow("checkpoint_123")
    
    # チェックポイントから復元されたことを確認
    assert restore_called


@pytest.mark.asyncio
async def test_execute_task(monkeypatch):
    """タスク実行が正しく行われるかテスト"""
    engine = WorkflowEngine()
    
    # タスク実行ハンドラのモック
    mock_handlers = {
        "split_chapters": AsyncMock(return_value={"chapters": ["ch1", "ch2"]}),
        "create_article": AsyncMock(return_value={"article": "content"})
    }
    
    monkeypatch.setattr(engine, "_task_handlers", mock_handlers, raising=False)
    monkeypatch.setattr(engine.task_manager, "mark_as_completed", lambda id, result: None, raising=False)
    
    # 章分割タスクを実行
    task = Mock()
    task.id = "task_1"
    task.type = "split_chapters"
    task.params = {"content": "# Chapter\nText"}
    
    result = await engine.execute_task(task)
    
    # 適切なハンドラが呼び出され、結果が返されることを確認
    mock_handlers["split_chapters"].assert_awaited_once()
    assert "chapters" in result
    assert len(result["chapters"]) == 2


def test_handle_task_failure(monkeypatch):
    """タスク失敗時の処理が正しく行われるかテスト"""
    engine = WorkflowEngine()
    
    # 失敗ハンドリングのモック
    handled_errors = []
    def mock_mark_failed(task_id, error):
        handled_errors.append((task_id, error))
    
    monkeypatch.setattr(engine.task_manager, "mark_as_failed", mock_mark_failed, raising=False)
    
    # エラー処理
    engine.handle_task_failure("failed_task", ValueError("処理失敗"))
    
    # エラーが記録されることを確認
    assert len(handled_errors) == 1
    assert handled_errors[0][0] == "failed_task"
    assert isinstance(handled_errors[0][1], ValueError)


def test_progress_tracking():
    """進捗追跡が正しく機能するかテスト"""
    engine = WorkflowEngine()
    
    # 初期状態
    assert engine.get_progress() == 0.0
    
    # タスク完了を記録
    engine.update_progress(1, 10)  # 1/10 = 10%
    assert engine.get_progress() == 0.1
    
    engine.update_progress(5, 10)  # 5/10 = 50%
    assert engine.get_progress() == 0.5
    
    engine.update_progress(10, 10)  # 10/10 = 100%
    assert engine.get_progress() == 1.0 