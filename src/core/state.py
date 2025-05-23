"""分散状態管理システム."""

import asyncio
import json
import logging
import time
import uuid
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, asdict, field
from enum import Enum

try:
    import aioredis
    REDIS_AVAILABLE = True
except (ImportError, TypeError) as e:
    REDIS_AVAILABLE = False
    aioredis = None
    logging.warning(f"Redis not available: {e}")

logger = logging.getLogger(__name__)


class WorkflowStatus(Enum):
    """ワークフロー状態."""
    INITIALIZED = "initialized"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SUSPENDED = "suspended"


@dataclass
class WorkflowContext:
    """ワークフロー実行コンテキスト."""
    workflow_id: str
    lang: str
    title: str
    status: WorkflowStatus
    metadata: Dict[str, Any] = field(default_factory=dict)
    checkpoints: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    completed_tasks: List[str] = field(default_factory=list)
    failed_tasks: List[str] = field(default_factory=list)
    input_file: Optional[str] = None
    
    def __post_init__(self):
        """初期化後処理."""
        if self.created_at is None:
            self.created_at = time.time()

    def update_status(self, status: WorkflowStatus):
        """状態を更新."""
        self.status = status
        self.updated_at = time.time()


@dataclass
class Checkpoint:
    """チェックポイントデータ."""
    checkpoint_id: str
    workflow_id: str
    checkpoint_type: str
    timestamp: float
    data: Dict[str, Any]
    completed_tasks: List[str] = field(default_factory=list)


