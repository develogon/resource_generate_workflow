"""
コンテンツ処理ワークフローを定義するモジュール。
Template Method パターンで処理フローを標準化し、各段階で必要な処理を定義する。
"""
import os
import time
import logging
from typing import Dict, List, Any, Optional, Union, Callable, Tuple, TypeVar, Generic

# ジェネリック型変数
T = TypeVar('T')


class ContentProcessor:
    """
    コンテンツ処理を担当する基底クラス。
    Template Method パターンを使用して、処理フローを標準化する。
    """

    def __init__(
        self,
        content: Optional[str] = None,
        args: Optional[Any] = None,
        file_manager: Optional[Any] = None,
        claude_service: Optional[Any] = None,
        github_service: Optional[Any] = None,
        storage_service: Optional[Any] = None,
        state_manager: Optional[Any] = None,
        notifier: Optional[Any] = None
    ):
        """
        ContentProcessorを初期化する

        Args:
            content (str, optional): 処理するコンテンツ
            args (Any, optional): コマンドライン引数
            file_manager (Any, optional): ファイル管理サービス
            claude_service (Any, optional): Claude APIサービス
            github_service (Any, optional): GitHub APIサービス
            storage_service (Any, optional): ストレージサービス
            state_manager (Any, optional): 状態管理サービス
            notifier (Any, optional): 通知サービス
        """
        self.content = content
        self.args = args
        self.file_manager = file_manager
        self.claude_service = claude_service
        self.github_service = github_service
        self.storage_service = storage_service
        self.state_manager = state_manager
        self.notifier = notifier
        
        # 処理進捗管理
        self.progress_percentage = 0.0
        
        # 実行タスクのリスト
        self.executables = []
        
        # 処理用のディレクトリパスなど
        self.base_dir = ""
        if args and hasattr(args, 'title'):
            self.base_dir = os.path.join(os.getcwd(), self.args.lang, self.args.title)

    @classmethod
    def from_state(cls, state: Dict[str, Any], **services):
        """
        保存された状態から新しいContentProcessorインスタンスを作成する

        Args:
            state (dict): 保存された状態データ
            **services: 必要なサービスのキーワード引数

        Returns:
            ContentProcessor: 状態から復元されたインスタンス
        """
        # ダミーのArgsオブジェクト作成
        class Args:
            pass
        
        args = Args()
        
        # 状態から引数を復元
        state_data = state.get("data", {})
        for key, value in state_data.items():
            if key in ["title", "lang", "input_path", "resume"]:
                setattr(args, key, value)
        
        # インスタンス作成
        processor = cls(
            args=args,
            **services
        )
        
        # その他の状態を復元
        processor.progress_percentage = state_data.get("progress_percentage", 0.0)
        processor.executables = state_data.get("executables", [])
        
        return processor

    def process(self) -> None:
        """
        コンテンツ処理のメインメソッド。
        Template Method パターンの中心となるメソッド。
        
        処理の流れ:
        1. 前処理 (pre_process)
        2. 主処理 (execute)
        3. 後処理 (post_process)
        
        例外が発生した場合は handle_error で処理される。
        
        Returns:
            None
        """
        try:
            # 前処理
            self.pre_process()
            
            # 主処理
            self.execute()
            
            # 後処理
            self.post_process()
            
        except Exception as e:
            # エラーハンドリング
            self.handle_error(e)

    def pre_process(self) -> None:
        """
        処理前の準備を行う。
        ディレクトリ構造の作成や初期ファイルの生成など。
        
        派生クラスでオーバーライドすることを想定。
        
        Returns:
            None
        """
        # ディレクトリ構造の作成
        structure = {
            "chapters": {},
            "output": {
                "article": {},
                "script": {},
                "images": {}
            }
        }
        
        # ディレクトリ構造の生成
        created_dirs = self.file_manager.create_directory_structure(self.base_dir, structure)
        logging.info(f"ディレクトリ構造を作成しました: {len(created_dirs)}個のディレクトリ")
        
        # チェックポイント保存
        self.save_checkpoint("pre_process_complete")

    def execute(self) -> None:
        """
        主処理を実行する。
        コンテンツ生成、変換、GitHubプッシュなどの中心的な処理。
        
        派生クラスでオーバーライドすることを想定。
        
        Returns:
            None
        """
        total_tasks = len(self.executables)
        completed = 0
        
        # 全ての実行タスクを処理
        for task in self.executables:
            if task.get("completed", False):
                # 既に完了しているタスクはスキップ
                completed += 1
                continue
                
            task_function = task.get("function")
            task_args = task.get("args", {})
            task_name = task.get("name", "不明なタスク")
            
            try:
                # タスク実行
                logging.info(f"タスク実行: {task_name}")
                result = task_function(**task_args)
                
                # タスク完了としてマーク
                task["completed"] = True
                task["result"] = result
                
                # 進捗更新
                completed += 1
                self.progress_percentage = (completed / total_tasks) * 100
                
                # 進捗通知
                if self.notifier:
                    self.notifier.send_progress(
                        f"{self.args.title} の処理中: {task_name}が完了しました。", 
                        self.progress_percentage
                    )
                
                # チェックポイント保存
                self.save_checkpoint(f"task_complete_{task_name}")
                
            except Exception as e:
                # タスク失敗時はエラーハンドラに処理を委譲
                logging.error(f"タスク実行エラー: {task_name} - {str(e)}")
                task["error"] = str(e)
                raise e
        
        # 全タスク完了
        self.progress_percentage = 100.0
        logging.info(f"全てのタスクが完了しました: {total_tasks}タスク")

    def post_process(self) -> None:
        """
        処理後の後始末を行う。
        一時ファイルの削除や最終通知など。
        
        派生クラスでオーバーライドすることを想定。
        
        Returns:
            None
        """
        # 処理完了通知
        if self.notifier:
            self.notifier.send_success(f"{self.args.title} の処理が完了しました。")
        
        logging.info(f"処理が完了しました: {self.args.title}")

    def handle_error(self, error: Exception) -> None:
        """
        エラー処理と復旧ロジックを実行する。
        
        Args:
            error (Exception): 発生したエラー
        
        Returns:
            None
        """
        # エラーログ出力
        logging.error(f"エラーが発生しました: {type(error).__name__} - {str(error)}")
        
        # チェックポイント保存
        checkpoint_id = self.save_checkpoint(f"error_{type(error).__name__}")
        
        # エラー通知
        if self.notifier:
            error_message = f"エラー発生: {type(error).__name__} - {str(error)}"
            recovery_message = f"チェックポイント {checkpoint_id} が作成されました。--resume {checkpoint_id} で再開できます。"
            self.notifier.send_error(error_message, recovery_message)

    def save_checkpoint(self, step_name: str = "checkpoint") -> str:
        """
        現在の処理状態のチェックポイントを保存する。
        
        Args:
            step_name (str, optional): チェックポイントのステップ名
        
        Returns:
            str: 生成されたチェックポイントID
        """
        # 状態データ構築
        state_data = {
            "step": step_name,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "processor_class": self.__class__.__name__,
            "data": {
                "title": self.args.title if hasattr(self.args, 'title') else None,
                "lang": self.args.lang if hasattr(self.args, 'lang') else None,
                "progress_percentage": self.progress_percentage,
                "executables": self.executables
            }
        }
        
        # 状態保存
        process_id = f"{self.args.lang}_{self.args.title}" if hasattr(self.args, 'title') else "process"
        checkpoint_id = self.state_manager.save_state(process_id, state_data)
        
        # チェックポイント通知
        if self.notifier:
            self.notifier.send_checkpoint_notification(
                f"{step_name}のチェックポイントが作成されました: {checkpoint_id}"
            )
        
        logging.info(f"チェックポイント保存: {step_name} - {checkpoint_id}")
        return checkpoint_id

    def chunk_processor(self, items: List[T], processor_func: Callable[[List[T]], Any], chunk_size: int = 5) -> List[Any]:
        """
        アイテムのリストをチャンクに分割して処理する
        
        Args:
            items (list): 処理するアイテムのリスト
            processor_func (callable): チャンクを受け取って処理する関数
            chunk_size (int, optional): チャンクサイズ。デフォルト5。
        
        Returns:
            list: 各チャンクの処理結果のリスト
        """
        results = []
        
        # チャンクに分割して処理
        for i in range(0, len(items), chunk_size):
            chunk = items[i:i+chunk_size]
            result = processor_func(chunk)
            results.append(result)
        
        return results 