import os
import json
import pytest
from unittest.mock import patch, mock_open, MagicMock
import datetime

from core.state_manager import StateManager


class TestStateManager:
    """状態管理のテストクラス"""

    def test_save_state(self, temp_dir):
        """状態保存のテスト"""
        state_manager = StateManager(checkpoint_dir=str(temp_dir))
        process_id = "test_process"
        state_data = {
            "step": "test_step",
            "data": {
                "key1": "value1",
                "key2": 42
            },
            "timestamp": "2023-01-01T12:00:00"
        }
        
        # 状態保存
        checkpoint_id = state_manager.save_state(process_id, state_data)
        
        # checkpoint_idが文字列であることを確認
        assert isinstance(checkpoint_id, str)
        assert len(checkpoint_id) > 0
        
        # チェックポイントファイルが作成されたことを確認
        checkpoint_file = os.path.join(str(temp_dir), f"{checkpoint_id}.json")
        assert os.path.exists(checkpoint_file)
        
        # 保存された内容を検証
        with open(checkpoint_file, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
            assert saved_data["process_id"] == process_id
            assert saved_data["state"]["step"] == "test_step"
            assert saved_data["state"]["data"]["key1"] == "value1"
            assert saved_data["state"]["data"]["key2"] == 42

    def test_load_state(self, temp_dir):
        """状態読み込みのテスト"""
        state_manager = StateManager(checkpoint_dir=str(temp_dir))
        checkpoint_id = "test_checkpoint"
        process_id = "test_process"
        
        # テストチェックポイントファイルの作成
        state_data = {
            "process_id": process_id,
            "state": {
                "step": "test_step",
                "data": {"key": "value"}
            },
            "timestamp": "2023-01-01T12:00:00"
        }
        
        checkpoint_file = os.path.join(str(temp_dir), f"{checkpoint_id}.json")
        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(state_data, f)
        
        # 状態読み込み
        loaded_state = state_manager.load_state(checkpoint_id)
        
        # 読み込まれた状態を検証
        assert loaded_state["step"] == "test_step"
        assert loaded_state["data"]["key"] == "value"

    def test_list_checkpoints(self, temp_dir):
        """チェックポイント一覧取得のテスト"""
        state_manager = StateManager(checkpoint_dir=str(temp_dir))
        
        # テストチェックポイントファイルの作成
        for i in range(3):
            checkpoint_file = os.path.join(str(temp_dir), f"checkpoint_{i}.json")
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "process_id": f"process_{i}",
                    "state": {"step": f"step_{i}"},
                    "timestamp": f"2023-01-0{i+1}T12:00:00"
                }, f)
        
        # チェックポイント一覧取得
        checkpoints = state_manager.list_checkpoints()
        
        # チェックポイント数の検証
        assert len(checkpoints) == 3
        
        # チェックポイント情報の検証
        for i, cp in enumerate(sorted(checkpoints, key=lambda x: x["id"])):
            assert cp["id"] == f"checkpoint_{i}"
            assert cp["process_id"] == f"process_{i}"
            assert cp["timestamp"].startswith("2023-01-0")

    def test_resume_from_checkpoint(self, temp_dir):
        """チェックポイントからの再開テスト"""
        state_manager = StateManager(checkpoint_dir=str(temp_dir))
        
        # テストチェックポイントファイルの作成
        checkpoint_id = "test_checkpoint"
        process_id = "test_process"
        state_data = {
            "process_id": process_id,
            "state": {
                "step": "test_step",
                "data": {"key": "value"},
                "processor_class": "TestProcessor"
            },
            "timestamp": "2023-01-01T12:00:00"
        }
        
        checkpoint_file = os.path.join(str(temp_dir), f"{checkpoint_id}.json")
        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(state_data, f)
        
        # モックプロセッサクラス
        mock_processor = MagicMock()
        
        # プロセッサクラスのインポートをモック
        with patch('importlib.import_module') as mock_import:
            mock_module = MagicMock()
            mock_module.TestProcessor.return_value = mock_processor
            mock_import.return_value = mock_module
            
            # チェックポイントからの再開
            result = state_manager.resume_from_checkpoint(checkpoint_id)
            
            # 結果の検証
            assert result == mock_processor
            
            # プロセッサインスタンス化時にstateが渡されたことを確認
            mock_module.TestProcessor.assert_called_once()
            call_args = mock_module.TestProcessor.call_args[1]
            assert "state" in call_args
            assert call_args["state"]["step"] == "test_step"
            assert call_args["state"]["data"]["key"] == "value"

    def test_cleanup_old_checkpoints(self, temp_dir):
        """古いチェックポイントのクリーンアップテスト"""
        state_manager = StateManager(checkpoint_dir=str(temp_dir))
        
        # 現在の日時
        now = datetime.datetime.now()
        
        # 新しいチェックポイント (3日前)
        recent_date = (now - datetime.timedelta(days=3)).isoformat()
        recent_file = os.path.join(str(temp_dir), "recent.json")
        with open(recent_file, 'w', encoding='utf-8') as f:
            json.dump({
                "process_id": "recent_process",
                "state": {"step": "recent_step"},
                "timestamp": recent_date
            }, f)
        
        # 古いチェックポイント (10日前)
        old_date = (now - datetime.timedelta(days=10)).isoformat()
        old_file = os.path.join(str(temp_dir), "old.json")
        with open(old_file, 'w', encoding='utf-8') as f:
            json.dump({
                "process_id": "old_process",
                "state": {"step": "old_step"},
                "timestamp": old_date
            }, f)
        
        # 7日より古いチェックポイントをクリーンアップ
        state_manager.cleanup_old_checkpoints(days=7)
        
        # 新しいチェックポイントは残り、古いチェックポイントは削除されたことを確認
        assert os.path.exists(recent_file)
        assert not os.path.exists(old_file) 