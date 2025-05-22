import pytest
import os
import json
import datetime
from unittest.mock import patch, MagicMock, mock_open

# テスト対象のモジュールをインポート
from app.workflow.checkpoint import CheckpointManager, Checkpoint

class TestCheckpointManager:
    """チェックポイント管理システムのテストクラス"""
    
    @pytest.fixture
    def checkpoint_manager(self, tmp_path):
        """テスト用のチェックポイント管理インスタンスを作成"""
        checkpoint_dir = tmp_path / "checkpoints"
        checkpoint_dir.mkdir()
        return CheckpointManager(checkpoint_dir=str(checkpoint_dir))
    
    def test_save_checkpoint(self, checkpoint_manager, sample_checkpoint_data):
        """チェックポイント保存のテスト"""
        # チェックポイントを保存
        state = sample_checkpoint_data["state"]
        checkpoint_id = checkpoint_manager.save_checkpoint("TEST", state)
        
        # チェックポイントIDが返されることを確認
        assert checkpoint_id is not None
        assert isinstance(checkpoint_id, str)
        
        # チェックポイントファイルが作成されていることを確認
        checkpoint_file = os.path.join(checkpoint_manager.checkpoint_dir, f"{checkpoint_id}.json")
        assert os.path.exists(checkpoint_file)
        
        # ファイルの内容を確認
        with open(checkpoint_file, "r") as f:
            data = json.load(f)
            assert data["id"] == checkpoint_id
            assert data["type"] == "TEST"
            assert data["state"] == state
    
    def test_load_checkpoint(self, checkpoint_manager, sample_checkpoint_data):
        """チェックポイント読込のテスト"""
        # チェックポイントを保存
        state = sample_checkpoint_data["state"]
        checkpoint_id = checkpoint_manager.save_checkpoint("TEST", state)
        
        # チェックポイントを読み込み
        checkpoint = checkpoint_manager.load_checkpoint(checkpoint_id)
        
        # チェックポイントが正しく読み込まれることを確認
        assert checkpoint is not None
        assert checkpoint["id"] == checkpoint_id
        assert checkpoint["type"] == "TEST"
        assert checkpoint["state"] == state
    
    @patch("os.listdir")
    def test_load_latest_checkpoint(self, mock_listdir, checkpoint_manager, sample_checkpoint_data):
        """最新のチェックポイント読込のテスト"""
        # チェックポイントを複数保存
        state1 = {"current_task": "task-001"}
        state2 = {"current_task": "task-002"}
        checkpoint_id1 = checkpoint_manager.save_checkpoint("TEST", state1)
        checkpoint_id2 = checkpoint_manager.save_checkpoint("TEST", state2)
        
        # リストディレクトリのモックを設定
        mock_listdir.return_value = [f"{checkpoint_id1}.json", f"{checkpoint_id2}.json"]
        
        # 最新のチェックポイントを読み込み
        checkpoint = checkpoint_manager.load_latest_checkpoint()
        
        # チェックポイントが正しく読み込まれることを確認
        assert checkpoint is not None
        assert "id" in checkpoint
        assert "timestamp" in checkpoint
        assert "state" in checkpoint
    
    def test_restore_from_checkpoint(self, checkpoint_manager, sample_checkpoint_data):
        """チェックポイントからの復元テスト"""
        # チェックポイントを保存
        state = sample_checkpoint_data["state"]
        checkpoint_id = checkpoint_manager.save_checkpoint("TEST", state)
        
        # チェックポイントから復元
        with patch.object(checkpoint_manager, "load_checkpoint", return_value=sample_checkpoint_data):
            result = checkpoint_manager.restore_from_checkpoint(checkpoint_id)
            
            # 復元が成功することを確認
            assert result is True
    
    def test_checkpoint_data_integrity(self, checkpoint_manager, sample_checkpoint_data):
        """チェックポイントデータの整合性テスト"""
        # チェックポイントを保存
        state = sample_checkpoint_data["state"]
        checkpoint_id = checkpoint_manager.save_checkpoint("TEST", state)
        
        # チェックポイントを読み込み
        loaded_checkpoint = checkpoint_manager.load_checkpoint(checkpoint_id)
        
        # データの整合性を確認
        assert loaded_checkpoint["state"] == state
        assert loaded_checkpoint["id"] == checkpoint_id
        assert "timestamp" in loaded_checkpoint
    
    def test_no_checkpoint_found(self, checkpoint_manager):
        """チェックポイントが見つからない場合のテスト"""
        # 存在しないチェックポイントの読み込みを試行
        result = checkpoint_manager.load_checkpoint("non-existent")
        
        # Noneが返されることを確認
        assert result is None 