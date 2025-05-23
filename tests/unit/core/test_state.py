"""
StateManagerの単体テスト

StateManager、WorkflowState、Checkpointクラスの機能をテストします：
- ワークフロー作成・更新・削除
- 状態管理とタスク追跡
- チェックポイント機能
- 復旧可能状態の取得
- 統計情報取得
"""

import pytest
import pytest_asyncio
import time
from typing import Dict, Any

from src.core.state_manager import (
    StateManager,
    WorkflowState,
    WorkflowStatus,
    Checkpoint
)


@pytest_asyncio.fixture
async def state_manager():
    """StateManagerのフィクスチャ"""
    manager = StateManager(storage_backend="memory")
    await manager.initialize()
    yield manager
    await manager.close()


@pytest_asyncio.fixture
async def redis_state_manager():
    """Redis backend StateManagerのフィクスチャ（モック）"""
    # Redis が利用できない環境でもテストできるようにmemoryにフォールバック
    manager = StateManager(storage_backend="redis", redis_url="redis://localhost:6379")
    await manager.initialize()
    yield manager
    await manager.close()


@pytest.fixture
def sample_workflow_data():
    """サンプルワークフローデータ"""
    return {
        "workflow_id": "test-workflow-001",
        "lang": "ja",
        "title": "テストワークフロー",
        "metadata": {"author": "test-user", "version": "1.0"}
    }


class TestWorkflowState:
    """WorkflowStateクラスのテスト"""
    
    def test_workflow_state_creation(self):
        """ワークフロー状態の作成テスト"""
        now = time.time()
        state = WorkflowState(
            workflow_id="test-001",
            status=WorkflowStatus.INITIALIZED,
            lang="ja",
            title="テストワークフロー",
            created_at=now,
            updated_at=now,
            metadata={"test": "data"},
            progress={"step": 1},
            completed_tasks={"task1", "task2"},
            failed_tasks={"task3"}
        )
        
        assert state.workflow_id == "test-001"
        assert state.status == WorkflowStatus.INITIALIZED
        assert state.lang == "ja"
        assert state.title == "テストワークフロー"
        assert "task1" in state.completed_tasks
        assert "task3" in state.failed_tasks
    
    def test_to_dict_conversion(self):
        """辞書形式への変換テスト"""
        now = time.time()
        state = WorkflowState(
            workflow_id="test-001",
            status=WorkflowStatus.RUNNING,
            lang="en",
            title="Test Workflow",
            created_at=now,
            updated_at=now,
            metadata={"key": "value"},
            progress={"progress": 50},
            completed_tasks={"task1"},
            failed_tasks={"task2"}
        )
        
        state_dict = state.to_dict()
        
        assert state_dict["workflow_id"] == "test-001"
        assert state_dict["status"] == "running"
        assert state_dict["completed_tasks"] == ["task1"]
        assert state_dict["failed_tasks"] == ["task2"]
        assert isinstance(state_dict["completed_tasks"], list)
        assert isinstance(state_dict["failed_tasks"], list)
    
    def test_from_dict_conversion(self):
        """辞書からの復元テスト"""
        state_dict = {
            "workflow_id": "test-001",
            "status": "completed",
            "lang": "ja",
            "title": "テストワークフロー",
            "created_at": 1234567890.0,
            "updated_at": 1234567891.0,
            "metadata": {"key": "value"},
            "progress": {"step": 2},
            "completed_tasks": ["task1", "task2"],
            "failed_tasks": ["task3"]
        }
        
        state = WorkflowState.from_dict(state_dict)
        
        assert state.workflow_id == "test-001"
        assert state.status == WorkflowStatus.COMPLETED
        assert state.completed_tasks == {"task1", "task2"}
        assert state.failed_tasks == {"task3"}


class TestCheckpoint:
    """Checkpointクラスのテスト"""
    
    def test_checkpoint_creation(self):
        """チェックポイントの作成テスト"""
        now = time.time()
        checkpoint = Checkpoint(
            checkpoint_id="checkpoint-001",
            workflow_id="workflow-001",
            checkpoint_type="section_completed",
            timestamp=now,
            data={"section_id": "section-1", "status": "completed"}
        )
        
        assert checkpoint.checkpoint_id == "checkpoint-001"
        assert checkpoint.workflow_id == "workflow-001"
        assert checkpoint.checkpoint_type == "section_completed"
        assert checkpoint.timestamp == now
        assert checkpoint.data["section_id"] == "section-1"
    
    def test_checkpoint_serialization(self):
        """チェックポイントのシリアライゼーションテスト"""
        now = time.time()
        checkpoint = Checkpoint(
            checkpoint_id="checkpoint-001",
            workflow_id="workflow-001",
            checkpoint_type="test",
            timestamp=now,
            data={"key": "value"}
        )
        
        # 辞書変換
        checkpoint_dict = checkpoint.to_dict()
        assert checkpoint_dict["checkpoint_id"] == "checkpoint-001"
        assert checkpoint_dict["data"]["key"] == "value"
        
        # 復元
        restored = Checkpoint.from_dict(checkpoint_dict)
        assert restored.checkpoint_id == checkpoint.checkpoint_id
        assert restored.workflow_id == checkpoint.workflow_id
        assert restored.data == checkpoint.data


