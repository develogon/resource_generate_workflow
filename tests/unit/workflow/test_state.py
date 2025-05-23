"""ワークフロー状態管理システムのテスト."""

import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.models.workflow import WorkflowStatus
from src.workflow.engine import (
    ExecutionMode,
    StepExecution,
    StepExecutionStatus,
    WorkflowExecution,
)
from src.workflow.state import (
    FileStateStore,
    MemoryStateStore,
    StateManager,
    StateStore,
)


class TestStateStore:
    """StateStore抽象クラスのテスト."""
    
    def test_abstract_methods(self):
        """抽象メソッドの確認."""
        # StateStoreを直接インスタンス化できないことを確認
        with pytest.raises(TypeError):
            StateStore()


class TestFileStateStore:
    """FileStateStoreのテスト."""
    
    @pytest.fixture
    def temp_dir(self):
        """一時ディレクトリフィクスチャ."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def file_store(self, temp_dir):
        """FileStateStoreフィクスチャ."""
        return FileStateStore(temp_dir)
    
    @pytest.fixture
    def sample_execution(self):
        """サンプル実行状態フィクスチャ."""
        execution = WorkflowExecution(
            id="test-execution-1",
            workflow_id="test-workflow",
            status=WorkflowStatus.RUNNING,
            start_time=1640995200.0,  # 2022-01-01 00:00:00
            context={"lang": "ja", "title": "テスト"},
            mode=ExecutionMode.ASYNC,
            metadata={"source": "test"}
        )
        
        # ステップ実行状態を追加
        step_execution = StepExecution(
            step_id="step1",
            task_id="task1",
            status=StepExecutionStatus.COMPLETED,
            start_time=1640995260.0,
            end_time=1640995320.0,
            result={"output": "success"},
            metadata={"duration": 60}
        )
        execution.step_executions["step1"] = step_execution
        
        return execution
    
    def test_initialization(self, temp_dir):
        """初期化のテスト."""
        store = FileStateStore(temp_dir)
        
        assert store.base_path == temp_dir
        assert store.executions_path == temp_dir / "executions"
        assert store.executions_path.exists()
    
    def test_get_execution_file(self, file_store):
        """実行ファイルパス取得のテスト."""
        execution_id = "test-execution-1"
        file_path = file_store._get_execution_file(execution_id)
        
        expected_path = file_store.executions_path / f"{execution_id}.json"
        assert file_path == expected_path
    
    @pytest.mark.asyncio
    async def test_save_execution(self, file_store, sample_execution):
        """実行状態保存のテスト."""
        result = await file_store.save_execution(sample_execution)
        
        assert result is True
        
        # ファイルが作成されていることを確認
        file_path = file_store._get_execution_file(sample_execution.id)
        assert file_path.exists()
        
        # ファイル内容を確認
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert data["id"] == sample_execution.id
        assert data["workflow_id"] == sample_execution.workflow_id
        assert data["status"] == sample_execution.status.value
        assert data["context"] == sample_execution.context
        assert "step_executions" in data
        assert "step1" in data["step_executions"]
    
    @pytest.mark.asyncio
    async def test_load_execution(self, file_store, sample_execution):
        """実行状態読み込みのテスト."""
        # まず保存
        await file_store.save_execution(sample_execution)
        
        # 読み込み
        loaded_execution = await file_store.load_execution(sample_execution.id)
        
        assert loaded_execution is not None
        assert loaded_execution.id == sample_execution.id
        assert loaded_execution.workflow_id == sample_execution.workflow_id
        assert loaded_execution.status == sample_execution.status
        assert loaded_execution.context == sample_execution.context
        assert loaded_execution.mode == sample_execution.mode
        assert len(loaded_execution.step_executions) == 1
        assert "step1" in loaded_execution.step_executions
    
    @pytest.mark.asyncio
    async def test_load_nonexistent_execution(self, file_store):
        """存在しない実行状態の読み込みテスト."""
        result = await file_store.load_execution("nonexistent-id")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_delete_execution(self, file_store, sample_execution):
        """実行状態削除のテスト."""
        # まず保存
        await file_store.save_execution(sample_execution)
        
        # 削除
        result = await file_store.delete_execution(sample_execution.id)
        assert result is True
        
        # ファイルが削除されていることを確認
        file_path = file_store._get_execution_file(sample_execution.id)
        assert not file_path.exists()
        
        # 存在しないファイルの削除
        result = await file_store.delete_execution("nonexistent-id")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_list_executions(self, file_store):
        """実行状態一覧取得のテスト."""
        # 複数の実行状態を保存
        executions = []
        for i in range(3):
            execution = WorkflowExecution(
                id=f"test-execution-{i}",
                workflow_id=f"workflow-{i % 2}",  # 2つのワークフローに分ける
                status=WorkflowStatus.COMPLETED if i % 2 == 0 else WorkflowStatus.RUNNING,
                context={"index": i}
            )
            executions.append(execution)
            await file_store.save_execution(execution)
        
        # 全ての実行状態を取得
        all_executions = await file_store.list_executions()
        assert len(all_executions) == 3
        
        # ワークフローIDでフィルタ
        workflow_0_executions = await file_store.list_executions(workflow_id="workflow-0")
        assert len(workflow_0_executions) == 2
        
        # ステータスでフィルタ
        running_executions = await file_store.list_executions(status="running")
        assert len(running_executions) == 1
        
        # 両方でフィルタ
        specific_executions = await file_store.list_executions(
            workflow_id="workflow-1", 
            status="running"
        )
        assert len(specific_executions) == 1
        
        # 制限数でフィルタ
        limited_executions = await file_store.list_executions(limit=2)
        assert len(limited_executions) == 2
    
    @pytest.mark.asyncio
    async def test_cleanup_old_executions(self, file_store):
        """古い実行状態クリーンアップのテスト."""
        # 古い実行状態を作成（30日以上前）
        old_execution = WorkflowExecution(
            id="old-execution",
            workflow_id="test-workflow",
            status=WorkflowStatus.COMPLETED,
            start_time=1609459200.0,  # 2021-01-01 00:00:00
            context={}
        )
        await file_store.save_execution(old_execution)
        
        # 新しい実行状態を作成
        new_execution = WorkflowExecution(
            id="new-execution",
            workflow_id="test-workflow",
            status=WorkflowStatus.COMPLETED,
            context={}
        )
        await file_store.save_execution(new_execution)
        
        # クリーンアップ実行
        cleaned_count = await file_store.cleanup_old_executions(days_old=30)
        
        assert cleaned_count == 1
        
        # 古いファイルが削除され、新しいファイルが残っていることを確認
        assert not file_store._get_execution_file("old-execution").exists()
        assert file_store._get_execution_file("new-execution").exists()
    
    @pytest.mark.asyncio
    async def test_save_execution_error_handling(self, file_store):
        """保存エラーハンドリングのテスト."""
        # 無効なパスを設定してエラーを発生させる
        file_store.executions_path = Path("/invalid/path/that/does/not/exist")
        
        execution = WorkflowExecution(
            id="test-execution",
            workflow_id="test-workflow",
            status=WorkflowStatus.RUNNING,
            context={}
        )
        
        with patch('builtins.open', side_effect=PermissionError("Permission denied")):
            result = await file_store.save_execution(execution)
            assert result is False


class TestMemoryStateStore:
    """MemoryStateStoreのテスト."""
    
    @pytest.fixture
    def memory_store(self):
        """MemoryStateStoreフィクスチャ."""
        return MemoryStateStore()
    
    @pytest.fixture
    def sample_execution(self):
        """サンプル実行状態フィクスチャ."""
        execution = WorkflowExecution(
            id="test-execution-1",
            workflow_id="test-workflow",
            status=WorkflowStatus.RUNNING,
            context={"lang": "ja"},
            mode=ExecutionMode.SYNC
        )
        return execution
    
    def test_initialization(self, memory_store):
        """初期化のテスト."""
        assert memory_store.executions == {}
    
    @pytest.mark.asyncio
    async def test_save_and_load_execution(self, memory_store, sample_execution):
        """実行状態の保存と読み込みテスト."""
        # 保存
        result = await memory_store.save_execution(sample_execution)
        assert result is True
        
        # 読み込み
        loaded_execution = await memory_store.load_execution(sample_execution.id)
        assert loaded_execution is not None
        assert loaded_execution.id == sample_execution.id
        assert loaded_execution.workflow_id == sample_execution.workflow_id
        assert loaded_execution.status == sample_execution.status
    
    @pytest.mark.asyncio
    async def test_load_nonexistent_execution(self, memory_store):
        """存在しない実行状態の読み込みテスト."""
        result = await memory_store.load_execution("nonexistent-id")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_delete_execution(self, memory_store, sample_execution):
        """実行状態削除のテスト."""
        # 保存
        await memory_store.save_execution(sample_execution)
        
        # 削除
        result = await memory_store.delete_execution(sample_execution.id)
        assert result is True
        
        # 削除されていることを確認
        loaded = await memory_store.load_execution(sample_execution.id)
        assert loaded is None
        
        # 存在しない実行の削除
        result = await memory_store.delete_execution("nonexistent-id")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_list_executions(self, memory_store):
        """実行状態一覧取得のテスト."""
        # 複数の実行状態を保存
        executions = []
        for i in range(3):
            execution = WorkflowExecution(
                id=f"test-execution-{i}",
                workflow_id=f"workflow-{i % 2}",
                status=WorkflowStatus.COMPLETED if i % 2 == 0 else WorkflowStatus.RUNNING,
                context={"index": i}
            )
            executions.append(execution)
            await memory_store.save_execution(execution)
        
        # 全ての実行状態を取得
        all_executions = await memory_store.list_executions()
        assert len(all_executions) == 3
        
        # フィルタリングテスト
        workflow_0_executions = await memory_store.list_executions(workflow_id="workflow-0")
        assert len(workflow_0_executions) == 2
        
        running_executions = await memory_store.list_executions(status="running")
        assert len(running_executions) == 1
    
    @pytest.mark.asyncio
    async def test_cleanup_old_executions(self, memory_store):
        """古い実行状態クリーンアップのテスト."""
        # メモリストアではクリーンアップ操作は無効
        result = await memory_store.cleanup_old_executions(days_old=30)
        assert result == 0


class TestStateManager:
    """StateManagerのテスト."""
    
    @pytest.fixture
    def mock_store(self):
        """モックストアフィクスチャ."""
        return Mock(spec=StateStore)
    
    @pytest.fixture
    def state_manager(self, mock_store):
        """StateManagerフィクスチャ."""
        return StateManager(mock_store)
    
    @pytest.fixture
    def sample_execution(self):
        """サンプル実行状態フィクスチャ."""
        return WorkflowExecution(
            id="test-execution",
            workflow_id="test-workflow",
            status=WorkflowStatus.RUNNING,
            context={}
        )
    
    def test_initialization(self, mock_store):
        """初期化のテスト."""
        manager = StateManager(mock_store)
        assert manager.store == mock_store
    
    @pytest.mark.asyncio
    async def test_save_execution_state(self, state_manager, mock_store, sample_execution):
        """実行状態保存のテスト."""
        mock_store.save_execution.return_value = True
        
        result = await state_manager.save_execution_state(sample_execution)
        
        assert result is True
        mock_store.save_execution.assert_called_once_with(sample_execution)
    
    @pytest.mark.asyncio
    async def test_restore_execution_state(self, state_manager, mock_store, sample_execution):
        """実行状態復元のテスト."""
        mock_store.load_execution.return_value = sample_execution
        
        result = await state_manager.restore_execution_state("test-execution")
        
        assert result == sample_execution
        mock_store.load_execution.assert_called_once_with("test-execution")
    
    @pytest.mark.asyncio
    async def test_delete_execution_state(self, state_manager, mock_store):
        """実行状態削除のテスト."""
        mock_store.delete_execution.return_value = True
        
        result = await state_manager.delete_execution_state("test-execution")
        
        assert result is True
        mock_store.delete_execution.assert_called_once_with("test-execution")
    
    @pytest.mark.asyncio
    async def test_get_execution_history(self, state_manager, mock_store):
        """実行履歴取得のテスト."""
        expected_history = [
            {"id": "exec1", "workflow_id": "workflow1", "status": "completed"},
            {"id": "exec2", "workflow_id": "workflow1", "status": "failed"}
        ]
        mock_store.list_executions.return_value = expected_history
        
        result = await state_manager.get_execution_history("workflow1", "completed", 50)
        
        assert result == expected_history
        mock_store.list_executions.assert_called_once_with("workflow1", "completed", 50)
    
    @pytest.mark.asyncio
    async def test_cleanup_old_states(self, state_manager, mock_store):
        """古い状態クリーンアップのテスト."""
        mock_store.cleanup_old_executions.return_value = 5
        
        result = await state_manager.cleanup_old_states(15)
        
        assert result == 5
        mock_store.cleanup_old_executions.assert_called_once_with(15)
    
    @pytest.mark.asyncio
    async def test_get_execution_statistics(self, state_manager, mock_store):
        """実行統計取得のテスト."""
        # モックデータ
        execution_data = [
            {"id": "exec1", "status": "completed", "workflow_id": "workflow1"},
            {"id": "exec2", "status": "failed", "workflow_id": "workflow1"},
            {"id": "exec3", "status": "running", "workflow_id": "workflow2"},
            {"id": "exec4", "status": "completed", "workflow_id": "workflow2"}
        ]
        mock_store.list_executions.return_value = execution_data
        
        stats = await state_manager.get_execution_statistics()
        
        assert stats["total_executions"] == 4
        assert stats["by_status"]["completed"] == 2
        assert stats["by_status"]["failed"] == 1
        assert stats["by_status"]["running"] == 1
        assert stats["by_workflow"]["workflow1"] == 2
        assert stats["by_workflow"]["workflow2"] == 2


@pytest.mark.asyncio
class TestStateStoreIntegration:
    """状態ストアの統合テスト."""
    
    async def test_file_and_memory_store_compatibility(self):
        """ファイルストアとメモリストアの互換性テスト."""
        # 一時ディレクトリ作成
        with tempfile.TemporaryDirectory() as temp_dir:
            file_store = FileStateStore(temp_dir)
            memory_store = MemoryStateStore()
            
            # サンプル実行状態
            execution = WorkflowExecution(
                id="compatibility-test",
                workflow_id="test-workflow",
                status=WorkflowStatus.RUNNING,
                context={"test": "data"},
                mode=ExecutionMode.ASYNC
            )
            
            # 両方のストアに保存
            await file_store.save_execution(execution)
            await memory_store.save_execution(execution)
            
            # 両方から読み込み
            file_loaded = await file_store.load_execution(execution.id)
            memory_loaded = await memory_store.load_execution(execution.id)
            
            # 同じデータが読み込まれることを確認
            assert file_loaded.id == memory_loaded.id
            assert file_loaded.workflow_id == memory_loaded.workflow_id
            assert file_loaded.status == memory_loaded.status
            assert file_loaded.context == memory_loaded.context
            assert file_loaded.mode == memory_loaded.mode
    
    async def test_state_manager_with_different_stores(self):
        """異なるストアでのStateManagerテスト."""
        memory_store = MemoryStateStore()
        memory_manager = StateManager(memory_store)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            file_store = FileStateStore(temp_dir)
            file_manager = StateManager(file_store)
            
            # サンプル実行状態
            execution = WorkflowExecution(
                id="manager-test",
                workflow_id="test-workflow",
                status=WorkflowStatus.RUNNING,
                context={}
            )
            
            # 両方のマネージャーでテスト
            for manager in [memory_manager, file_manager]:
                # 保存
                assert await manager.save_execution_state(execution) is True
                
                # 復元
                restored = await manager.restore_execution_state(execution.id)
                assert restored is not None
                assert restored.id == execution.id
                
                # 削除
                assert await manager.delete_execution_state(execution.id) is True
                
                # 削除後の確認
                assert await manager.restore_execution_state(execution.id) is None 