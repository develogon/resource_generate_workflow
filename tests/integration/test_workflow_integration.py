"""ワークフロー全体の統合テスト."""

import pytest
import asyncio
from pathlib import Path
from typing import Dict, Any
from unittest.mock import patch, AsyncMock

from core.orchestrator import WorkflowOrchestrator
from core.events import Event, EventType
from core.state import StateManager
from workers.pool import WorkerPool
from models.workflow import WorkflowStatus


class TestWorkflowIntegration:
    """ワークフロー統合テストクラス."""
    
    @pytest.mark.asyncio
    async def test_complete_workflow_execution(
        self,
        orchestrator: WorkflowOrchestrator,
        temp_dir: Path,
        sample_markdown_content: str,
        sample_workflow_context: Dict[str, Any]
    ):
        """完全なワークフロー実行のテスト."""
        # テスト用入力ファイルを作成
        input_dir = temp_dir / "input"
        input_dir.mkdir(exist_ok=True)
        input_file = input_dir / "python_basics.md"
        input_file.write_text(sample_markdown_content, encoding="utf-8")
        
        # ワークフロー実行
        workflow_id = sample_workflow_context["workflow_id"]
        lang = sample_workflow_context["lang"]
        title = sample_workflow_context["title"]
        
        result = await orchestrator.execute(
            lang=lang,
            title=title,
            input_file=str(input_file)
        )
        
        # 結果の検証
        assert result is not None
        assert result.workflow_id == workflow_id
        assert result.status == WorkflowStatus.COMPLETED
        
        # 出力ディレクトリの確認
        output_dir = temp_dir / "output" / lang / title
        assert output_dir.exists()
        
        # 生成されたファイルの確認
        expected_files = [
            "chapters.json",
            "sections.json", 
            "paragraphs.json",
            "metadata.json"
        ]
        
        for file_name in expected_files:
            assert (output_dir / file_name).exists()
    
    @pytest.mark.asyncio
    async def test_workflow_with_error_recovery(
        self,
        orchestrator: WorkflowOrchestrator,
        temp_dir: Path,
        sample_markdown_content: str,
        sample_workflow_context: Dict[str, Any]
    ):
        """エラー復旧機能のテスト."""
        # テスト用入力ファイルを作成
        input_dir = temp_dir / "input"
        input_dir.mkdir(exist_ok=True)
        input_file = input_dir / "python_basics.md"
        input_file.write_text(sample_markdown_content, encoding="utf-8")
        
        # AIワーカーでエラーを発生させる
        with patch.object(
            orchestrator.worker_pool.get_worker("ai"),
            "process",
            side_effect=[Exception("AI API Error"), AsyncMock()]
        ):
            result = await orchestrator.execute(
                lang=sample_workflow_context["lang"],
                title=sample_workflow_context["title"],
                input_file=str(input_file)
            )
            
            # エラーが回復されて成功することを確認
            assert result.status == WorkflowStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_workflow_state_persistence(
        self,
        orchestrator: WorkflowOrchestrator,
        state_manager: StateManager,
        sample_workflow_context: Dict[str, Any]
    ):
        """ワークフロー状態の永続化テスト."""
        workflow_id = sample_workflow_context["workflow_id"]
        
        # 初期状態を保存
        await state_manager.save_workflow_state(
            workflow_id,
            sample_workflow_context
        )
        
        # チェックポイントを保存
        checkpoint_data = {
            "step": "chapter_parsing",
            "completed_chapters": 1,
            "total_chapters": 3
        }
        await state_manager.save_checkpoint(
            workflow_id,
            "chapter_parsed",
            checkpoint_data
        )
        
        # 状態を復元
        restored_state = await state_manager.get_workflow_state(workflow_id)
        assert restored_state is not None
        assert restored_state["workflow_id"] == workflow_id
        
        # 最新チェックポイントを取得
        latest_checkpoint = await state_manager.get_latest_checkpoint(workflow_id)
        assert latest_checkpoint is not None
        assert latest_checkpoint["data"]["step"] == "chapter_parsing"
    
    @pytest.mark.asyncio
    async def test_workflow_resume_from_checkpoint(
        self,
        orchestrator: WorkflowOrchestrator,
        state_manager: StateManager,
        sample_workflow_context: Dict[str, Any]
    ):
        """チェックポイントからのワークフロー再開テスト."""
        workflow_id = sample_workflow_context["workflow_id"]
        
        # 中断された状態をシミュレート
        interrupted_state = {
            **sample_workflow_context,
            "status": "suspended",
            "completed_steps": ["chapter_parsing", "section_parsing"]
        }
        
        await state_manager.save_workflow_state(workflow_id, interrupted_state)
        
        # チェックポイントを作成
        checkpoint_data = {
            "step": "paragraph_processing",
            "completed_paragraphs": 5,
            "total_paragraphs": 10
        }
        await state_manager.save_checkpoint(
            workflow_id,
            "paragraph_parsed",
            checkpoint_data
        )
        
        # ワークフローを再開
        result = await orchestrator.resume(workflow_id)
        
        # 再開が成功することを確認
        assert result is not None
        assert result.workflow_id == workflow_id
    
    @pytest.mark.asyncio
    async def test_parallel_workflow_execution(
        self,
        orchestrator: WorkflowOrchestrator,
        temp_dir: Path,
        sample_markdown_content: str
    ):
        """複数ワークフローの並列実行テスト."""
        # 複数の入力ファイルを作成
        input_dir = temp_dir / "input"
        input_dir.mkdir(exist_ok=True)
        
        workflows = []
        for i in range(3):
            input_file = input_dir / f"content_{i}.md"
            input_file.write_text(
                sample_markdown_content.replace(
                    "第1章: Pythonの基礎",
                    f"第{i+1}章: コンテンツ{i+1}"
                ),
                encoding="utf-8"
            )
            
            workflows.append({
                "lang": "ja",
                "title": f"コンテンツ{i+1}",
                "input_file": str(input_file)
            })
        
        # 並列実行
        tasks = []
        for workflow in workflows:
            task = orchestrator.execute(
                lang=workflow["lang"],
                title=workflow["title"],
                input_file=workflow["input_file"]
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # 全てのワークフローが成功することを確認
        assert len(results) == 3
        for result in results:
            assert result.status == WorkflowStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_workflow_metrics_collection(
        self,
        orchestrator: WorkflowOrchestrator,
        temp_dir: Path,
        sample_markdown_content: str,
        sample_workflow_context: Dict[str, Any]
    ):
        """ワークフローメトリクス収集のテスト."""
        # テスト用入力ファイルを作成
        input_dir = temp_dir / "input"
        input_dir.mkdir(exist_ok=True)
        input_file = input_dir / "python_basics.md"
        input_file.write_text(sample_markdown_content, encoding="utf-8")
        
        # メトリクス収集を有効化
        metrics = orchestrator.metrics
        initial_workflows_started = metrics.workflows_started._value._value
        
        # ワークフロー実行
        await orchestrator.execute(
            lang=sample_workflow_context["lang"],
            title=sample_workflow_context["title"],
            input_file=str(input_file)
        )
        
        # メトリクスが更新されていることを確認
        assert metrics.workflows_started._value._value > initial_workflows_started
        assert metrics.workflows_completed._value._value > 0
    
    @pytest.mark.asyncio
    async def test_workflow_timeout_handling(
        self,
        orchestrator: WorkflowOrchestrator,
        temp_dir: Path,
        sample_markdown_content: str,
        sample_workflow_context: Dict[str, Any]
    ):
        """ワークフロータイムアウト処理のテスト."""
        # テスト用入力ファイルを作成
        input_dir = temp_dir / "input"
        input_dir.mkdir(exist_ok=True)
        input_file = input_dir / "python_basics.md"
        input_file.write_text(sample_markdown_content, encoding="utf-8")
        
        # タイムアウトを短く設定
        orchestrator.config.task_timeout = 0.1
        
        # 長時間実行されるワーカーをモック
        with patch.object(
            orchestrator.worker_pool.get_worker("ai"),
            "process",
            side_effect=lambda *args: asyncio.sleep(1.0)  # タイムアウトより長い
        ):
            with pytest.raises(asyncio.TimeoutError):
                await orchestrator.execute(
                    lang=sample_workflow_context["lang"],
                    title=sample_workflow_context["title"],
                    input_file=str(input_file)
                ) 