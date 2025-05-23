"""イベントバスとワーカー間の統合テスト."""

import pytest
import asyncio
from typing import List, Dict, Any
from unittest.mock import patch, AsyncMock

from core.events import EventBus, Event, EventType
from workers.parser import ParserWorker
from workers.ai import AIWorker
from workers.media import MediaWorker
from workers.aggregator import AggregatorWorker
from conftest import create_test_event


class TestEventWorkerIntegration:
    """イベントバスとワーカーの統合テストクラス."""
    
    @pytest.mark.asyncio
    async def test_event_bus_worker_communication(
        self,
        event_bus: EventBus,
        parser_worker: ParserWorker,
        ai_worker: AIWorker,
        sample_workflow_context: Dict[str, Any]
    ):
        """イベントバスとワーカー間の基本的な通信テスト."""
        workflow_id = sample_workflow_context["workflow_id"]
        
        # イベント発行履歴を追跡
        published_events = []
        original_publish = event_bus.publish
        
        async def track_publish(event: Event, delay: float = 0):
            published_events.append(event)
            return await original_publish(event, delay)
        
        event_bus.publish = track_publish
        
        # ワークフロー開始イベントを発行
        start_event = create_test_event(
            EventType.WORKFLOW_STARTED,
            workflow_id,
            {
                "lang": "ja",
                "title": "テストコンテンツ",
                "input_file": "/test/input.md"
            }
        )
        
        await event_bus.publish(start_event)
        
        # イベント処理を待機
        await asyncio.sleep(0.1)
        
        # イベントが適切に発行されたことを確認
        assert len(published_events) >= 1
        assert any(e.type == EventType.WORKFLOW_STARTED for e in published_events)
    
    @pytest.mark.asyncio
    async def test_parser_to_ai_event_flow(
        self,
        event_bus: EventBus,
        parser_worker: ParserWorker,
        ai_worker: AIWorker,
        sample_workflow_context: Dict[str, Any]
    ):
        """パーサーからAIワーカーへのイベントフローテスト."""
        workflow_id = sample_workflow_context["workflow_id"]
        
        # AIワーカーの処理をモック
        ai_worker.process = AsyncMock()
        
        # セクション解析完了イベントを発行
        section_event = create_test_event(
            EventType.SECTION_PARSED,
            workflow_id,
            {
                "section_index": 0,
                "section_title": "Pythonとは",
                "content": "Pythonは優れたプログラミング言語です。",
                "structure_info": {"paragraphs": 3, "code_blocks": 1}
            }
        )
        
        await event_bus.publish(section_event)
        
        # イベント処理を待機
        await asyncio.sleep(0.1)
        
        # AIワーカーが適切に呼び出されたことを確認
        ai_worker.process.assert_called()
    
    @pytest.mark.asyncio
    async def test_ai_to_media_event_flow(
        self,
        event_bus: EventBus,
        ai_worker: AIWorker,
        media_worker: MediaWorker,
        sample_workflow_context: Dict[str, Any]
    ):
        """AIワーカーからメディアワーカーへのイベントフローテスト."""
        workflow_id = sample_workflow_context["workflow_id"]
        
        # メディアワーカーの処理をモック
        media_worker.process = AsyncMock()
        
        # コンテンツ生成完了イベントを発行
        content_event = create_test_event(
            EventType.CONTENT_GENERATED,
            workflow_id,
            {
                "paragraph_id": "p001",
                "content_type": "article",
                "content": "生成された記事コンテンツ",
                "images": ["image1.svg", "image2.mermaid"]
            }
        )
        
        await event_bus.publish(content_event)
        
        # イベント処理を待機
        await asyncio.sleep(0.1)
        
        # メディアワーカーが適切に呼び出されたことを確認
        media_worker.process.assert_called()
    
    @pytest.mark.asyncio
    async def test_event_retry_mechanism(
        self,
        event_bus: EventBus,
        ai_worker: AIWorker,
        sample_workflow_context: Dict[str, Any]
    ):
        """イベント処理のリトライメカニズムテスト."""
        workflow_id = sample_workflow_context["workflow_id"]
        
        # 最初はエラー、2回目は成功するようにモック
        call_count = 0
        
        async def mock_process(event):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("一時的なエラー")
            return "成功"
        
        ai_worker.process = mock_process
        
        # パラグラフ解析イベントを発行
        paragraph_event = create_test_event(
            EventType.PARAGRAPH_PARSED,
            workflow_id,
            {
                "paragraph_id": "p001",
                "content": "テストパラグラフ",
                "metadata": {"word_count": 50}
            }
        )
        
        await event_bus.publish(paragraph_event)
        
        # リトライ処理を待機
        await asyncio.sleep(1.0)
        
        # リトライが機能していることを確認
        assert call_count >= 2
    
    @pytest.mark.asyncio
    async def test_event_priority_handling(
        self,
        event_bus: EventBus,
        parser_worker: ParserWorker,
        sample_workflow_context: Dict[str, Any]
    ):
        """イベント優先度処理のテスト."""
        workflow_id = sample_workflow_context["workflow_id"]
        
        # 処理順序を追跡
        processing_order = []
        
        async def track_processing(event):
            processing_order.append(event.data.get("priority", 0))
        
        parser_worker.process = track_processing
        
        # 異なる優先度のイベントを発行
        low_priority_event = create_test_event(
            EventType.CHAPTER_PARSED,
            workflow_id,
            {"priority": 1, "chapter": "低優先度"}
        )
        low_priority_event.priority = 1
        
        high_priority_event = create_test_event(
            EventType.CHAPTER_PARSED,
            workflow_id,
            {"priority": 5, "chapter": "高優先度"}
        )
        high_priority_event.priority = 5
        
        medium_priority_event = create_test_event(
            EventType.CHAPTER_PARSED,
            workflow_id,
            {"priority": 3, "chapter": "中優先度"}
        )
        medium_priority_event.priority = 3
        
        # 順序を変えて発行
        await event_bus.publish(low_priority_event)
        await event_bus.publish(high_priority_event)
        await event_bus.publish(medium_priority_event)
        
        # 処理完了を待機
        await asyncio.sleep(0.2)
        
        # 優先度順に処理されたことを確認
        assert processing_order == [5, 3, 1]
    
    @pytest.mark.asyncio
    async def test_dead_letter_queue_handling(
        self,
        event_bus: EventBus,
        ai_worker: AIWorker,
        sample_workflow_context: Dict[str, Any]
    ):
        """デッドレターキュー処理のテスト."""
        workflow_id = sample_workflow_context["workflow_id"]
        
        # 常にエラーを発生させるモック
        ai_worker.process = AsyncMock(side_effect=Exception("永続的なエラー"))
        
        # イベントを発行
        problem_event = create_test_event(
            EventType.CONTENT_GENERATED,
            workflow_id,
            {"problematic": True}
        )
        
        await event_bus.publish(problem_event)
        
        # エラー処理を待機
        await asyncio.sleep(0.5)
        
        # デッドレターキューにイベントが移動したことを確認
        assert event_bus.dead_letter_queue.qsize() > 0
    
    @pytest.mark.asyncio
    async def test_event_tracing(
        self,
        event_bus: EventBus,
        parser_worker: ParserWorker,
        ai_worker: AIWorker,
        sample_workflow_context: Dict[str, Any]
    ):
        """イベントトレーシング機能のテスト."""
        workflow_id = sample_workflow_context["workflow_id"]
        trace_id = "trace-001"
        
        # トレースIDを含むイベントを発行
        traced_event = create_test_event(
            EventType.SECTION_PARSED,
            workflow_id,
            {"section": "test"}
        )
        traced_event.trace_id = trace_id
        
        # ワーカーの処理をモック（トレースIDを確認）
        received_trace_ids = []
        
        async def capture_trace_id(event):
            received_trace_ids.append(event.trace_id)
        
        parser_worker.process = capture_trace_id
        
        await event_bus.publish(traced_event)
        
        # 処理完了を待機
        await asyncio.sleep(0.1)
        
        # トレースIDが正しく伝播されたことを確認
        assert trace_id in received_trace_ids
    
    @pytest.mark.asyncio
    async def test_worker_load_balancing(
        self,
        event_bus: EventBus,
        test_config,
        sample_workflow_context: Dict[str, Any]
    ):
        """ワーカー間の負荷分散テスト."""
        workflow_id = sample_workflow_context["workflow_id"]
        
        # 複数のAIワーカーを作成
        ai_workers = []
        for i in range(3):
            worker = AIWorker(test_config, f"ai-worker-{i}")
            worker.process = AsyncMock()
            await worker.start(event_bus, None)
            ai_workers.append(worker)
        
        # 複数のイベントを発行
        events = []
        for i in range(9):
            event = create_test_event(
                EventType.PARAGRAPH_PARSED,
                workflow_id,
                {"paragraph_id": f"p{i:03d}"}
            )
            events.append(event)
        
        # 全イベントを発行
        for event in events:
            await event_bus.publish(event)
        
        # 処理完了を待機
        await asyncio.sleep(0.3)
        
        # 各ワーカーが適切に負荷分散されたことを確認
        total_calls = sum(worker.process.call_count for worker in ai_workers)
        assert total_calls == len(events)
        
        # 負荷がある程度均等に分散されたことを確認
        call_counts = [worker.process.call_count for worker in ai_workers]
        assert max(call_counts) - min(call_counts) <= 1 