class TestStateManager:
    """StateManagerクラスのテスト"""
    
    @pytest.mark.asyncio
    async def test_initialization(self):
        """StateManagerの初期化テスト"""
        manager = StateManager(storage_backend="memory")
        await manager.initialize()
        
        assert manager.storage_backend == "memory"
        assert manager._redis is None
        
        await manager.close()
    
    @pytest.mark.asyncio
    async def test_create_workflow(self, state_manager, sample_workflow_data):
        """ワークフロー作成テスト"""
        state = await state_manager.create_workflow(
            sample_workflow_data["workflow_id"],
            sample_workflow_data["lang"],
            sample_workflow_data["title"],
            sample_workflow_data["metadata"]
        )
        
        assert state.workflow_id == sample_workflow_data["workflow_id"]
        assert state.status == WorkflowStatus.INITIALIZED
        assert state.lang == sample_workflow_data["lang"]
        assert state.title == sample_workflow_data["title"]
        assert state.metadata == sample_workflow_data["metadata"]
        assert len(state.completed_tasks) == 0
        assert len(state.failed_tasks) == 0
    
    @pytest.mark.asyncio
    async def test_create_duplicate_workflow(self, state_manager, sample_workflow_data):
        """重複ワークフロー作成のエラーテスト"""
        # 最初のワークフロー作成
        await state_manager.create_workflow(
            sample_workflow_data["workflow_id"],
            sample_workflow_data["lang"],
            sample_workflow_data["title"]
        )
        
        # 同じIDで再作成を試行
        with pytest.raises(ValueError, match="already exists"):
            await state_manager.create_workflow(
                sample_workflow_data["workflow_id"],
                sample_workflow_data["lang"],
                sample_workflow_data["title"]
            )
    
    @pytest.mark.asyncio
    async def test_get_workflow_state(self, state_manager, sample_workflow_data):
        """ワークフロー状態取得テスト"""
        # 存在しないワークフロー
        state = await state_manager.get_workflow_state("non-existent")
        assert state is None
        
        # ワークフロー作成
        created_state = await state_manager.create_workflow(
            sample_workflow_data["workflow_id"],
            sample_workflow_data["lang"],
            sample_workflow_data["title"]
        )
        
        # 作成したワークフローの取得
        retrieved_state = await state_manager.get_workflow_state(sample_workflow_data["workflow_id"])
        assert retrieved_state is not None
        assert retrieved_state.workflow_id == created_state.workflow_id
        assert retrieved_state.status == created_state.status
    
    @pytest.mark.asyncio
    async def test_update_workflow_state(self, state_manager, sample_workflow_data):
        """ワークフロー状態更新テスト"""
        # ワークフロー作成
        await state_manager.create_workflow(
            sample_workflow_data["workflow_id"],
            sample_workflow_data["lang"],
            sample_workflow_data["title"]
        )
        
        # 状態更新
        updated_state = await state_manager.update_workflow_state(
            sample_workflow_data["workflow_id"],
            status=WorkflowStatus.RUNNING,
            metadata={"updated": True},
            progress={"step": 1, "total": 5}
        )
        
        assert updated_state.status == WorkflowStatus.RUNNING
        assert updated_state.metadata["updated"] is True
        assert updated_state.progress["step"] == 1
        assert updated_state.progress["total"] == 5
    
    @pytest.mark.asyncio
    async def test_update_nonexistent_workflow(self, state_manager):
        """存在しないワークフローの更新エラーテスト"""
        with pytest.raises(ValueError, match="not found"):
            await state_manager.update_workflow_state(
                "non-existent",
                status=WorkflowStatus.RUNNING
            )
    
    @pytest.mark.asyncio
    async def test_mark_task_completed(self, state_manager, sample_workflow_data):
        """タスク完了マークテスト"""
        # ワークフロー作成
        await state_manager.create_workflow(
            sample_workflow_data["workflow_id"],
            sample_workflow_data["lang"],
            sample_workflow_data["title"]
        )
        
        # タスクを完了としてマーク
        updated_state = await state_manager.mark_task_completed(
            sample_workflow_data["workflow_id"],
            "task-001"
        )
        
        assert "task-001" in updated_state.completed_tasks
        assert "task-001" not in updated_state.failed_tasks
    
    @pytest.mark.asyncio
    async def test_mark_task_failed(self, state_manager, sample_workflow_data):
        """タスク失敗マークテスト"""
        # ワークフロー作成
        await state_manager.create_workflow(
            sample_workflow_data["workflow_id"],
            sample_workflow_data["lang"],
            sample_workflow_data["title"]
        )
        
        # まずタスクを完了としてマーク
        await state_manager.mark_task_completed(
            sample_workflow_data["workflow_id"],
            "task-001"
        )
        
        # 同じタスクを失敗としてマーク
        updated_state = await state_manager.mark_task_failed(
            sample_workflow_data["workflow_id"],
            "task-001"
        )
        
        assert "task-001" not in updated_state.completed_tasks
        assert "task-001" in updated_state.failed_tasks
    
    @pytest.mark.asyncio
    async def test_save_checkpoint(self, state_manager, sample_workflow_data):
        """チェックポイント保存テスト"""
        # ワークフロー作成
        await state_manager.create_workflow(
            sample_workflow_data["workflow_id"],
            sample_workflow_data["lang"],
            sample_workflow_data["title"]
        )
        
        # チェックポイント保存
        checkpoint = await state_manager.save_checkpoint(
            sample_workflow_data["workflow_id"],
            "section_completed",
            {"section_id": "section-1", "completed_tasks": ["task-1", "task-2"]}
        )
        
        assert checkpoint.workflow_id == sample_workflow_data["workflow_id"]
        assert checkpoint.checkpoint_type == "section_completed"
        assert checkpoint.data["section_id"] == "section-1"
        assert checkpoint.timestamp > 0
    
    @pytest.mark.asyncio
    async def test_get_checkpoints(self, state_manager, sample_workflow_data):
        """チェックポイント取得テスト"""
        # ワークフロー作成
        await state_manager.create_workflow(
            sample_workflow_data["workflow_id"],
            sample_workflow_data["lang"],
            sample_workflow_data["title"]
        )
        
        # 複数のチェックポイントを保存
        checkpoint1 = await state_manager.save_checkpoint(
            sample_workflow_data["workflow_id"],
            "step1",
            {"data": "checkpoint1"}
        )
        
        checkpoint2 = await state_manager.save_checkpoint(
            sample_workflow_data["workflow_id"],
            "step2",
            {"data": "checkpoint2"}
        )
        
        # チェックポイント取得
        checkpoints = await state_manager.get_checkpoints(sample_workflow_data["workflow_id"])
        
        assert len(checkpoints) == 2
        checkpoint_ids = [cp.checkpoint_id for cp in checkpoints]
        assert checkpoint1.checkpoint_id in checkpoint_ids
        assert checkpoint2.checkpoint_id in checkpoint_ids
    
    @pytest.mark.asyncio
    async def test_get_latest_checkpoint(self, state_manager, sample_workflow_data):
        """最新チェックポイント取得テスト"""
        # ワークフロー作成
        await state_manager.create_workflow(
            sample_workflow_data["workflow_id"],
            sample_workflow_data["lang"],
            sample_workflow_data["title"]
        )
        
        # チェックポイントがない場合
        latest = await state_manager.get_latest_checkpoint(sample_workflow_data["workflow_id"])
        assert latest is None
        
        # 最初のチェックポイント
        checkpoint1 = await state_manager.save_checkpoint(
            sample_workflow_data["workflow_id"],
            "step1",
            {"data": "checkpoint1"}
        )
        
        # 少し待機してから2番目のチェックポイント
        import asyncio
        await asyncio.sleep(0.01)
        
        checkpoint2 = await state_manager.save_checkpoint(
            sample_workflow_data["workflow_id"],
            "step2",
            {"data": "checkpoint2"}
        )
        
        # 最新チェックポイント取得
        latest = await state_manager.get_latest_checkpoint(sample_workflow_data["workflow_id"])
        assert latest is not None
        assert latest.checkpoint_id == checkpoint2.checkpoint_id
        assert latest.timestamp >= checkpoint1.timestamp
    
    @pytest.mark.asyncio
    async def test_get_resumable_state(self, state_manager, sample_workflow_data):
        """復旧可能状態取得テスト"""
        # ワークフロー作成
        await state_manager.create_workflow(
            sample_workflow_data["workflow_id"],
            sample_workflow_data["lang"],
            sample_workflow_data["title"]
        )
        
        # タスクの完了・失敗をマーク
        await state_manager.mark_task_completed(sample_workflow_data["workflow_id"], "task-1")
        await state_manager.mark_task_failed(sample_workflow_data["workflow_id"], "task-2")
        
        # チェックポイント保存
        checkpoint = await state_manager.save_checkpoint(
            sample_workflow_data["workflow_id"],
            "section_completed",
            {"section_id": "section-1"}
        )
        
        # 復旧可能状態取得
        resumable_state = await state_manager.get_resumable_state(sample_workflow_data["workflow_id"])
        
        assert resumable_state is not None
        assert resumable_state["workflow_state"].workflow_id == sample_workflow_data["workflow_id"]
        assert resumable_state["latest_checkpoint"].checkpoint_id == checkpoint.checkpoint_id
        assert "task-1" in resumable_state["completed_tasks"]
        assert "task-2" in resumable_state["failed_tasks"]
    
    @pytest.mark.asyncio
    async def test_delete_workflow(self, state_manager, sample_workflow_data):
        """ワークフロー削除テスト"""
        # ワークフロー作成
        await state_manager.create_workflow(
            sample_workflow_data["workflow_id"],
            sample_workflow_data["lang"],
            sample_workflow_data["title"]
        )
        
        # チェックポイント保存
        await state_manager.save_checkpoint(
            sample_workflow_data["workflow_id"],
            "test",
            {"data": "test"}
        )
        
        # 削除前の確認
        state_before = await state_manager.get_workflow_state(sample_workflow_data["workflow_id"])
        assert state_before is not None
        
        # ワークフロー削除
        success = await state_manager.delete_workflow(sample_workflow_data["workflow_id"])
        assert success is True
        
        # 削除後の確認
        state_after = await state_manager.get_workflow_state(sample_workflow_data["workflow_id"])
        assert state_after is None
        
        checkpoints_after = await state_manager.get_checkpoints(sample_workflow_data["workflow_id"])
        assert len(checkpoints_after) == 0
    
    @pytest.mark.asyncio
    async def test_list_workflows(self, state_manager):
        """ワークフロー一覧取得テスト"""
        # 初期状態では空
        workflows = await state_manager.list_workflows()
        assert len(workflows) == 0
        
        # 複数のワークフローを作成
        await state_manager.create_workflow("workflow-1", "ja", "ワークフロー1")
        await state_manager.create_workflow("workflow-2", "en", "Workflow 2")
        
        # ワークフロー2を実行中に変更
        await state_manager.update_workflow_state("workflow-2", status=WorkflowStatus.RUNNING)
        
        # 全ワークフロー取得
        all_workflows = await state_manager.list_workflows()
        assert len(all_workflows) == 2
        
        # ステータスフィルタ
        running_workflows = await state_manager.list_workflows(status_filter=WorkflowStatus.RUNNING)
        assert len(running_workflows) == 1
        assert running_workflows[0].workflow_id == "workflow-2"
        
        initialized_workflows = await state_manager.list_workflows(status_filter=WorkflowStatus.INITIALIZED)
        assert len(initialized_workflows) == 1
        assert initialized_workflows[0].workflow_id == "workflow-1"
    
    @pytest.mark.asyncio
    async def test_get_stats(self, state_manager):
        """統計情報取得テスト"""
        # 初期統計
        stats = await state_manager.get_stats()
        assert stats["total_workflows"] == 0
        assert stats["total_checkpoints"] == 0
        assert stats["storage_backend"] == "memory"
        assert stats["redis_connected"] is False
        
        # ワークフロー作成
        await state_manager.create_workflow("workflow-1", "ja", "ワークフロー1")
        await state_manager.create_workflow("workflow-2", "en", "Workflow 2")
        await state_manager.update_workflow_state("workflow-2", status=WorkflowStatus.RUNNING)
        
        # チェックポイント保存
        await state_manager.save_checkpoint("workflow-1", "test", {"data": "test"})
        await state_manager.save_checkpoint("workflow-2", "test", {"data": "test"})
        
        # 統計確認
        stats = await state_manager.get_stats()
        assert stats["total_workflows"] == 2
        assert stats["total_checkpoints"] == 2
        assert stats["status_counts"]["initialized"] == 1
        assert stats["status_counts"]["running"] == 1
    
    @pytest.mark.asyncio
    async def test_concurrent_access(self, state_manager):
        """並行アクセステスト"""
        workflow_id = "concurrent-test"
        
        # ワークフロー作成
        await state_manager.create_workflow(workflow_id, "ja", "並行テスト")
        
        async def mark_tasks(start_id: int, count: int):
            """タスクを並行でマーク"""
            for i in range(count):
                task_id = f"task-{start_id + i}"
                if i % 2 == 0:
                    await state_manager.mark_task_completed(workflow_id, task_id)
                else:
                    await state_manager.mark_task_failed(workflow_id, task_id)
        
        # 並行でタスクをマーク
        import asyncio
        await asyncio.gather(
            mark_tasks(0, 10),
            mark_tasks(10, 10),
            mark_tasks(20, 10)
        )
        
        # 結果確認
        final_state = await state_manager.get_workflow_state(workflow_id)
        assert len(final_state.completed_tasks) == 15  # 偶数番号のタスク
        assert len(final_state.failed_tasks) == 15     # 奇数番号のタスク 