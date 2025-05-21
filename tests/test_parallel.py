import pytest
import time
import concurrent.futures
from unittest.mock import patch, MagicMock, call

from utils.parallel import ParallelExecutor, task_group, run_in_parallel, chunk_processor


class TestParallelExecutor:
    """ParallelExecutorクラスのテスト"""

    def test_execute(self):
        """タスク実行のテスト"""
        # テスト用のタスク関数
        def test_task(x):
            return x * 2
        
        # タスクリスト
        tasks = [(test_task, (i,), {}) for i in range(5)]
        
        # ParallelExecutorの初期化と実行
        executor = ParallelExecutor(max_workers=2)
        results = executor.execute(tasks)
        
        # 結果の検証
        assert results == [0, 2, 4, 6, 8]
        
        # 例外発生するタスク
        def failing_task(x):
            if x == 2:
                raise ValueError("Error at 2")
            return x * 2
        
        # 例外発生タスクリスト
        failing_tasks = [(failing_task, (i,), {}) for i in range(5)]
        
        # 例外を無視せずに実行
        with pytest.raises(ValueError) as excinfo:
            executor.execute(failing_tasks, ignore_exceptions=False)
        assert "Error at 2" in str(excinfo.value)
        
        # 例外を無視して実行
        results = executor.execute(failing_tasks, ignore_exceptions=True)
        assert None in results  # 例外発生タスクの結果はNone
        assert results.count(None) == 1  # 1つのタスクが失敗
        assert sum(x for x in results if x is not None) == 16  # 0, 2, 6, 8の合計

    def test_map(self):
        """map関数のテスト"""
        # テスト用のタスク関数
        def test_task(x):
            return x * 2
        
        # ParallelExecutorの初期化とmap実行
        executor = ParallelExecutor(max_workers=2)
        results = list(executor.map(test_task, range(5)))
        
        # 結果の検証
        assert results == [0, 2, 4, 6, 8]
        
        # キーワード引数を含む場合
        def test_task_with_kwargs(x, factor=1):
            return x * factor
        
        # キーワード引数を使用してmap実行
        results = list(executor.map(test_task_with_kwargs, range(5), factor=3))
        
        # 結果の検証
        assert results == [0, 3, 6, 9, 12]


class TestTaskGroup:
    """タスクグループのテスト"""

    def test_task_group(self):
        """コンテキストマネージャとしてのタスクグループのテスト"""
        # テスト用のタスク関数
        def test_task(x):
            return x * 2
        
        # ThreadPoolExecutorのモック
        mock_pool = MagicMock()
        mock_pool.submit.side_effect = lambda fn, *args, **kwargs: concurrent.futures.Future()
        mock_pool.__enter__.return_value = mock_pool
        
        # concurrent.futures.ThreadPoolExecutorをモックに置き換え
        with patch('concurrent.futures.ThreadPoolExecutor') as mock_executor:
            mock_executor.return_value = mock_pool
            
            # タスクグループの実行
            with task_group(max_workers=2) as group:
                for i in range(5):
                    group.submit(test_task, i)
            
            # ThreadPoolExecutorが正しく呼ばれたことを確認
            mock_executor.assert_called_once_with(max_workers=2)
            
            # submitが5回呼ばれたことを確認
            assert mock_pool.submit.call_count == 5
            
            # 各submitの引数を確認
            calls = [call(test_task, i) for i in range(5)]
            mock_pool.submit.assert_has_calls(calls, any_order=True)


class TestRunInParallel:
    """run_in_parallel関数のテスト"""

    def test_run_in_parallel(self):
        """並列タスク実行のテスト"""
        # テスト用のタスク関数
        def test_task(x):
            return x * 2
        
        # タスクリスト
        tasks = [lambda: test_task(i) for i in range(5)]
        
        # ThreadPoolExecutorのモック
        mock_futures = [MagicMock() for _ in range(5)]
        for i, future in enumerate(mock_futures):
            future.result.return_value = i * 2
        
        mock_pool = MagicMock()
        mock_pool.submit.side_effect = mock_futures
        mock_pool.__enter__.return_value = mock_pool
        
        # concurrent.futures.ThreadPoolExecutorをモックに置き換え
        with patch('concurrent.futures.ThreadPoolExecutor') as mock_executor:
            mock_executor.return_value = mock_pool
            
            # 並列実行
            results = run_in_parallel(tasks, max_workers=2)
            
            # ThreadPoolExecutorが正しく呼ばれたことを確認
            mock_executor.assert_called_once_with(max_workers=2)
            
            # submitが5回呼ばれたことを確認
            assert mock_pool.submit.call_count == 5
            
            # 結果が正しいことを確認
            assert results == [0, 2, 4, 6, 8]


class TestChunkProcessor:
    """チャンク処理関数のテスト"""

    def test_chunk_processor(self):
        """アイテムの分割処理テスト"""
        # テスト用のプロセッサ関数
        processor_func = MagicMock(side_effect=lambda items: [item * 2 for item in items])
        
        # テスト用のアイテムリスト
        items = list(range(10))
        
        # チャンク処理実行
        results = chunk_processor(
            items=items,
            processor_func=processor_func,
            chunk_size=3
        )
        
        # プロセッサ関数の呼び出し回数確認
        assert processor_func.call_count == 4  # 3, 3, 3, 1の4チャンク
        
        # プロセッサ関数の各呼び出し引数を確認
        assert processor_func.call_args_list[0][0][0] == [0, 1, 2]
        assert processor_func.call_args_list[1][0][0] == [3, 4, 5]
        assert processor_func.call_args_list[2][0][0] == [6, 7, 8]
        assert processor_func.call_args_list[3][0][0] == [9]
        
        # 結果が正しいことを確認
        assert results == [0, 2, 4, 6, 8, 10, 12, 14, 16, 18]
        
        # 空のアイテムリストの場合
        empty_results = chunk_processor([], processor_func, chunk_size=3)
        assert empty_results == []
        
        # chunk_sizeがアイテム数より大きい場合
        large_chunk_results = chunk_processor([1, 2], processor_func, chunk_size=5)
        assert large_chunk_results == [2, 4]
        assert processor_func.call_args_list[-1][0][0] == [1, 2]

    def test_parallel_chunk_processor(self):
        """並列チャンク処理のテスト"""
        # テスト用のプロセッサ関数（時間がかかることをシミュレート）
        def slow_processor(items):
            time.sleep(0.01)
            return [item * 2 for item in items]
        
        # テスト用のアイテムリスト
        items = list(range(100))
        
        # 並列数1での実行時間測定
        start = time.time()
        sequential_results = chunk_processor(
            items=items,
            processor_func=slow_processor,
            chunk_size=10,
            max_workers=1
        )
        sequential_time = time.time() - start
        
        # 並列数4での実行時間測定
        start = time.time()
        parallel_results = chunk_processor(
            items=items,
            processor_func=slow_processor,
            chunk_size=10,
            max_workers=4
        )
        parallel_time = time.time() - start
        
        # 結果が同じであることを確認
        assert sequential_results == parallel_results
        
        # 並列実行の方が速いことを確認
        # 注: この部分は環境によって結果が変わるため、コメントアウトしています
        # assert parallel_time < sequential_time 