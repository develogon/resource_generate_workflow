"""パフォーマンス統合テスト."""

import pytest
import asyncio
import time
import psutil
import resource
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch, AsyncMock

from core.orchestrator import WorkflowOrchestrator
from core.events import EventBus
from workers.pool import WorkerPool
from utils.rate_limiter import RateLimiter
from utils.cache import CacheManager


class TestPerformanceIntegration:
    """パフォーマンス統合テストクラス."""
    
    @pytest.mark.asyncio
    async def test_throughput_performance(
        self,
        orchestrator: WorkflowOrchestrator,
        temp_dir,
        sample_markdown_content: str
    ):
        """スループットパフォーマンステスト."""
        # 複数の入力ファイルを準備
        input_dir = temp_dir / "input"
        input_dir.mkdir(exist_ok=True)
        
        num_files = 20
        input_files = []
        
        for i in range(num_files):
            input_file = input_dir / f"content_{i:03d}.md"
            content = sample_markdown_content.replace(
                "第1章: Pythonの基礎",
                f"第{i+1}章: コンテンツ{i+1}"
            )
            input_file.write_text(content, encoding="utf-8")
            input_files.append(str(input_file))
        
        # 処理時間の計測開始
        start_time = time.time()
        
        # 並列ワークフロー実行
        tasks = []
        for i, input_file in enumerate(input_files):
            task = orchestrator.execute(
                lang="ja",
                title=f"コンテンツ{i+1}",
                input_file=input_file
            )
            tasks.append(task)
        
        # 全タスクの完了を待機
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 処理時間の計測終了
        end_time = time.time()
        total_time = end_time - start_time
        
        # 成功したタスクの数を計算
        successful_results = [r for r in results if not isinstance(r, Exception)]
        
        # パフォーマンスメトリクスの計算
        throughput = len(successful_results) / total_time  # files per second
        avg_processing_time = total_time / len(successful_results) if successful_results else 0
        
        # パフォーマンス要件の確認
        assert len(successful_results) >= num_files * 0.9  # 90%以上成功
        assert throughput >= 0.5  # 最低0.5 files/second
        assert avg_processing_time <= 60.0  # 平均60秒以内
        
        print(f"スループット: {throughput:.2f} files/second")
        print(f"平均処理時間: {avg_processing_time:.2f} seconds")
        print(f"成功率: {len(successful_results)/num_files*100:.1f}%")
    
    @pytest.mark.asyncio
    async def test_latency_performance(
        self,
        event_bus: EventBus,
        ai_worker,
        sample_workflow_context: Dict[str, Any]
    ):
        """レイテンシパフォーマンステスト."""
        workflow_id = sample_workflow_context["workflow_id"]
        
        # 処理時間をシミュレート
        async def simulated_process(event):
            # 実際のAI処理をシミュレート（100-500ms）
            await asyncio.sleep(0.1 + (hash(str(event.data)) % 400) / 1000)
            return f"処理完了: {event.data.get('task_id')}"
        
        ai_worker.process = simulated_process
        
        # レイテンシ測定用のイベント
        num_events = 100
        latencies = []
        
        for i in range(num_events):
            start_time = time.time()
            
            from conftest import create_test_event
            from core.events import EventType
            
            event = create_test_event(
                EventType.PARAGRAPH_PARSED,
                workflow_id,
                {"task_id": f"task_{i:03d}", "data": f"test_data_{i}"}
            )
            
            await event_bus.publish(event)
            
            # 処理完了を待機（簡単な実装）
            await asyncio.sleep(0.6)  # 最大処理時間 + バッファ
            
            end_time = time.time()
            latency = (end_time - start_time) * 1000  # milliseconds
            latencies.append(latency)
        
        # レイテンシ統計の計算
        avg_latency = sum(latencies) / len(latencies)
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
        p99_latency = sorted(latencies)[int(len(latencies) * 0.99)]
        max_latency = max(latencies)
        
        # レイテンシ要件の確認
        assert avg_latency <= 1000  # 平均1秒以内
        assert p95_latency <= 2000  # 95%ile 2秒以内
        assert p99_latency <= 5000  # 99%ile 5秒以内
        
        print(f"平均レイテンシ: {avg_latency:.2f}ms")
        print(f"95%ile レイテンシ: {p95_latency:.2f}ms")
        print(f"99%ile レイテンシ: {p99_latency:.2f}ms")
        print(f"最大レイテンシ: {max_latency:.2f}ms")
    
    @pytest.mark.asyncio
    async def test_memory_usage_performance(
        self,
        orchestrator: WorkflowOrchestrator,
        temp_dir,
        sample_markdown_content: str
    ):
        """メモリ使用量パフォーマンステスト."""
        # 初期メモリ使用量を記録
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # 大量のデータを処理
        large_content = sample_markdown_content * 50  # 50倍に拡大
        
        input_dir = temp_dir / "input"
        input_dir.mkdir(exist_ok=True)
        input_file = input_dir / "large_content.md"
        input_file.write_text(large_content, encoding="utf-8")
        
        # メモリ使用量を監視しながら実行
        memory_snapshots = []
        
        async def memory_monitor():
            while True:
                memory_usage = process.memory_info().rss / 1024 / 1024  # MB
                memory_snapshots.append(memory_usage)
                await asyncio.sleep(0.5)
        
        # メモリ監視を開始
        monitor_task = asyncio.create_task(memory_monitor())
        
        try:
            # 大量データの処理
            result = await orchestrator.execute(
                lang="ja",
                title="大量データテスト",
                input_file=str(input_file)
            )
            
            # 処理完了を待機
            await asyncio.sleep(1.0)
            
        finally:
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass
        
        # 最終メモリ使用量を記録
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        peak_memory = max(memory_snapshots) if memory_snapshots else final_memory
        
        # メモリ使用量の計算
        memory_increase = final_memory - initial_memory
        peak_increase = peak_memory - initial_memory
        
        # メモリ使用量要件の確認
        assert memory_increase <= 500  # 最大500MB増加
        assert peak_increase <= 1000   # ピーク時最大1GB増加
        
        print(f"初期メモリ: {initial_memory:.2f}MB")
        print(f"最終メモリ: {final_memory:.2f}MB")
        print(f"ピークメモリ: {peak_memory:.2f}MB")
        print(f"メモリ増加: {memory_increase:.2f}MB")
        print(f"ピーク増加: {peak_increase:.2f}MB")
    
    @pytest.mark.asyncio
    async def test_concurrent_processing_performance(
        self,
        worker_pool: WorkerPool,
        event_bus: EventBus,
        sample_workflow_context: Dict[str, Any]
    ):
        """並行処理パフォーマンステスト."""
        workflow_id = sample_workflow_context["workflow_id"]
        
        # 並行処理数の段階的テスト
        concurrency_levels = [1, 5, 10, 20, 50]
        results = {}
        
        for concurrency in concurrency_levels:
            # 処理時間をシミュレート
            async def timed_process(event):
                await asyncio.sleep(0.1)  # 100ms processing time
                return f"Processed: {event.data['task_id']}"
            
            # ワーカーのモック設定
            for worker_type in ["parser", "ai", "media"]:
                workers = worker_pool.get_workers(worker_type)
                for worker in workers[:concurrency]:  # 指定数のワーカーのみ使用
                    worker.process = timed_process
            
            # 並行タスクの実行
            start_time = time.time()
            
            tasks = []
            for i in range(concurrency * 2):  # ワーカー数の2倍のタスク
                from conftest import create_test_event
                from core.events import EventType
                
                event = create_test_event(
                    EventType.PARAGRAPH_PARSED,
                    workflow_id,
                    {"task_id": f"task_{i:03d}"}
                )
                task = asyncio.create_task(
                    worker_pool.get_worker("ai").process(event)
                )
                tasks.append(task)
            
            # 全タスクの完了を待機
            await asyncio.gather(*tasks, return_exceptions=True)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            results[concurrency] = {
                "time": total_time,
                "throughput": (concurrency * 2) / total_time
            }
        
        # 並行処理効率の確認
        for concurrency in concurrency_levels[1:]:
            prev_concurrency = concurrency_levels[concurrency_levels.index(concurrency) - 1]
            
            current_throughput = results[concurrency]["throughput"]
            prev_throughput = results[prev_concurrency]["throughput"]
            
            # スループットの向上を確認（理想的には線形スケーリング）
            efficiency = current_throughput / (prev_throughput * (concurrency / prev_concurrency))
            
            print(f"並行数 {concurrency}: {current_throughput:.2f} tasks/sec, 効率: {efficiency:.2f}")
            
            # 最低50%の効率を期待
            assert efficiency >= 0.5
    
    @pytest.mark.asyncio
    async def test_rate_limiting_performance(
        self,
        test_config
    ):
        """レート制限パフォーマンステスト."""
        # レート制限器の設定（10 requests/second）
        rate_limiter = RateLimiter(requests_per_second=10)
        
        # 大量のリクエストを送信
        num_requests = 50
        request_times = []
        
        async def rate_limited_request(request_id: int):
            start_time = time.time()
            
            await rate_limiter.acquire()
            
            # 模擬的なAPI呼び出し
            await asyncio.sleep(0.01)  # 10ms processing
            
            rate_limiter.release()
            
            end_time = time.time()
            return {
                "request_id": request_id,
                "duration": end_time - start_time,
                "timestamp": end_time
            }
        
        # 並列リクエストの実行
        start_time = time.time()
        
        tasks = []
        for i in range(num_requests):
            task = rate_limited_request(i)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # レート制限の効果を確認
        actual_rate = num_requests / total_time
        expected_rate = 10.0  # requests/second
        
        # 実際のレートが期待値に近いことを確認（±20%の許容範囲）
        assert abs(actual_rate - expected_rate) / expected_rate <= 0.2
        
        # リクエスト間隔の確認
        timestamps = [r["timestamp"] for r in results]
        timestamps.sort()
        
        intervals = []
        for i in range(1, len(timestamps)):
            interval = timestamps[i] - timestamps[i-1]
            intervals.append(interval)
        
        avg_interval = sum(intervals) / len(intervals)
        expected_interval = 1.0 / expected_rate  # 0.1 seconds
        
        # 平均間隔が期待値に近いことを確認
        assert abs(avg_interval - expected_interval) / expected_interval <= 0.3
        
        print(f"実際のレート: {actual_rate:.2f} req/sec")
        print(f"期待レート: {expected_rate:.2f} req/sec")
        print(f"平均間隔: {avg_interval:.3f} sec")
        print(f"期待間隔: {expected_interval:.3f} sec")
    
    @pytest.mark.asyncio
    async def test_cache_performance(
        self,
        test_config
    ):
        """キャッシュパフォーマンステスト."""
        cache_manager = CacheManager(test_config)
        
        # キャッシュ性能のテスト
        num_operations = 1000
        cache_keys = [f"key_{i:04d}" for i in range(num_operations)]
        cache_values = [f"value_{i:04d}" * 100 for i in range(num_operations)]  # 大きなデータ
        
        # 書き込み性能のテスト
        start_time = time.time()
        
        write_tasks = []
        for key, value in zip(cache_keys, cache_values):
            task = cache_manager.set(key, value, ttl=300)
            write_tasks.append(task)
        
        await asyncio.gather(*write_tasks)
        
        write_time = time.time() - start_time
        write_throughput = num_operations / write_time
        
        # 読み込み性能のテスト
        start_time = time.time()
        
        read_tasks = []
        for key in cache_keys:
            task = cache_manager.get(key)
            read_tasks.append(task)
        
        read_results = await asyncio.gather(*read_tasks)
        
        read_time = time.time() - start_time
        read_throughput = num_operations / read_time
        
        # キャッシュヒット率の確認
        cache_hits = sum(1 for result in read_results if result is not None)
        hit_rate = cache_hits / num_operations
        
        # パフォーマンス要件の確認
        assert write_throughput >= 100   # 最低100 ops/sec
        assert read_throughput >= 500    # 最低500 ops/sec
        assert hit_rate >= 0.95          # 95%以上のヒット率
        
        print(f"書き込みスループット: {write_throughput:.2f} ops/sec")
        print(f"読み込みスループット: {read_throughput:.2f} ops/sec")
        print(f"キャッシュヒット率: {hit_rate:.3f}")
    
    @pytest.mark.asyncio
    async def test_scalability_limits(
        self,
        event_bus: EventBus,
        sample_workflow_context: Dict[str, Any]
    ):
        """スケーラビリティ限界テスト."""
        workflow_id = sample_workflow_context["workflow_id"]
        
        # 段階的に負荷を増やしてテスト
        load_levels = [100, 500, 1000, 2000, 5000]
        performance_results = {}
        
        for load_level in load_levels:
            print(f"負荷レベル {load_level} をテスト中...")
            
            # 負荷生成
            start_time = time.time()
            success_count = 0
            error_count = 0
            
            async def generate_load():
                nonlocal success_count, error_count
                try:
                    from conftest import create_test_event
                    from core.events import EventType
                    
                    event = create_test_event(
                        EventType.PARAGRAPH_PARSED,
                        workflow_id,
                        {"load_test": True}
                    )
                    
                    await event_bus.publish(event)
                    success_count += 1
                    
                except Exception:
                    error_count += 1
            
            # 負荷レベルに応じたタスクを並列実行
            tasks = [generate_load() for _ in range(load_level)]
            
            await asyncio.gather(*tasks, return_exceptions=True)
            
            end_time = time.time()
            duration = end_time - start_time
            
            # パフォーマンス指標の計算
            total_requests = success_count + error_count
            success_rate = success_count / total_requests if total_requests > 0 else 0
            throughput = success_count / duration
            
            performance_results[load_level] = {
                "duration": duration,
                "success_rate": success_rate,
                "throughput": throughput,
                "errors": error_count
            }
            
            # 極端な性能劣化をチェック
            if success_rate < 0.5:  # 成功率50%を下回ったら限界
                print(f"スケーラビリティ限界に到達: {load_level} requests")
                break
        
        # スケーラビリティの評価
        for load_level, result in performance_results.items():
            print(f"負荷 {load_level}: 成功率 {result['success_rate']:.3f}, "
                  f"スループット {result['throughput']:.2f} req/sec")
            
            # 最低限の性能要件
            if load_level <= 1000:  # 1000リクエストまでは高い性能を期待
                assert result["success_rate"] >= 0.9
                assert result["throughput"] >= load_level / 10  # 最低10秒以内
    
    def test_resource_usage_limits(self):
        """リソース使用量制限テスト."""
        # CPU使用率の監視
        cpu_percent = psutil.cpu_percent(interval=1.0)
        
        # メモリ使用量の監視
        memory = psutil.virtual_memory()
        memory_usage_percent = memory.percent
        
        # ディスク使用量の監視
        disk = psutil.disk_usage('/')
        disk_usage_percent = disk.used / disk.total * 100
        
        # ファイルディスクリプタの使用量
        process = psutil.Process()
        num_fds = process.num_fds() if hasattr(process, 'num_fds') else 0
        
        # リソース制限の確認
        assert cpu_percent <= 80.0          # CPU使用率80%以下
        assert memory_usage_percent <= 85.0  # メモリ使用率85%以下
        assert disk_usage_percent <= 90.0    # ディスク使用率90%以下
        assert num_fds <= 1000               # ファイルディスクリプタ1000以下
        
        print(f"CPU使用率: {cpu_percent:.1f}%")
        print(f"メモリ使用率: {memory_usage_percent:.1f}%")
        print(f"ディスク使用率: {disk_usage_percent:.1f}%")
        print(f"ファイルディスクリプタ数: {num_fds}") 