class StateManager:
    """分散状態管理システム."""
    
    def __init__(self, config):
        """初期化."""
        self.config = config
        self.redis = None  # Redis接続（実装時に設定）
        self.local_cache: Dict[str, Any] = {}
        self.workflows: Dict[str, WorkflowContext] = {}
        
    async def initialize(self):
        """StateManagerの初期化処理."""
        await self.connect()
        logger.info("StateManager initialized")
        
    async def close(self):
        """StateManagerのクリーンアップ処理."""
        await self.disconnect()
        logger.info("StateManager closed")
        
    async def connect(self):
        """外部ストレージ接続の確立."""
        if REDIS_AVAILABLE and hasattr(self.config, 'redis_url'):
            try:
                await self._connect_redis()
            except Exception as e:
                logger.warning(f"Redis connection failed, using local cache: {e}")
                
        logger.info("StateManager connected")
        
    async def disconnect(self):
        """外部ストレージ接続の切断."""
        if self.redis:
            await self.redis.aclose()
            self.redis = None
        logger.info("StateManager disconnected")
        
    async def _connect_redis(self):
        """Redis接続の確立."""
        if not REDIS_AVAILABLE:
            raise ImportError("aioredis not available")
            
        self.redis = aioredis.from_url(
            self.config.redis_url,
            decode_responses=True
        )
        
        # 接続テスト
        await self.redis.ping()
        logger.info("Connected to Redis")
        
    async def create_workflow(self, lang: str, title: str, input_file: Optional[str] = None) -> WorkflowContext:
        """新しいワークフローを作成."""
        workflow_id = str(uuid.uuid4())
        
        context = WorkflowContext(
            workflow_id=workflow_id,
            lang=lang,
            title=title,
            status=WorkflowStatus.INITIALIZED,
            metadata={
                "input_file": input_file,
                "created_by": "system",
                "version": "1.0"
            }
        )
        
        # ローカルキャッシュに保存
        self.workflows[workflow_id] = context
        
        # 永続化
        await self.save_workflow_state(workflow_id, context)
        
        logger.info(f"Created workflow {workflow_id}")
        return context
        
    async def get_workflow(self, workflow_id: str) -> Optional[WorkflowContext]:
        """ワークフローコンテキストを取得."""
        # ローカルキャッシュから確認
        if workflow_id in self.workflows:
            return self.workflows[workflow_id]
            
        # 永続ストレージから復元
        state_data = await self.load_workflow_state(workflow_id)
        if state_data:
            context = self._deserialize_workflow(state_data)
            self.workflows[workflow_id] = context
            return context
            
        return None
        
    async def update_workflow(self, workflow_id: str, **updates):
        """ワークフローを更新."""
        context = await self.get_workflow(workflow_id)
        if not context:
            raise ValueError(f"Workflow not found: {workflow_id}")
            
        # 更新適用
        for key, value in updates.items():
            if hasattr(context, key):
                setattr(context, key, value)
                
        context.updated_at = time.time()
        
        # 永続化
        await self.save_workflow_state(workflow_id, context)
        
    async def save_workflow_state(self, workflow_id: str, context: WorkflowContext):
        """ワークフロー状態の保存."""
        state_data = self._serialize_workflow(context)
        key = f"workflow:{workflow_id}:state"
        
        # ローカルキャッシュ更新
        self.local_cache[key] = state_data
        
        # Redis保存（実装時）
        if self.redis:
            await self.redis.setex(key, 3600, json.dumps(state_data))
            
    async def load_workflow_state(self, workflow_id: str) -> Optional[Dict]:
        """ワークフロー状態を読み込み."""
        key = f"workflow:{workflow_id}:state"
        
        # ローカルキャッシュから確認
        if key in self.local_cache:
            return self.local_cache[key]
            
        # Redis から読み込み（実装時）
        if self.redis:
            data = await self.redis.get(key)
            if data:
                return json.loads(data)
                
        return None
        
    async def get_workflow_state(self, workflow_id: str) -> Optional[Dict]:
        """ワークフロー状態を取得（load_workflow_stateのエイリアス）."""
        return await self.load_workflow_state(workflow_id)
        
    async def update_workflow_state(self, workflow_id: str, **updates):
        """ワークフロー状態を更新."""
        await self.update_workflow(workflow_id, **updates)
        
    async def save_checkpoint(self, workflow_id: str, checkpoint_type: str, data: Dict):
        """チェックポイントの保存."""
        checkpoint_id = str(uuid.uuid4())
        checkpoint = Checkpoint(
            checkpoint_id=checkpoint_id,
            workflow_id=workflow_id,
            checkpoint_type=checkpoint_type,
            timestamp=time.time(),
            data=data
        )
        
        # チェックポイントリストに追加
        key = f"workflow:{workflow_id}:checkpoints"
        checkpoint_data = self._serialize_checkpoint(checkpoint)
        
        # ローカルキャッシュ
        if key not in self.local_cache:
            self.local_cache[key] = []
        self.local_cache[key].append(checkpoint_data)
        
        # 最新チェックポイントを別途保存
        latest_key = f"workflow:{workflow_id}:latest_checkpoint"
        self.local_cache[latest_key] = checkpoint_data
        
        # Redis保存（実装時）
        if self.redis:
            await self.redis.rpush(key, json.dumps(checkpoint_data))
            await self.redis.set(latest_key, json.dumps(checkpoint_data))
            
        logger.debug(f"Saved checkpoint {checkpoint_type} for workflow {workflow_id}")
        
    async def get_latest_checkpoint(self, workflow_id: str) -> Optional[Checkpoint]:
        """最新チェックポイントを取得."""
        key = f"workflow:{workflow_id}:latest_checkpoint"
        
        # ローカルキャッシュから確認
        if key in self.local_cache:
            return self._deserialize_checkpoint(self.local_cache[key])
            
        # Redis から読み込み（実装時）
        if self.redis:
            data = await self.redis.get(key)
            if data:
                return self._deserialize_checkpoint(json.loads(data))
                
        return None
        
    async def get_resumable_state(self, workflow_id: str) -> Optional[Dict]:
        """再開可能な状態を取得."""
        checkpoint = await self.get_latest_checkpoint(workflow_id)
        if not checkpoint:
            return None
            
        context = await self.get_workflow(workflow_id)
        if not context:
            return None
            
        return {
            "checkpoint": checkpoint,
            "completed_tasks": context.completed_tasks,
            "workflow_state": context
        }
        
    async def mark_task_completed(self, workflow_id: str, task_id: str):
        """タスクを完了済みとしてマーク."""
        context = await self.get_workflow(workflow_id)
        if context and task_id not in context.completed_tasks:
            context.completed_tasks.append(task_id)
            await self.save_workflow_state(workflow_id, context)
            
    async def mark_task_failed(self, workflow_id: str, task_id: str):
        """タスクを失敗としてマーク."""
        context = await self.get_workflow(workflow_id)
        if context and task_id not in context.failed_tasks:
            context.failed_tasks.append(task_id)
            await self.save_workflow_state(workflow_id, context)
            
    def _serialize_workflow(self, context: WorkflowContext) -> Dict:
        """ワークフローコンテキストをシリアライズ."""
        return {
            "workflow_id": context.workflow_id,
            "lang": context.lang,
            "title": context.title,
            "status": context.status.value,
            "metadata": context.metadata,
            "checkpoints": context.checkpoints,
            "created_at": context.created_at,
            "updated_at": context.updated_at,
            "completed_tasks": context.completed_tasks,
            "failed_tasks": context.failed_tasks,
            "input_file": context.input_file
        }
        
    def _deserialize_workflow(self, data: Dict) -> WorkflowContext:
        """ワークフローコンテキストをデシリアライズ."""
        return WorkflowContext(
            workflow_id=data["workflow_id"],
            lang=data["lang"],
            title=data["title"],
            status=WorkflowStatus(data["status"]),
            metadata=data.get("metadata", {}),
            checkpoints=data.get("checkpoints", []),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
            completed_tasks=data.get("completed_tasks", []),
            failed_tasks=data.get("failed_tasks", []),
            input_file=data.get("input_file")
        )
        
    def _serialize_checkpoint(self, checkpoint: Checkpoint) -> Dict:
        """チェックポイントをシリアライズ."""
        return {
            "checkpoint_id": checkpoint.checkpoint_id,
            "workflow_id": checkpoint.workflow_id,
            "checkpoint_type": checkpoint.checkpoint_type,
            "timestamp": checkpoint.timestamp,
            "data": checkpoint.data,
            "completed_tasks": checkpoint.completed_tasks
        }
        
    def _deserialize_checkpoint(self, data: Dict) -> Checkpoint:
        """チェックポイントをデシリアライズ."""
        return Checkpoint(
            checkpoint_id=data["checkpoint_id"],
            workflow_id=data["workflow_id"],
            checkpoint_type=data["checkpoint_type"],
            timestamp=data["timestamp"],
            data=data["data"],
            completed_tasks=data.get("completed_tasks", [])
        )
        
    async def get_checkpoint_history(self, workflow_id: str) -> List[Dict[str, Any]]:
        """チェックポイント履歴の取得."""
        key = f"workflow:{workflow_id}:checkpoints"
        
        # Redisから取得
        if self.redis:
            try:
                values = await self.redis.lrange(key, 0, -1)
                return [json.loads(value) for value in values]
            except Exception as e:
                logger.error(f"Redis get checkpoint history failed: {e}")
                
        # ローカルキャッシュから取得
        checkpoints = self.local_cache.get(key, [])
        if checkpoints and isinstance(checkpoints[0], dict):
            return checkpoints
        return checkpoints
        
    async def load_context(self, workflow_id: str) -> Optional[WorkflowContext]:
        """ワークフローコンテキストの復元."""
        state = await self.load_workflow_state(workflow_id)
        if not state:
            return None
            
        try:
            context = self._deserialize_workflow(state)
            return context
        except Exception as e:
            logger.error(f"Failed to load context for {workflow_id}: {e}")
            return None
            
    async def delete_workflow_data(self, workflow_id: str):
        """ワークフローデータの削除."""
        keys = [
            f"workflow:{workflow_id}:state",
            f"workflow:{workflow_id}:checkpoints",
            f"workflow:{workflow_id}:latest_checkpoint"
        ]
        
        # Redisから削除
        if self.redis:
            try:
                await self.redis.delete(*keys)
            except Exception as e:
                logger.error(f"Redis delete failed: {e}")
                
        # ローカルキャッシュから削除
        for key in keys:
            self.local_cache.pop(key, None)
            
        logger.info(f"Deleted workflow data for {workflow_id}")
        
    async def get_active_workflows(self) -> List[str]:
        """アクティブなワークフローIDのリストを取得."""
        if self.redis:
            try:
                keys = await self.redis.keys("workflow:*:state")
                # ワークフローIDを抽出
                workflow_ids = []
                for key in keys:
                    parts = key.split(':')
                    if len(parts) >= 2:
                        workflow_ids.append(parts[1])
                return workflow_ids
            except Exception as e:
                logger.error(f"Redis get active workflows failed: {e}")
                
        # ローカルキャッシュから取得
        workflow_ids = []
        for key in self.local_cache.keys():
            if key.startswith("workflow:") and key.endswith(":state"):
                parts = key.split(':')
                if len(parts) >= 2:
                    workflow_ids.append(parts[1])
        return workflow_ids 