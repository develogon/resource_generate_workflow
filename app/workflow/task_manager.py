"""タスク管理システム

このモジュールは、非同期タスクの登録、実行、進捗管理を担当します。
タスクキューを使用して処理を順序付けし、エラー発生時の再試行やスキップなどを制御します。
"""

from enum import Enum
from typing import List, Dict, Any, Optional


class TaskStatus(Enum):
    """タスクの状態を表す列挙型"""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class TaskType(Enum):
    """タスクの種類を表す列挙型"""
    FILE_OPERATION = "FILE_OPERATION"
    API_CALL = "API_CALL"
    GITHUB_OPERATION = "GITHUB_OPERATION"
    S3_OPERATION = "S3_OPERATION"
    IMAGE_PROCESSING = "IMAGE_PROCESSING"


class Task:
    """タスクの基本単位"""
    
    def __init__(self, task_type: TaskType, params: Dict, dependencies: List[str] = None, 
                 max_retries: int = 3):
        """
        タスクの初期化

        Args:
            task_type: タスクのタイプ
            params: タスク実行パラメータ
            dependencies: 依存するタスクID
            max_retries: 最大再試行回数
        """
        self.id = None  # 登録時に設定される
        self.type = task_type
        self.status = TaskStatus.PENDING
        self.dependencies = dependencies or []
        self.retry_count = 0
        self.max_retries = max_retries
        self.params = params
        self.result = None
        self.error = None


class TaskManager:
    """タスク管理システム"""
    
    def __init__(self):
        """初期化"""
        self.tasks = {}  # タスクIDからタスクオブジェクトへのマッピング
        self.task_counter = 0
    
    def register_task(self, task: Dict) -> str:
        """
        新しいタスクを登録

        Args:
            task: タスク情報を含む辞書または Task オブジェクト

        Returns:
            str: 登録されたタスクのID
        """
        if isinstance(task, Dict):
            task_obj = Task(
                task_type=task.get("type"),
                params=task.get("params", {}),
                dependencies=task.get("dependencies", []),
                max_retries=task.get("max_retries", 3)
            )
        else:
            task_obj = task
        
        self.task_counter += 1
        task_id = f"task-{self.task_counter:03d}"
        task_obj.id = task_id
        self.tasks[task_id] = task_obj
        
        return task_id
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """
        タスクIDからタスクを取得

        Args:
            task_id: タスクID

        Returns:
            Optional[Task]: タスクオブジェクト（存在しない場合はNone）
        """
        return self.tasks.get(task_id)
    
    def get_all_tasks(self) -> List[Task]:
        """
        すべてのタスクを取得

        Returns:
            List[Task]: タスクのリスト
        """
        return list(self.tasks.values())
    
    def get_next_executable_task(self) -> Optional[Dict]:
        """
        実行可能な次のタスクを取得

        Returns:
            Optional[Dict]: 実行可能なタスク（辞書形式）、実行可能なタスクがない場合はNone
        """
        for task in self.tasks.values():
            # 保留中のタスクのみを対象とする
            if task.status != TaskStatus.PENDING:
                continue
            
            # すべての依存タスクが完了しているか確認
            dependencies_completed = True
            for dep_id in task.dependencies:
                dep_task = self.tasks.get(dep_id)
                if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                    dependencies_completed = False
                    break
            
            if dependencies_completed:
                return {
                    "id": task.id,
                    "type": task.type.value,
                    "status": task.status.value,
                    "params": task.params
                }
        
        return None
    
    def mark_as_completed(self, task_id: str, result: Any = None) -> None:
        """
        タスクを完了としてマーク

        Args:
            task_id: タスクID
            result: タスク実行結果
        """
        task = self.tasks.get(task_id)
        if task:
            task.status = TaskStatus.COMPLETED
            task.result = result
    
    def mark_as_failed(self, task_id: str, error: Exception) -> None:
        """
        タスクを失敗としてマーク

        Args:
            task_id: タスクID
            error: エラー情報
        """
        task = self.tasks.get(task_id)
        if task:
            task.status = TaskStatus.FAILED
            task.error = str(error)
    
    def retry_task(self, task_id: str) -> bool:
        """
        タスクの再試行

        Args:
            task_id: タスクID

        Returns:
            bool: 再試行が可能な場合はTrue、それ以外はFalse
        """
        task = self.tasks.get(task_id)
        if not task:
            return False
        
        if task.retry_count >= task.max_retries:
            return False
        
        task.retry_count += 1
        task.status = TaskStatus.PENDING
        task.error = None
        
        return True 