"""ワークフローエンジン

このモジュールは、システム全体を制御し、実行フローを管理します。
コンテンツプロセッサ、ジェネレータシステム、タスク管理システム、チェックポイント管理を連携させます。
"""

import os
import logging
from typing import Dict, Any, Optional, List

from app.workflow.task_manager import TaskManager, TaskType
from app.workflow.checkpoint import CheckpointManager

# ロガーの設定
logger = logging.getLogger(__name__)


class WorkflowEngine:
    """ワークフローエンジン"""
    
    def __init__(self, config: Dict = None):
        """
        初期化

        Args:
            config: 設定情報
        """
        self.config = config or {}
        self.task_manager = TaskManager()
        self.checkpoint_manager = CheckpointManager(
            checkpoint_dir=self.config.get("checkpoint_dir", "checkpoints")
        )
    
    def start(self, input_path: str) -> bool:
        """
        ワークフローを開始する

        Args:
            input_path: 入力ファイルパス

        Returns:
            bool: 開始が成功した場合はTrue、それ以外はFalse
        """
        try:
            logger.info(f"ワークフローを開始します: {input_path}")
            
            # 入力ファイルの存在確認
            if not os.path.exists(input_path):
                logger.error(f"入力ファイルが見つかりません: {input_path}")
                return False
            
            # 初期タスクの登録
            self._register_initial_tasks(input_path)
            
            # 初期チェックポイントの保存
            initial_state = {
                "input_path": input_path,
                "stage": "INITIALIZED"
            }
            self.checkpoint_manager.save_checkpoint("INITIAL", initial_state)
            
            # タスク実行ループを開始
            return self.execute_task_loop()
            
        except Exception as e:
            logger.exception(f"ワークフロー開始中にエラーが発生しました: {str(e)}")
            self.handle_error(e, {"input_path": input_path})
            return False
    
    def resume(self, checkpoint_id: str = None) -> bool:
        """
        チェックポイントからワークフローを再開する

        Args:
            checkpoint_id: 再開するチェックポイントID（指定がない場合は最新のチェックポイント）

        Returns:
            bool: 再開が成功した場合はTrue、それ以外はFalse
        """
        try:
            # チェックポイントの読み込み
            if checkpoint_id:
                logger.info(f"チェックポイントからワークフローを再開します: {checkpoint_id}")
                checkpoint_data = self.checkpoint_manager.load_checkpoint(checkpoint_id)
            else:
                logger.info("最新のチェックポイントからワークフローを再開します")
                checkpoint_data = self.checkpoint_manager.load_latest_checkpoint()
            
            if not checkpoint_data:
                logger.error("再開可能なチェックポイントが見つかりません")
                return False
            
            # チェックポイントからの復元
            result = self.checkpoint_manager.restore_from_checkpoint(checkpoint_data["id"])
            if not result:
                logger.error("チェックポイントからの復元に失敗しました")
                return False
            
            # タスク実行ループを再開
            return self.execute_task_loop()
            
        except Exception as e:
            logger.exception(f"ワークフロー再開中にエラーが発生しました: {str(e)}")
            self.handle_error(e, {"checkpoint_id": checkpoint_id})
            return False
    
    def execute_task_loop(self) -> bool:
        """
        タスク実行ループ

        Returns:
            bool: すべてのタスクが正常に実行された場合はTrue、それ以外はFalse
        """
        try:
            while True:
                # 次の実行可能タスクを取得
                task = self.task_manager.get_next_executable_task()
                if not task:
                    logger.info("実行可能なタスクがありません。ワークフローを終了します。")
                    break
                
                # タスクを実行
                logger.info(f"タスク実行: {task['id']} ({task['type']})")
                try:
                    # タスクタイプに応じた処理を実行
                    result = self._execute_task(task)
                    
                    # タスクを完了としてマーク
                    self.task_manager.mark_as_completed(task["id"], result)
                    
                    # チェックポイントを保存
                    state = {
                        "last_completed_task": task["id"],
                        "task_type": task["type"]
                    }
                    self.checkpoint_manager.save_checkpoint("TASK", state)
                    
                except Exception as e:
                    logger.exception(f"タスク実行中にエラーが発生しました: {str(e)}")
                    self.task_manager.mark_as_failed(task["id"], e)
                    
                    # 再試行可能な場合は再試行
                    if self.task_manager.retry_task(task["id"]):
                        logger.info(f"タスクを再試行します: {task['id']}")
                    else:
                        # エラー処理
                        logger.error(f"タスクの再試行回数が上限に達しました: {task['id']}")
                        self.handle_error(e, {"task_id": task["id"]})
                        return False
            
            logger.info("ワークフローが正常に完了しました")
            return True
            
        except Exception as e:
            logger.exception(f"タスク実行ループ中にエラーが発生しました: {str(e)}")
            self.handle_error(e, {})
            return False
    
    def handle_error(self, error: Exception, context: Dict) -> bool:
        """
        エラー処理

        Args:
            error: 発生したエラー
            context: エラーコンテキスト情報

        Returns:
            bool: エラー処理が成功した場合はTrue、それ以外はFalse
        """
        try:
            logger.error(f"エラーハンドリング: {str(error)}")
            
            # エラーチェックポイントの保存
            error_state = {
                "error": str(error),
                "context": context
            }
            self.checkpoint_manager.save_checkpoint("ERROR", error_state)
            
            # エラー通知の送信
            # 実際の実装では、Slack通知などを行う
            
            return False
            
        except Exception as e:
            logger.exception(f"エラー処理中に例外が発生しました: {str(e)}")
            return False
    
    def _register_initial_tasks(self, input_path: str) -> None:
        """
        初期タスクを登録する

        Args:
            input_path: 入力ファイルパス
        """
        # チャプター分割タスク
        self.task_manager.register_task({
            "type": TaskType.FILE_OPERATION,
            "params": {
                "operation": "SPLIT_CHAPTERS",
                "input_path": input_path
            }
        })
    
    def _execute_task(self, task: Dict) -> Any:
        """
        タスクを実行する

        Args:
            task: 実行するタスク情報

        Returns:
            Any: タスク実行結果
        """
        # タスクタイプに応じた処理を実行
        # 実際の実装では、タスクタイプに応じて対応するハンドラを呼び出す
        
        # この実装は仮のもので、実際には各タスクタイプに応じた処理が必要
        task_type = task["type"]
        params = task["params"]
        
        if task_type == "FILE_OPERATION":
            # ファイル操作の実行
            return {"success": True, "message": f"ファイル操作を実行: {params}"}
            
        elif task_type == "API_CALL":
            # API呼び出しの実行
            return {"success": True, "message": f"API呼び出しを実行: {params}"}
            
        elif task_type == "GITHUB_OPERATION":
            # GitHub操作の実行
            return {"success": True, "message": f"GitHub操作を実行: {params}"}
            
        elif task_type == "S3_OPERATION":
            # S3操作の実行
            return {"success": True, "message": f"S3操作を実行: {params}"}
            
        elif task_type == "IMAGE_PROCESSING":
            # 画像処理の実行
            return {"success": True, "message": f"画像処理を実行: {params}"}
            
        else:
            raise ValueError(f"未知のタスクタイプ: {task_type}") 