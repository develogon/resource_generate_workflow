"""
分散状態管理システム - StateManager

このモジュールはワークフローの状態管理を担当します：
- ワークフロー状態の永続化
- チェックポイント機能
- 障害時の状態復旧
- 分散環境での状態同期
"""

import json
import time
import logging
import asyncio
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class WorkflowStatus(Enum):
    """ワークフローステータス"""
    INITIALIZED = "initialized"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class WorkflowState:
    """ワークフロー状態データ構造"""
    workflow_id: str
    status: WorkflowStatus
    lang: str
    title: str
    created_at: float
    updated_at: float
    metadata: Dict[str, Any]
    progress: Dict[str, Any]
    completed_tasks: Set[str]
    failed_tasks: Set[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        data = asdict(self)
        data['status'] = self.status.value
        data['completed_tasks'] = list(self.completed_tasks)
        data['failed_tasks'] = list(self.failed_tasks)
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowState':
        """辞書から復元"""
        data['status'] = WorkflowStatus(data['status'])
        data['completed_tasks'] = set(data.get('completed_tasks', []))
        data['failed_tasks'] = set(data.get('failed_tasks', []))
        return cls(**data)


@dataclass
class Checkpoint:
    """チェックポイントデータ構造"""
    checkpoint_id: str
    workflow_id: str
    checkpoint_type: str
    timestamp: float
    data: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Checkpoint':
        """辞書から復元"""
        return cls(**data)


class StateManager:
    """分散状態管理システム
    
    ワークフローの状態を永続化し、障害時の復旧を可能にする。
    ローカルキャッシュとリモートストレージの両方をサポート。
    """
    
    def __init__(self, storage_backend: str = "memory", redis_url: Optional[str] = None):
        self.storage_backend = storage_backend
        self.redis_url = redis_url
        
        # ローカルキャッシュ
        self._workflow_states: Dict[str, WorkflowState] = {}
        self._checkpoints: Dict[str, List[Checkpoint]] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        
        # Redis接続（オプション）
        self._redis = None
        
        # 設定
        self.state_ttl = 86400  # 24時間
        self.checkpoint_limit = 100
        
    async def initialize(self) -> None:
        """StateManagerの初期化"""
        if self.storage_backend == "redis" and self.redis_url:
            try:
                import aioredis
                self._redis = await aioredis.from_url(self.redis_url)
                logger.info("Connected to Redis for state management")
            except ImportError:
                logger.warning("aioredis not available, falling back to memory storage")
                self.storage_backend = "memory"
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                self.storage_backend = "memory"
                
        logger.info(f"StateManager initialized with {self.storage_backend} storage")
    
    async def close(self) -> None:
        """StateManagerのクリーンアップ"""
        if self._redis:
            await self._redis.close()
            logger.info("Redis connection closed")
    
    async def create_workflow(self, workflow_id: str, lang: str, title: str, 
                            metadata: Optional[Dict[str, Any]] = None) -> WorkflowState:
        """新しいワークフローを作成"""
        async with self._get_lock(workflow_id):
            # 既存ワークフローチェック
            existing_state = await self.get_workflow_state(workflow_id)
            if existing_state:
                raise ValueError(f"Workflow {workflow_id} already exists")
            
            # 新しい状態を作成
            now = time.time()
            state = WorkflowState(
                workflow_id=workflow_id,
                status=WorkflowStatus.INITIALIZED,
                lang=lang,
                title=title,
                created_at=now,
                updated_at=now,
                metadata=metadata or {},
                progress={},
                completed_tasks=set(),
                failed_tasks=set()
            )
            
            # 状態を保存
            await self._save_workflow_state(state)
            
            logger.info(f"Created workflow {workflow_id}")
            return state
    
    async def get_workflow_state(self, workflow_id: str) -> Optional[WorkflowState]:
        """ワークフロー状態を取得"""
        # ローカルキャッシュを最初にチェック
        if workflow_id in self._workflow_states:
            return self._workflow_states[workflow_id]
        
        # リモートストレージから取得
        state = await self._load_workflow_state(workflow_id)
        if state:
            self._workflow_states[workflow_id] = state
        
        return state
    
    async def update_workflow_state(self, workflow_id: str, 
                                  status: Optional[WorkflowStatus] = None,
                                  metadata: Optional[Dict[str, Any]] = None,
                                  progress: Optional[Dict[str, Any]] = None) -> WorkflowState:
        """ワークフロー状態を更新"""
        async with self._get_lock(workflow_id):
            state = await self.get_workflow_state(workflow_id)
            if not state:
                raise ValueError(f"Workflow {workflow_id} not found")
            
            # 状態を更新
            if status is not None:
                state.status = status
            if metadata is not None:
                state.metadata.update(metadata)
            if progress is not None:
                state.progress.update(progress)
            
            state.updated_at = time.time()
            
            # 保存
            await self._save_workflow_state(state)
            
            logger.debug(f"Updated workflow {workflow_id} state")
            return state
    
    async def mark_task_completed(self, workflow_id: str, task_id: str) -> WorkflowState:
        """タスクを完了としてマーク"""
        async with self._get_lock(workflow_id):
            state = await self.get_workflow_state(workflow_id)
            if not state:
                raise ValueError(f"Workflow {workflow_id} not found")
            
            state.completed_tasks.add(task_id)
            state.failed_tasks.discard(task_id)  # 失敗リストから削除
            state.updated_at = time.time()
            
            await self._save_workflow_state(state)
            
            logger.debug(f"Marked task {task_id} as completed for workflow {workflow_id}")
            return state
    
    async def mark_task_failed(self, workflow_id: str, task_id: str) -> WorkflowState:
        """タスクを失敗としてマーク"""
        async with self._get_lock(workflow_id):
            state = await self.get_workflow_state(workflow_id)
            if not state:
                raise ValueError(f"Workflow {workflow_id} not found")
            
            state.failed_tasks.add(task_id)
            state.completed_tasks.discard(task_id)  # 完了リストから削除
            state.updated_at = time.time()
            
            await self._save_workflow_state(state)
            
            logger.debug(f"Marked task {task_id} as failed for workflow {workflow_id}")
            return state
    
    async def save_checkpoint(self, workflow_id: str, checkpoint_type: str, 
                            data: Dict[str, Any]) -> Checkpoint:
        """チェックポイントを保存"""
        checkpoint_id = f"{workflow_id}_{checkpoint_type}_{int(time.time())}"
        
        checkpoint = Checkpoint(
            checkpoint_id=checkpoint_id,
            workflow_id=workflow_id,
            checkpoint_type=checkpoint_type,
            timestamp=time.time(),
            data=data
        )
        
        # チェックポイントリストに追加
        if workflow_id not in self._checkpoints:
            self._checkpoints[workflow_id] = []
        
        self._checkpoints[workflow_id].append(checkpoint)
        
        # 制限を超えた場合は古いものを削除
        if len(self._checkpoints[workflow_id]) > self.checkpoint_limit:
            self._checkpoints[workflow_id] = self._checkpoints[workflow_id][-self.checkpoint_limit:]
        
        # リモートストレージにも保存
        await self._save_checkpoint(checkpoint)
        
        logger.debug(f"Saved checkpoint {checkpoint_id}")
        return checkpoint
    
    async def get_checkpoints(self, workflow_id: str) -> List[Checkpoint]:
        """ワークフローのチェックポイント一覧を取得"""
        # ローカルキャッシュから取得
        if workflow_id in self._checkpoints:
            return self._checkpoints[workflow_id].copy()
        
        # リモートストレージから取得
        checkpoints = await self._load_checkpoints(workflow_id)
        if checkpoints:
            self._checkpoints[workflow_id] = checkpoints
        
        return checkpoints or []
    
    async def get_latest_checkpoint(self, workflow_id: str) -> Optional[Checkpoint]:
        """最新のチェックポイントを取得"""
        checkpoints = await self.get_checkpoints(workflow_id)
        if not checkpoints:
            return None
        
        return max(checkpoints, key=lambda cp: cp.timestamp)
    
    async def get_resumable_state(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """復旧可能な状態を取得"""
        state = await self.get_workflow_state(workflow_id)
        if not state:
            return None
        
        latest_checkpoint = await self.get_latest_checkpoint(workflow_id)
        
        return {
            "workflow_state": state,
            "latest_checkpoint": latest_checkpoint,
            "completed_tasks": list(state.completed_tasks),
            "failed_tasks": list(state.failed_tasks)
        }
    
    async def delete_workflow(self, workflow_id: str) -> bool:
        """ワークフローを削除"""
        async with self._get_lock(workflow_id):
            # ローカルキャッシュから削除
            self._workflow_states.pop(workflow_id, None)
            self._checkpoints.pop(workflow_id, None)
            
            # リモートストレージからも削除
            success = await self._delete_workflow_data(workflow_id)
            
            if success:
                logger.info(f"Deleted workflow {workflow_id}")
            else:
                logger.warning(f"Failed to delete workflow {workflow_id}")
            
            return success
    
    async def list_workflows(self, status_filter: Optional[WorkflowStatus] = None) -> List[WorkflowState]:
        """ワークフロー一覧を取得"""
        # 実装の簡略化：ローカルキャッシュのみ
        # 本格的な実装では、リモートストレージからも取得する
        workflows = list(self._workflow_states.values())
        
        if status_filter:
            workflows = [w for w in workflows if w.status == status_filter]
        
        return workflows
    
    def _get_lock(self, workflow_id: str) -> asyncio.Lock:
        """ワークフロー用のロックを取得"""
        if workflow_id not in self._locks:
            self._locks[workflow_id] = asyncio.Lock()
        return self._locks[workflow_id]
    
    async def _save_workflow_state(self, state: WorkflowState) -> None:
        """ワークフロー状態をストレージに保存"""
        # ローカルキャッシュに保存
        self._workflow_states[state.workflow_id] = state
        
        # リモートストレージに保存
        if self.storage_backend == "redis" and self._redis:
            key = f"workflow:state:{state.workflow_id}"
            data = json.dumps(state.to_dict())
            await self._redis.setex(key, self.state_ttl, data)
    
    async def _load_workflow_state(self, workflow_id: str) -> Optional[WorkflowState]:
        """ストレージからワークフロー状態を読み込み"""
        if self.storage_backend == "redis" and self._redis:
            key = f"workflow:state:{workflow_id}"
            data = await self._redis.get(key)
            if data:
                try:
                    state_dict = json.loads(data)
                    return WorkflowState.from_dict(state_dict)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to decode workflow state: {e}")
        
        return None
    
    async def _save_checkpoint(self, checkpoint: Checkpoint) -> None:
        """チェックポイントをストレージに保存"""
        if self.storage_backend == "redis" and self._redis:
            key = f"workflow:checkpoint:{checkpoint.workflow_id}:{checkpoint.checkpoint_id}"
            data = json.dumps(checkpoint.to_dict())
            await self._redis.setex(key, self.state_ttl, data)
    
    async def _load_checkpoints(self, workflow_id: str) -> List[Checkpoint]:
        """ストレージからチェックポイントを読み込み"""
        checkpoints = []
        
        if self.storage_backend == "redis" and self._redis:
            pattern = f"workflow:checkpoint:{workflow_id}:*"
            keys = await self._redis.keys(pattern)
            
            for key in keys:
                data = await self._redis.get(key)
                if data:
                    try:
                        checkpoint_dict = json.loads(data)
                        checkpoint = Checkpoint.from_dict(checkpoint_dict)
                        checkpoints.append(checkpoint)
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to decode checkpoint: {e}")
        
        # タイムスタンプでソート
        checkpoints.sort(key=lambda cp: cp.timestamp)
        return checkpoints
    
    async def _delete_workflow_data(self, workflow_id: str) -> bool:
        """ストレージからワークフローデータを削除"""
        try:
            if self.storage_backend == "redis" and self._redis:
                # 状態削除
                state_key = f"workflow:state:{workflow_id}"
                await self._redis.delete(state_key)
                
                # チェックポイント削除
                checkpoint_pattern = f"workflow:checkpoint:{workflow_id}:*"
                checkpoint_keys = await self._redis.keys(checkpoint_pattern)
                if checkpoint_keys:
                    await self._redis.delete(*checkpoint_keys)
            
            return True
        except Exception as e:
            logger.error(f"Failed to delete workflow data: {e}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """StateManagerの統計情報を取得"""
        total_workflows = len(self._workflow_states)
        status_counts = {}
        
        for state in self._workflow_states.values():
            status = state.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        total_checkpoints = sum(len(cps) for cps in self._checkpoints.values())
        
        return {
            "total_workflows": total_workflows,
            "status_counts": status_counts,
            "total_checkpoints": total_checkpoints,
            "storage_backend": self.storage_backend,
            "redis_connected": self._redis is not None
        } 