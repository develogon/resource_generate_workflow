"""チェックポイント管理システム

このモジュールは、処理状態を定期的に保存し、中断時に再開可能にします。
"""

import os
import json
import datetime
from typing import Dict, List, Any, Optional


class Checkpoint:
    """チェックポイント情報"""
    
    def __init__(self, checkpoint_type: str, state: Dict, completed_tasks: List[str] = None, 
                 pending_tasks: List[str] = None):
        """
        チェックポイントの初期化

        Args:
            checkpoint_type: チェックポイントのタイプ（例: "INITIAL", "CHAPTER", "ERROR"）
            state: 保存するシステム状態
            completed_tasks: 完了したタスクID
            pending_tasks: 保留中のタスクID
        """
        self.id = f"checkpoint-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.type = checkpoint_type
        self.timestamp = datetime.datetime.now().isoformat()
        self.state = state
        self.completed_tasks = completed_tasks or []
        self.pending_tasks = pending_tasks or []
    
    def to_dict(self) -> Dict:
        """
        チェックポイントを辞書形式に変換

        Returns:
            Dict: チェックポイントの辞書表現
        """
        return {
            "id": self.id,
            "type": self.type,
            "timestamp": self.timestamp,
            "state": self.state,
            "completed_tasks": self.completed_tasks,
            "pending_tasks": self.pending_tasks
        }


class CheckpointManager:
    """チェックポイント管理システム"""
    
    def __init__(self, checkpoint_dir: str = "checkpoints"):
        """
        初期化

        Args:
            checkpoint_dir: チェックポイントを保存するディレクトリパス
        """
        self.checkpoint_dir = checkpoint_dir
        os.makedirs(checkpoint_dir, exist_ok=True)
    
    def save_checkpoint(self, checkpoint_type: str, state: Dict = None) -> str:
        """
        現在の状態をチェックポイントとして保存

        Args:
            checkpoint_type: チェックポイントのタイプ
            state: 保存する状態情報

        Returns:
            str: 保存されたチェックポイントのID
        """
        state = state or {}
        checkpoint = Checkpoint(checkpoint_type, state)
        checkpoint_id = checkpoint.id
        
        checkpoint_path = os.path.join(self.checkpoint_dir, f"{checkpoint_id}.json")
        with open(checkpoint_path, "w", encoding="utf-8") as f:
            json.dump(checkpoint.to_dict(), f, ensure_ascii=False, indent=2)
        
        return checkpoint_id
    
    def load_checkpoint(self, checkpoint_id: str) -> Optional[Dict]:
        """
        指定されたIDのチェックポイントを読み込む

        Args:
            checkpoint_id: チェックポイントID

        Returns:
            Optional[Dict]: チェックポイントデータ、存在しない場合はNone
        """
        checkpoint_path = os.path.join(self.checkpoint_dir, f"{checkpoint_id}.json")
        if not os.path.exists(checkpoint_path):
            return None
        
        with open(checkpoint_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def load_latest_checkpoint(self) -> Optional[Dict]:
        """
        最新のチェックポイントを読み込み

        Returns:
            Optional[Dict]: 最新のチェックポイントデータ、存在しない場合はNone
        """
        checkpoint_files = [f for f in os.listdir(self.checkpoint_dir) if f.endswith(".json")]
        if not checkpoint_files:
            return None
        
        # ファイル名でソート（チェックポイントIDには日時が含まれているため、これが最新順になる）
        checkpoint_files.sort(reverse=True)
        latest_checkpoint = checkpoint_files[0]
        
        return self.load_checkpoint(latest_checkpoint.replace(".json", ""))
    
    def restore_from_checkpoint(self, checkpoint_id: str) -> bool:
        """
        指定されたチェックポイントから状態を復元

        Args:
            checkpoint_id: チェックポイントID

        Returns:
            bool: 復元が成功した場合はTrue、それ以外はFalse
        """
        checkpoint_data = self.load_checkpoint(checkpoint_id)
        if not checkpoint_data:
            return False
        
        # 実際の復元ロジックはここに実装
        # この実装はシステムのコンテキストによって異なる
        
        return True 