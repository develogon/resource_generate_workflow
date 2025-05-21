import time
import random
import functools
import logging
from typing import Callable, Tuple, Any, TypeVar, Optional

logger = logging.getLogger(__name__)

# ジェネリック型変数
T = TypeVar('T')


def exponential_backoff(attempt: int, factor: float = 0.1) -> float:
    """
    指数バックオフアルゴリズムを使用して待機時間を計算します。
    
    Parameters
    ----------
    attempt : int
        試行回数（1から始まる）
    factor : float, optional
        基本待機時間の係数 (default: 0.1)
        
    Returns
    -------
    float
        計算された待機時間（秒）
    """
    # 待機時間 = 係数 * 2^(試行回数-1) + ランダムなジッター
    wait_time = factor * (2 ** (attempt - 1))
    
    # 最大20%のランダムなジッターを追加
    jitter = random.uniform(0, 0.2 * wait_time)
    total_wait = wait_time + jitter
    
    return total_wait


def retry_on_exception(max_attempts: int = 3, 
                       exceptions: Tuple[Exception, ...] = (Exception,),
                       backoff_factor: float = 0.1) -> Callable:
    """
    指定された例外が発生した場合にリトライを行うデコレータ。
    
    Parameters
    ----------
    max_attempts : int, optional
        最大試行回数 (default: 3)
    exceptions : tuple of Exception, optional
        リトライ対象の例外タイプ (default: (Exception,))
    backoff_factor : float, optional
        バックオフ計算の係数 (default: 0.1)
        
    Returns
    -------
    Callable
        デコレートされた関数
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            attempts = 0
            last_exception = None
            
            # 関数名を取得（モックオブジェクト対応）
            func_name = getattr(func, '__name__', str(func))
            
            while attempts < max_attempts:
                attempts += 1
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    # 最大試行回数に達した場合は例外を再発生
                    if attempts == max_attempts:
                        logger.error(f"Max retry attempts ({max_attempts}) reached for {func_name}. "
                                     f"Last error: {str(e)}")
                        raise
                    
                    # 待機時間を計算して待機
                    wait_time = exponential_backoff(attempts, backoff_factor)
                    logger.warning(f"Retry {attempts}/{max_attempts} for {func_name} "
                                   f"after {wait_time:.2f}s. Error: {str(e)}")
                    time.sleep(wait_time)
            
            # この行は実行されないはずだが、念のため
            if last_exception:
                raise last_exception
            
            raise RuntimeError("Unexpected error in retry mechanism")
        
        return wrapper
    
    return decorator


def retry_on_result(max_attempts: int = 3,
                   validate_result: Callable[[Any], bool] = None,
                   backoff_factor: float = 0.1) -> Callable:
    """
    関数の結果が特定の条件を満たさない場合にリトライを行うデコレータ。
    
    Parameters
    ----------
    max_attempts : int, optional
        最大試行回数 (default: 3)
    validate_result : callable, optional
        結果を検証する関数。Trueを返せば成功、Falseを返せば失敗 (default: None)
    backoff_factor : float, optional
        バックオフ計算の係数 (default: 0.1)
        
    Returns
    -------
    Callable
        デコレートされた関数
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            attempts = 0
            last_result = None
            
            # 関数名を取得（モックオブジェクト対応）
            func_name = getattr(func, '__name__', str(func))
            
            while attempts < max_attempts:
                attempts += 1
                result = func(*args, **kwargs)
                last_result = result
                
                # 検証関数がない場合や結果が有効な場合は結果を返す
                if validate_result is None or validate_result(result):
                    return result
                
                # 最大試行回数に達した場合は最後の結果を返す
                if attempts == max_attempts:
                    logger.warning(f"Max retry attempts ({max_attempts}) reached for {func_name}. "
                                  f"Returning last result.")
                    return last_result
                
                # 待機時間を計算して待機
                wait_time = exponential_backoff(attempts, backoff_factor)
                logger.warning(f"Retry {attempts}/{max_attempts} for {func_name} "
                              f"after {wait_time:.2f}s due to invalid result.")
                time.sleep(wait_time)
            
            # この行は実行されないはずだが、念のため
            return last_result
        
        return wrapper
    
    return decorator


def circuit_breaker(failure_threshold: int = 5, reset_timeout: int = 60) -> Callable:
    """
    サーキットブレーカーパターンを実装するデコレータ。
    一定回数の連続失敗があった場合、一定時間呼び出しを遮断します。
    
    Parameters
    ----------
    failure_threshold : int, optional
        回路を開くまでの連続失敗回数 (default: 5)
    reset_timeout : int, optional
        回路をリセット（半開状態）するまでの時間（秒） (default: 60)
        
    Returns
    -------
    Callable
        デコレートされた関数
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        # クロージャ内で状態を保持
        decorator.failure_count = 0
        decorator.is_open = False
        decorator.last_failure_time = 0
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            current_time = time.time()
            
            # 関数名を取得（モックオブジェクト対応）
            func_name = getattr(func, '__name__', str(func))
            
            # 回路が開いているか確認
            if decorator.is_open:
                # リセット時間が経過したかチェック
                if current_time - decorator.last_failure_time > reset_timeout:
                    # 回路を半開状態に設定
                    logger.info(f"Circuit half-open for {func_name}. "
                               f"Allowing one test request after {reset_timeout}s.")
                    # ここでは回路の状態は変更せず、1回のトライを許可
                else:
                    # リセット時間が経過していない場合は例外を発生
                    raise Exception(f"Circuit breaker is open for {func_name}. "
                                   f"Please retry after {reset_timeout}s.")
            
            try:
                # 関数を実行
                result = func(*args, **kwargs)
                
                # 成功した場合、失敗カウントをリセット
                decorator.failure_count = 0
                decorator.is_open = False
                
                return result
                
            except Exception as e:
                # 失敗カウントを増加
                decorator.failure_count += 1
                decorator.last_failure_time = current_time
                
                # 失敗閾値に達した場合、回路を開く
                if decorator.failure_count >= failure_threshold:
                    decorator.is_open = True
                    logger.warning(f"Circuit opened for {func_name} after {failure_threshold} "
                                  f"consecutive failures. Last error: {str(e)}")
                
                # 元の例外を再発生
                raise
        
        return wrapper
    
    return decorator 