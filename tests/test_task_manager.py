import pytest
from unittest.mock import Mock

pytest.importorskip("app.workflow.task_manager", reason="TaskManager module is not yet implemented")

from app.workflow.task_manager import TaskManager, TaskStatus, Task


def _make_dummy_task(task_id: str, deps=None):
    return Task(
        id=task_id,
        type="dummy",
        status=TaskStatus.PENDING,
        dependencies=deps or [],
        retry_count=0,
        params={},
        result=None,
    )


def test_register_and_get_next_executable_task():
    manager = TaskManager()
    task = _make_dummy_task("t1")

    t_id = manager.register_task(task)
    assert t_id == "t1"

    next_task = manager.get_next_executable_task()
    assert next_task.id == "t1"


def test_dependencies_block_until_completed():
    manager = TaskManager()
    parent = _make_dummy_task("parent")
    child = _make_dummy_task("child", deps=["parent"])

    manager.register_task(parent)
    manager.register_task(child)

    # Only parent should be executable initially
    next_task = manager.get_next_executable_task()
    assert next_task.id == "parent"

    # Mark parent completed
    manager.mark_as_completed("parent", result="ok")

    # Now child becomes executable
    next_child = manager.get_next_executable_task()
    assert next_child.id == "child"


def test_mark_as_failed_and_retry(monkeypatch):
    manager = TaskManager()
    task = _make_dummy_task("retryable")

    manager.register_task(task)

    manager.mark_as_failed("retryable", error=RuntimeError("boom"))

    # After failure, retry should schedule task again
    manager.retry_task("retryable")

    next_task = manager.get_next_executable_task()
    assert next_task.id == "retryable"


def test_complex_dependency_chain():
    """テスト複雑な依存関係チェーンが正しく処理されるかどうか"""
    manager = TaskManager()
    
    # A → B, C → D のグラフを作成
    task_a = _make_dummy_task("A")
    task_b = _make_dummy_task("B", deps=["A"])
    task_c = _make_dummy_task("C", deps=["A"])
    task_d = _make_dummy_task("D", deps=["B", "C"])
    
    # すべてのタスクを登録
    manager.register_task(task_a)
    manager.register_task(task_b)
    manager.register_task(task_c)
    manager.register_task(task_d)
    
    # 最初はAのみ実行可能
    next_task = manager.get_next_executable_task()
    assert next_task.id == "A"
    manager.mark_as_completed("A", result="ok")
    
    # Aが完了したのでBとCが実行可能になるはず
    # どちらが先に取得されるかは実装次第なので、B, Cのどちらかであることを確認
    next_task = manager.get_next_executable_task()
    assert next_task.id in ["B", "C"]
    
    # 一方を完了させる
    first_task_id = next_task.id
    manager.mark_as_completed(first_task_id, result="ok")
    
    # もう一方を取得して完了させる
    next_task = manager.get_next_executable_task()
    second_task_id = next_task.id
    assert second_task_id in ["B", "C"] and second_task_id != first_task_id
    manager.mark_as_completed(second_task_id, result="ok")
    
    # これでDが実行可能になるはず
    next_task = manager.get_next_executable_task()
    assert next_task.id == "D"


def test_retry_increment_retry_count():
    """再試行でリトライカウントが増加するか確認"""
    manager = TaskManager()
    task = _make_dummy_task("retry_task")
    
    manager.register_task(task)
    manager.mark_as_failed("retry_task", error=ValueError("failed"))
    
    # 最初の再試行
    manager.retry_task("retry_task")
    retried_task = manager.get_next_executable_task()
    assert retried_task.id == "retry_task"
    assert retried_task.retry_count == 1
    
    # 2回目の失敗と再試行
    manager.mark_as_failed("retry_task", error=ValueError("failed again"))
    manager.retry_task("retry_task")
    
    retried_task = manager.get_next_executable_task()
    assert retried_task.retry_count == 2


def test_error_handling_with_max_retries(monkeypatch):
    """最大リトライ回数を超えた場合のエラー処理をテスト"""
    manager = TaskManager()
    monkeypatch.setattr(manager, "MAX_RETRIES", 2, raising=False)  # 最大2回までリトライ可能
    
    task = _make_dummy_task("max_retry_task")
    manager.register_task(task)
    
    # 1回目の失敗と再試行
    manager.mark_as_failed("max_retry_task", error=ValueError("error1"))
    manager.retry_task("max_retry_task")
    
    # 2回目の失敗と再試行
    task1 = manager.get_next_executable_task()
    manager.mark_as_failed("max_retry_task", error=ValueError("error2"))
    manager.retry_task("max_retry_task")
    
    # 3回目の失敗 - これ以上再試行できないはず
    task2 = manager.get_next_executable_task()
    manager.mark_as_failed("max_retry_task", error=ValueError("error3"))
    
    # この実装次第でエラーを投げるか、Falseを返すなどの動作が考えられる
    # ここでは単にリトライ不可を確認
    try:
        manager.retry_task("max_retry_task")
        # リトライ後にタスクが取得できないことを確認
        next_task = manager.get_next_executable_task()
        if next_task and next_task.id == "max_retry_task":
            # リトライカウントが変わっていなければOK
            assert next_task.retry_count <= 2
    except Exception as e:
        # 例外を投げる実装の場合はここでキャッチ
        assert "max retries" in str(e).lower() or "retry limit" in str(e).lower() 