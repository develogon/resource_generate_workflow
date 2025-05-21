import concurrent.futures
import logging
from typing import List, Callable, Any, Tuple, Dict, Iterable, Generator, Optional, TypeVar, Iterator
from contextlib import contextmanager

logger = logging.getLogger(__name__)

T = TypeVar('T')
R = TypeVar('R')


class ParallelExecutor:
    """
    複数のタスクを並列実行するクラス。
    ThreadPoolExecutorを使用してタスクを実行します。
    """
    
    def __init__(self, max_workers: Optional[int] = None):
        """
        Parameters
        ----------
        max_workers : int, optional
            同時実行できるワーカー数、Noneの場合はデフォルト（CPUコア数 * 5）
        """
        self.max_workers = max_workers
    
    def execute(self, tasks: List[Tuple[Callable, Tuple, Dict]], ignore_exceptions: bool = False) -> List[Any]:
        """
        複数のタスクを並列実行します。
        
        Parameters
        ----------
        tasks : list of (function, args, kwargs)
            実行するタスクの関数、引数、キーワード引数のタプルのリスト
        ignore_exceptions : bool, optional
            Trueの場合、実行中に例外が発生してもその結果をNoneとして処理を続行 (default: False)
            Falseの場合、例外が発生すると中断して例外を再発生
            
        Returns
        -------
        list
            各タスクの実行結果のリスト。ignore_exceptions=Trueの場合、例外が発生したタスクの結果はNone
            
        Raises
        ------
        Exception
            ignore_exceptions=Falseの場合、発生した例外を再発生
        """
        results = [None] * len(tasks)  # タスク数分の結果リストを初期化
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # タスクを並列で実行し、Future オブジェクトを順序と関連付ける
            futures = []
            for i, (task, args, kwargs) in enumerate(tasks):
                future = executor.submit(task, *args, **kwargs)
                futures.append((i, future))
            
            # 結果を収集（元の順序を保持）
            for i, future in futures:
                try:
                    results[i] = future.result()
                except Exception as e:
                    if ignore_exceptions:
                        logger.warning(f"タスク実行中に例外が発生しましたが無視します: {str(e)}")
                        results[i] = None
                    else:
                        logger.error(f"タスク実行中に例外が発生しました: {str(e)}")
                        raise
        
        return results
    
    def map(self, fn: Callable[..., R], *iterables: Iterable, **kwargs) -> Generator[R, None, None]:
        """
        Pythonの組み込みmap関数の並列版。
        複数のイテラブルの要素に関数を適用した結果を返します。
        
        Parameters
        ----------
        fn : callable
            各要素に適用する関数
        *iterables : iterable
            関数に渡す引数のイテラブル
        **kwargs : dict
            関数に渡す追加のキーワード引数
            
        Returns
        -------
        generator
            fn(i1, i2, ..., **kwargs)の結果を返すジェネレータ
        """
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # *iterablesの要素に関数を適用
            futures = [executor.submit(fn, *args, **kwargs) for args in zip(*iterables)]
            
            # 結果を順番に返す
            for future in futures:
                yield future.result()


@contextmanager
def task_group(max_workers: Optional[int] = None):
    """
    タスクグループのコンテキストマネージャ。
    複数の非同期タスクをグループとして管理するためのヘルパー。
    
    Parameters
    ----------
    max_workers : int, optional
        同時実行できるワーカー数、Noneの場合はデフォルト（CPUコア数 * 5）
        
    Yields
    ------
    ThreadPoolExecutor
        タスク実行のためのエグゼキュータインスタンス
    
    Examples
    --------
    >>> with task_group() as group:
    >>>     future1 = group.submit(func1, arg1, arg2)
    >>>     future2 = group.submit(func2, arg3)
    >>> # グループを抜けると、すべてのタスクの完了を待機
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        yield executor
        # コンテキストを抜けるとexecutorのシャットダウンが自動的に処理される


def run_in_parallel(tasks: List[Callable[[], T]], max_workers: Optional[int] = None) -> List[T]:
    """
    引数を取らない関数（クロージャ）のリストを並列実行します。
    
    Parameters
    ----------
    tasks : list of callable
        実行する引数なしの関数リスト
    max_workers : int, optional
        同時実行できるワーカー数、Noneの場合はデフォルト（CPUコア数 * 5）
        
    Returns
    -------
    list
        各タスクの実行結果のリスト
    """
    results = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # タスクを並列で実行
        futures = [executor.submit(task) for task in tasks]
        
        # 結果を収集（順序を維持）
        for future in futures:
            result = future.result()
            results.append(result)
    
    return results


def chunk_processor(items: List[T], 
                   processor_func: Callable[[List[T]], List[R]], 
                   chunk_size: int = 10,
                   max_workers: Optional[int] = None) -> List[R]:
    """
    大きなリストを指定サイズのチャンクに分割して処理し、結果を連結します。
    オプションで並列処理も行えます。
    
    Parameters
    ----------
    items : list
        処理するアイテムのリスト
    processor_func : callable
        チャンク処理関数。アイテムのリストを受け取り、処理結果のリストを返す関数
    chunk_size : int, optional
        チャンクのサイズ (default: 10)
    max_workers : int, optional
        並列実行する場合のワーカー数、1の場合は逐次処理 (default: None)
        
    Returns
    -------
    list
        連結された処理結果のリスト
    """
    if not items:
        return []
    
    # アイテムをチャンクに分割（順序を維持）
    chunks = []
    for i in range(0, len(items), chunk_size):
        chunks.append(items[i:i + chunk_size])
    
    # チャンクの処理（順序を維持）
    all_results = []
    
    if max_workers == 1 or max_workers is None:
        # 逐次処理
        for chunk in chunks:
            result = processor_func(chunk)
            all_results.extend(result)
    else:
        # 並列処理
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(processor_func, chunk) for chunk in chunks]
            for future in futures:
                result = future.result()
                all_results.extend(result)
    
    return all_results 