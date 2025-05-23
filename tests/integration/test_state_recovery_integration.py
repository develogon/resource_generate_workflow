"""状態管理とエラー復旧の統合テスト."""

import pytest
import asyncio
import json
from typing import Dict, Any, List
from unittest.mock import patch, AsyncMock
from datetime import datetime, timedelta

from core.state import StateManager
from core.orchestrator import WorkflowOrchestrator
from models.workflow import WorkflowStatus, WorkflowContext
from workers.base import BaseWorker
from utils.cache import CacheManager
from utils.retry import RetryManager


class TestStateRecoveryIntegration:
    """状態管理とエラー復旧の統合テストクラス."""
    
    @pytest.mark.asyncio
    async def test_checkpoint_creation_and_restoration(
        self,
        state_manager: StateManager,
        sample_workflow_context: Dict[str, Any]
    ):
        """チェックポイントの作成と復元テスト."""
        workflow_id = sample_workflow_context["workflow_id"]
        
        # 初期チェックポイントの作成
        initial_checkpoint = {
            "step": "workflow_initialized",
            "timestamp": datetime.utcnow().isoformat(),
            "data": sample_workflow_context
        }
        
        await state_manager.save_checkpoint(
            workflow_id,
            "workflow_initialized",
            initial_checkpoint
        )
        
        # 進行中チェックポイントの作成
        progress_checkpoint = {
            "step": "chapter_parsing",
            "timestamp": datetime.utcnow().isoformat(),
            "completed_chapters": 2,
            "total_chapters": 5,
            "processing_chapter": 3,
            "data": {
                "processed_files": ["chapter1.md", "chapter2.md"],
                "current_file": "chapter3.md"
            }
        }
        
        await state_manager.save_checkpoint(
            workflow_id,
            "chapter_parsing",
            progress_checkpoint
        )
        
        # 完了チェックポイントの作成
        completion_checkpoint = {
            "step": "content_generation_completed",
            "timestamp": datetime.utcnow().isoformat(),
            "generated_contents": {
                "articles": 15,
                "scripts": 15,
                "tweets": 30
            },
            "data": {
                "output_files": ["articles.json", "scripts.json", "tweets.json"]
            }
        }
        
        await state_manager.save_checkpoint(
            workflow_id,
            "content_generation_completed",
            completion_checkpoint
        )
        
        # チェックポイント履歴の取得
        checkpoints = await state_manager.get_checkpoint_history(workflow_id)
        
        # チェックポイントが適切に保存されたことを確認
        assert len(checkpoints) == 3
        
        # 最新チェックポイントの取得
        latest_checkpoint = await state_manager.get_latest_checkpoint(workflow_id)
        assert latest_checkpoint["step"] == "content_generation_completed"
        
        # 特定ステップのチェックポイント取得
        parsing_checkpoint = await state_manager.get_checkpoint_by_step(
            workflow_id,
            "chapter_parsing"
        )
        assert parsing_checkpoint["completed_chapters"] == 2
    
    @pytest.mark.asyncio
    async def test_workflow_interruption_and_resume(
        self,
        orchestrator: WorkflowOrchestrator,
        state_manager: StateManager,
        temp_dir,
        sample_markdown_content: str,
        sample_workflow_context: Dict[str, Any]
    ):
        """ワークフロー中断と再開のテスト."""
        workflow_id = sample_workflow_context["workflow_id"]
        
        # テスト用入力ファイルを作成
        input_dir = temp_dir / "input"
        input_dir.mkdir(exist_ok=True)
        input_file = input_dir / "test_content.md"
        input_file.write_text(sample_markdown_content, encoding="utf-8")
        
        # ワーカー処理を中断シミュレーション
        interruption_count = 0
        
        async def interrupting_process(event):
            nonlocal interruption_count
            interruption_count += 1
            
            # 3回目の処理で中断
            if interruption_count == 3:
                # チェックポイントを保存して中断
                await state_manager.save_checkpoint(
                    workflow_id,
                    "interrupted_at_ai_processing",
                    {
                        "interrupted_at": datetime.utcnow().isoformat(),
                        "completed_tasks": interruption_count - 1,
                        "current_task": event.data
                    }
                )
                raise Exception("システム中断シミュレーション")
            
            return f"処理完了: {interruption_count}"
        
        # AIワーカーを中断させる
        with patch.object(
            orchestrator.worker_pool.get_worker("ai"),
            "process",
            side_effect=interrupting_process
        ):
            # ワークフロー実行（中断される）
            with pytest.raises(Exception, match="システム中断シミュレーション"):
                await orchestrator.execute(
                    lang=sample_workflow_context["lang"],
                    title=sample_workflow_context["title"],
                    input_file=str(input_file)
                )
        
        # 中断状態の確認
        workflow_state = await state_manager.get_workflow_state(workflow_id)
        assert workflow_state is not None
        
        latest_checkpoint = await state_manager.get_latest_checkpoint(workflow_id)
        assert latest_checkpoint["step"] == "interrupted_at_ai_processing"
        assert latest_checkpoint["completed_tasks"] == 2
        
        # ワーカーを正常処理に戻す
        with patch.object(
            orchestrator.worker_pool.get_worker("ai"),
            "process",
            return_value="復旧後処理"
        ):
            # ワークフロー再開
            resumed_result = await orchestrator.resume(workflow_id)
            
            # 再開が成功したことを確認
            assert resumed_result is not None
            assert resumed_result.status == WorkflowStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_partial_failure_recovery(
        self,
        orchestrator: WorkflowOrchestrator,
        state_manager: StateManager,
        temp_dir,
        sample_workflow_context: Dict[str, Any]
    ):
        """部分的な失敗からの復旧テスト."""
        workflow_id = sample_workflow_context["workflow_id"]
        
        # 失敗するタスクのシミュレーション
        failed_tasks = set()
        
        async def partially_failing_process(event):
            task_id = event.data.get("task_id", "unknown")
            
            # 特定のタスクで失敗
            if task_id in ["task_3", "task_7", "task_12"]:
                failed_tasks.add(task_id)
                # 失敗情報をチェックポイントに保存
                await state_manager.save_checkpoint(
                    workflow_id,
                    f"failed_task_{task_id}",
                    {
                        "failed_task": task_id,
                        "error": "模擬的な処理失敗",
                        "timestamp": datetime.utcnow().isoformat(),
                        "retry_count": 0
                    }
                )
                raise Exception(f"Task {task_id} failed")
            
            return f"Task {task_id} completed successfully"
        
        # 複数タスクを実行
        tasks = []
        for i in range(15):
            task_event = {
                "task_id": f"task_{i}",
                "data": f"test_data_{i}"
            }
            tasks.append(task_event)
        
        # 部分的失敗の実行
        with patch.object(
            orchestrator.worker_pool.get_worker("ai"),
            "process",
            side_effect=partially_failing_process
        ):
            # 失敗するタスクがあることを期待
            results = []
            for task in tasks:
                try:
                    result = await orchestrator.worker_pool.get_worker("ai").process(task)
                    results.append(result)
                except Exception as e:
                    results.append(f"Failed: {str(e)}")
        
        # 失敗したタスクの確認
        assert len(failed_tasks) == 3
        assert "task_3" in failed_tasks
        assert "task_7" in failed_tasks
        assert "task_12" in failed_tasks
        
        # 失敗したタスクのチェックポイント確認
        failed_checkpoints = []
        for task_id in failed_tasks:
            checkpoint = await state_manager.get_checkpoint_by_step(
                workflow_id,
                f"failed_task_{task_id}"
            )
            failed_checkpoints.append(checkpoint)
        
        assert len(failed_checkpoints) == 3
        
        # 失敗タスクの再実行
        async def retry_process(event):
            task_id = event.data.get("task_id", "unknown")
            return f"Task {task_id} completed on retry"
        
        with patch.object(
            orchestrator.worker_pool.get_worker("ai"),
            "process",
            side_effect=retry_process
        ):
            # 失敗したタスクを再実行
            retry_results = []
            for task_id in failed_tasks:
                task_event = {"task_id": task_id, "data": f"retry_data_{task_id}"}
                result = await orchestrator.worker_pool.get_worker("ai").process(task_event)
                retry_results.append(result)
                
                # 成功チェックポイントを保存
                await state_manager.save_checkpoint(
                    workflow_id,
                    f"completed_task_{task_id}",
                    {
                        "task_id": task_id,
                        "status": "completed_on_retry",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
        
        # 再実行が成功したことを確認
        assert len(retry_results) == 3
        assert all("completed on retry" in result for result in retry_results)
    
    @pytest.mark.asyncio
    async def test_state_persistence_across_restarts(
        self,
        redis_client,
        state_manager: StateManager,
        sample_workflow_context: Dict[str, Any]
    ):
        """再起動を跨いだ状態永続化テスト."""
        workflow_id = sample_workflow_context["workflow_id"]
        
        # 複雑な状態データを作成
        complex_state = {
            "workflow_id": workflow_id,
            "status": "processing",
            "progress": {
                "chapters": {
                    "total": 10,
                    "completed": 6,
                    "current": 7
                },
                "sections": {
                    "total": 45,
                    "completed": 32,
                    "current": 33
                },
                "paragraphs": {
                    "total": 120,
                    "completed": 95,
                    "current": 96
                }
            },
            "generated_content": {
                "articles": 95,
                "scripts": 95,
                "tweets": 190,
                "thumbnails": 32
            },
            "processing_stats": {
                "start_time": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
                "estimated_completion": (datetime.utcnow() + timedelta(minutes=30)).isoformat(),
                "avg_processing_time_per_paragraph": 1.2,
                "error_count": 3,
                "retry_count": 8
            },
            "metadata": {
                "author": "テストユーザー",
                "content_type": "技術書",
                "target_language": "ja",
                "output_formats": ["article", "script", "tweet"]
            }
        }
        
        # 状態を保存
        await state_manager.save_workflow_state(workflow_id, complex_state)
        
        # 複数のチェックポイントを作成
        checkpoints = [
            {
                "step": "chapter_6_completed",
                "data": {"completed_at": datetime.utcnow().isoformat()}
            },
            {
                "step": "section_32_completed", 
                "data": {"completed_at": datetime.utcnow().isoformat()}
            },
            {
                "step": "paragraph_95_completed",
                "data": {"completed_at": datetime.utcnow().isoformat()}
            }
        ]
        
        for checkpoint in checkpoints:
            await state_manager.save_checkpoint(
                workflow_id,
                checkpoint["step"],
                checkpoint["data"]
            )
        
        # Redis接続を一旦切断（再起動シミュレーション）
        await redis_client.close()
        
        # 新しいStateManagerインスタンスを作成（再起動後）
        new_state_manager = StateManager(state_manager.config)
        await new_state_manager.connect()
        
        # 状態の復元
        restored_state = await new_state_manager.get_workflow_state(workflow_id)
        
        # 状態が完全に復元されたことを確認
        assert restored_state is not None
        assert restored_state["workflow_id"] == workflow_id
        assert restored_state["progress"]["chapters"]["completed"] == 6
        assert restored_state["generated_content"]["articles"] == 95
        assert restored_state["processing_stats"]["error_count"] == 3
        
        # チェックポイントの復元確認
        restored_checkpoints = await new_state_manager.get_checkpoint_history(workflow_id)
        assert len(restored_checkpoints) == 3
        
        latest_checkpoint = await new_state_manager.get_latest_checkpoint(workflow_id)
        assert latest_checkpoint["step"] == "paragraph_95_completed"
        
        # クリーンアップ
        await new_state_manager.close()
    
    @pytest.mark.asyncio
    async def test_concurrent_state_updates(
        self,
        state_manager: StateManager,
        sample_workflow_context: Dict[str, Any]
    ):
        """同時状態更新のテスト."""
        workflow_id = sample_workflow_context["workflow_id"]
        
        # 並列更新タスクを定義
        async def update_progress(worker_id: int, updates: int):
            for i in range(updates):
                checkpoint_data = {
                    "worker_id": worker_id,
                    "update_number": i,
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": f"Worker {worker_id} update {i}"
                }
                
                await state_manager.save_checkpoint(
                    workflow_id,
                    f"worker_{worker_id}_update_{i}",
                    checkpoint_data
                )
                
                # 小さな遅延を追加
                await asyncio.sleep(0.01)
        
        # 5つのワーカーが並列で状態更新
        tasks = []
        for worker_id in range(5):
            task = update_progress(worker_id, 10)
            tasks.append(task)
        
        # 並列実行
        await asyncio.gather(*tasks)
        
        # 全ての更新が保存されたことを確認
        all_checkpoints = await state_manager.get_checkpoint_history(workflow_id)
        assert len(all_checkpoints) == 50  # 5 workers × 10 updates
        
        # ワーカー別の更新数を確認
        worker_updates = {}
        for checkpoint in all_checkpoints:
            worker_id = checkpoint["worker_id"]
            worker_updates[worker_id] = worker_updates.get(worker_id, 0) + 1
        
        # 各ワーカーが10回ずつ更新したことを確認
        for worker_id in range(5):
            assert worker_updates[worker_id] == 10
    
    @pytest.mark.asyncio
    async def test_cache_invalidation_on_state_change(
        self,
        state_manager: StateManager,
        sample_workflow_context: Dict[str, Any]
    ):
        """状態変更時のキャッシュ無効化テスト."""
        workflow_id = sample_workflow_context["workflow_id"]
        
        # 初期状態を保存
        initial_state = {
            "status": "processing",
            "progress": 25
        }
        await state_manager.save_workflow_state(workflow_id, initial_state)
        
        # 状態をキャッシュから取得
        cached_state_1 = await state_manager.get_workflow_state(workflow_id)
        assert cached_state_1["progress"] == 25
        
        # 状態を更新
        updated_state = {
            "status": "processing",
            "progress": 75
        }
        await state_manager.save_workflow_state(workflow_id, updated_state)
        
        # キャッシュが無効化され、新しい状態が取得されることを確認
        cached_state_2 = await state_manager.get_workflow_state(workflow_id)
        assert cached_state_2["progress"] == 75
        
        # チェックポイント更新でもキャッシュが無効化されることを確認
        await state_manager.save_checkpoint(
            workflow_id,
            "progress_update",
            {"new_progress": 90}
        )
        
        # 最新チェックポイントが正しく取得されることを確認
        latest_checkpoint = await state_manager.get_latest_checkpoint(workflow_id)
        assert latest_checkpoint["new_progress"] == 90
    
    @pytest.mark.asyncio
    async def test_state_cleanup_and_retention(
        self,
        state_manager: StateManager,
        sample_workflow_context: Dict[str, Any]
    ):
        """状態クリーンアップと保持ポリシーのテスト."""
        workflow_id = sample_workflow_context["workflow_id"]
        
        # 古いワークフローを作成
        old_workflow_id = "old-workflow-001"
        old_state = {
            "workflow_id": old_workflow_id,
            "status": "completed",
            "completed_at": (datetime.utcnow() - timedelta(days=30)).isoformat()
        }
        
        await state_manager.save_workflow_state(old_workflow_id, old_state)
        
        # 古いチェックポイントを作成
        for i in range(5):
            checkpoint_data = {
                "step": f"old_step_{i}",
                "timestamp": (datetime.utcnow() - timedelta(days=25 + i)).isoformat()
            }
            await state_manager.save_checkpoint(
                old_workflow_id,
                f"old_step_{i}",
                checkpoint_data
            )
        
        # 現在のワークフロー状態を保存
        current_state = {
            "workflow_id": workflow_id,
            "status": "processing", 
            "started_at": datetime.utcnow().isoformat()
        }
        await state_manager.save_workflow_state(workflow_id, current_state)
        
        # クリーンアップ実行（30日より古いデータを削除）
        cleanup_result = await state_manager.cleanup_old_states(
            retention_days=30
        )
        
        # 古いワークフローが削除されたことを確認
        old_state_result = await state_manager.get_workflow_state(old_workflow_id)
        assert old_state_result is None
        
        # 現在のワークフローは保持されていることを確認
        current_state_result = await state_manager.get_workflow_state(workflow_id)
        assert current_state_result is not None
        assert current_state_result["workflow_id"] == workflow_id
        
        # クリーンアップ結果の確認
        assert cleanup_result["deleted_workflows"] >= 1
        assert cleanup_result["deleted_checkpoints"] >= 5 