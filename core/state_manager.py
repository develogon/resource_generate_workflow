"""
処理状態の管理とチェックポイント機能を提供するモジュール。
処理の中断・再開をサポートし、エラー発生時に自動的にチェックポイントを作成する。
"""
import os
import json
import uuid
import datetime
import importlib
import glob
from typing import Dict, List, Any, Optional, Union


class StateManager:
    """
    処理状態の管理とチェックポイントを担当するクラス。
    Memento パターンにより、状態の保存と復元を実現する。
    """

    def __init__(self, checkpoint_dir: Optional[str] = None):
        """
        StateManagerを初期化する

        Args:
            checkpoint_dir (str, optional): チェックポイントを保存するディレクトリ
                省略時はカレントディレクトリの下に '.checkpoints' ディレクトリを作成
        """
        if checkpoint_dir is None:
            self.checkpoint_dir = os.path.join(os.getcwd(), '.checkpoints')
        else:
            self.checkpoint_dir = checkpoint_dir
        
        # チェックポイントディレクトリがなければ作成
        if not os.path.exists(self.checkpoint_dir):
            os.makedirs(self.checkpoint_dir)

    def save_state(self, process_id: str, state_data: Dict[str, Any]) -> str:
        """
        処理状態を保存する

        Args:
            process_id (str): 処理を識別するID
            state_data (dict): 保存する状態データ

        Returns:
            str: 生成されたチェックポイントID
        """
        # チェックポイントIDを生成
        checkpoint_id = f"{process_id}_{uuid.uuid4().hex[:8]}"
        
        # 現在のタイムスタンプを追加
        timestamp = datetime.datetime.now().isoformat()
        
        # チェックポイントデータを構成
        checkpoint_data = {
            "process_id": process_id,
            "state": state_data,
            "timestamp": timestamp
        }
        
        # JSONファイルに保存
        checkpoint_file = os.path.join(self.checkpoint_dir, f"{checkpoint_id}.json")
        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)
        
        return checkpoint_id

    def load_state(self, checkpoint_id: str) -> Dict[str, Any]:
        """
        チェックポイントから状態を読み込む

        Args:
            checkpoint_id (str): チェックポイントID

        Returns:
            dict: 読み込まれた状態データ

        Raises:
            FileNotFoundError: チェックポイントファイルが存在しない場合
            ValueError: チェックポイントデータが無効な場合
        """
        checkpoint_file = os.path.join(self.checkpoint_dir, f"{checkpoint_id}.json")
        
        if not os.path.exists(checkpoint_file):
            raise FileNotFoundError(f"チェックポイントファイル {checkpoint_file} が見つかりません")
        
        try:
            with open(checkpoint_file, 'r', encoding='utf-8') as f:
                checkpoint_data = json.load(f)
            
            if "state" not in checkpoint_data:
                raise ValueError(f"チェックポイントデータに 'state' が含まれていません: {checkpoint_id}")
            
            return checkpoint_data["state"]
        except json.JSONDecodeError:
            raise ValueError(f"チェックポイントファイルの形式が無効です: {checkpoint_id}")

    def list_checkpoints(self) -> List[Dict[str, Any]]:
        """
        利用可能なすべてのチェックポイント一覧を取得する

        Returns:
            list: チェックポイント情報のリスト (各チェックポイントはID、プロセスID、タイムスタンプなどを含む)
        """
        checkpoints = []
        
        # チェックポイントディレクトリ内のすべてのJSONファイルを検索
        checkpoint_files = glob.glob(os.path.join(self.checkpoint_dir, "*.json"))
        
        for checkpoint_file in checkpoint_files:
            try:
                # ファイル名からチェックポイントIDを抽出
                checkpoint_id = os.path.splitext(os.path.basename(checkpoint_file))[0]
                
                # チェックポイントデータを読み込み
                with open(checkpoint_file, 'r', encoding='utf-8') as f:
                    checkpoint_data = json.load(f)
                
                # 最低限必要な情報のみを抽出
                checkpoint_info = {
                    "id": checkpoint_id,
                    "process_id": checkpoint_data.get("process_id", "unknown"),
                    "timestamp": checkpoint_data.get("timestamp", "unknown"),
                    "step": checkpoint_data.get("state", {}).get("step", "unknown")
                }
                
                checkpoints.append(checkpoint_info)
            except (json.JSONDecodeError, IOError) as e:
                # エラーが発生した場合はそのチェックポイントをスキップ
                continue
        
        # タイムスタンプの新しい順にソート
        checkpoints.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return checkpoints

    def resume_from_checkpoint(self, checkpoint_id: str) -> Any:
        """
        チェックポイントから処理を再開する

        Args:
            checkpoint_id (str): 再開するチェックポイントID

        Returns:
            Any: 再初期化されたプロセッサインスタンス

        Raises:
            ValueError: プロセッサクラスが見つからない、またはインスタンス化できない場合
        """
        # チェックポイントから状態を読み込む
        state = self.load_state(checkpoint_id)
        
        if "processor_class" not in state:
            raise ValueError(f"チェックポイントに 'processor_class' が含まれていません: {checkpoint_id}")
        
        processor_class_name = state["processor_class"]
        module_name = "core.processor"  # デフォルトのモジュール名
        
        if "." in processor_class_name:
            # モジュール名とクラス名が明示的に指定されている場合
            module_name, processor_class_name = processor_class_name.rsplit(".", 1)
        
        try:
            # モジュールをインポート
            module = importlib.import_module(module_name)
            
            # プロセッサクラスを取得
            processor_class = getattr(module, processor_class_name)
            
            # プロセッサインスタンスを作成して状態を設定
            processor = processor_class(state=state)
            
            return processor
        except (ImportError, AttributeError) as e:
            raise ValueError(f"プロセッサクラス '{processor_class_name}' をロードできません: {str(e)}")

    def cleanup_old_checkpoints(self, days: int = 7) -> int:
        """
        指定日数より古いチェックポイントを削除する

        Args:
            days (int): 保持する日数の閾値 (デフォルト: 7日)

        Returns:
            int: 削除したチェックポイントの数
        """
        # 削除基準日時を計算
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)
        deleted_count = 0
        
        # チェックポイント一覧を取得
        checkpoints = self.list_checkpoints()
        
        for checkpoint in checkpoints:
            try:
                # タイムスタンプをdatetimeオブジェクトに変換
                timestamp = datetime.datetime.fromisoformat(checkpoint["timestamp"])
                
                # 基準日時より古い場合は削除
                if timestamp < cutoff_date:
                    checkpoint_file = os.path.join(self.checkpoint_dir, f"{checkpoint['id']}.json")
                    os.remove(checkpoint_file)
                    deleted_count += 1
            except (ValueError, IOError) as e:
                # 日付の変換エラーまたはファイル削除エラーの場合はスキップ
                continue
        
        return deleted_count

    def list_checkpoints_for_title(self, title: str) -> List[Dict[str, Any]]:
        """
        特定のタイトルに関連するチェックポイント一覧を取得する

        Args:
            title (str): フィルタリングするタイトル

        Returns:
            list: タイトルに関連するチェックポイント情報のリスト
        """
        all_checkpoints = self.list_checkpoints()
        
        # タイトルに関連するチェックポイントをフィルタリング
        title_checkpoints = []
        for checkpoint in all_checkpoints:
            # プロセスIDにタイトルが含まれている場合や、
            # 状態データ内のタイトル情報が一致する場合に選択
            process_id = checkpoint.get("process_id", "")
            if title.lower() in process_id.lower():
                title_checkpoints.append(checkpoint)
            
            # 必要に応じて、状態データの詳細も検査することも可能
        
        return title_checkpoints 