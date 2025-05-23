"""リトライシステム."""

from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, Callable, Optional, Type, Union

from tenacity import (
    AsyncRetrying,
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    wait_fixed,
    wait_random,
)


@dataclass
class RetryConfig:
    """リトライ設定."""
    
    max_attempts: int = 3
    wait_strategy: str = "exponential"  # exponential, fixed, random
    wait_min: float = 1.0
    wait_max: float = 60.0
    wait_multiplier: float = 2.0
    jitter: bool = True
    retry_exceptions: tuple[Type[Exception], ...] = field(
        default_factory=lambda: (Exception,)
    )
    stop_exceptions: tuple[Type[Exception], ...] = field(default_factory=tuple)
    
    def create_tenacity_retry(self):
        """tenacityのリトライオブジェクトを作成."""
        # 停止戦略
        stop_strategy = stop_after_attempt(self.max_attempts)
        
        # 待機戦略
        if self.wait_strategy == "exponential":
            wait_strategy = wait_exponential(
                multiplier=self.wait_multiplier,
                min=self.wait_min,
                max=self.wait_max
            )
        elif self.wait_strategy == "fixed":
            wait_strategy = wait_fixed(self.wait_min)
        elif self.wait_strategy == "random":
            wait_strategy = wait_random(min=self.wait_min, max=self.wait_max)
        else:
            wait_strategy = wait_exponential(
                multiplier=self.wait_multiplier,
                min=self.wait_min,
                max=self.wait_max
            )
        
        # ジッターの追加
        if self.jitter and self.wait_strategy != "random":
            wait_strategy = wait_strategy + wait_random(0, 1)
        
        # リトライ条件
        retry_condition = retry_if_exception_type(self.retry_exceptions)
        
        return Retrying(
            stop=stop_strategy,
            wait=wait_strategy,
            retry=retry_condition,
            reraise=True
        )
    
    def create_async_tenacity_retry(self):
        """非同期tenacityのリトライオブジェクトを作成."""
        # 停止戦略
        stop_strategy = stop_after_attempt(self.max_attempts)
        
        # 待機戦略
        if self.wait_strategy == "exponential":
            wait_strategy = wait_exponential(
                multiplier=self.wait_multiplier,
                min=self.wait_min,
                max=self.wait_max
            )
        elif self.wait_strategy == "fixed":
            wait_strategy = wait_fixed(self.wait_min)
        elif self.wait_strategy == "random":
            wait_strategy = wait_random(min=self.wait_min, max=self.wait_max)
        else:
            wait_strategy = wait_exponential(
                multiplier=self.wait_multiplier,
                min=self.wait_min,
                max=self.wait_max
            )
        
        # ジッターの追加
        if self.jitter and self.wait_strategy != "random":
            wait_strategy = wait_strategy + wait_random(0, 1)
        
        # リトライ条件
        retry_condition = retry_if_exception_type(self.retry_exceptions)
        
        return AsyncRetrying(
            stop=stop_strategy,
            wait=wait_strategy,
            retry=retry_condition,
            reraise=True
        )


def retry_with_config(config: RetryConfig):
    """設定に基づくリトライデコレータ."""
    def decorator(func: Callable) -> Callable:
        retry_obj = config.create_tenacity_retry()
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            return retry_obj(func, *args, **kwargs)
        
        return wrapper
    return decorator


def async_retry_with_config(config: RetryConfig):
    """設定に基づく非同期リトライデコレータ."""
    def decorator(func: Callable) -> Callable:
        retry_obj = config.create_async_tenacity_retry()
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await retry_obj(func, *args, **kwargs)
        
        return wrapper
    return decorator


async def retry_async(
    func: Callable,
    max_attempts: int = 3,
    wait_strategy: str = "exponential",
    wait_min: float = 1.0,
    wait_max: float = 60.0,
    wait_multiplier: float = 2.0,
    jitter: bool = True,
    retry_exceptions: tuple[Type[Exception], ...] = (Exception,),
    stop_exceptions: tuple[Type[Exception], ...] = (),
    on_retry: Optional[Callable] = None,
    *args,
    **kwargs
) -> Any:
    """非同期関数のリトライ実行."""
    config = RetryConfig(
        max_attempts=max_attempts,
        wait_strategy=wait_strategy,
        wait_min=wait_min,
        wait_max=wait_max,
        wait_multiplier=wait_multiplier,
        jitter=jitter,
        retry_exceptions=retry_exceptions,
        stop_exceptions=stop_exceptions
    )
    
    last_exception = None
    
    for attempt in range(max_attempts):
        try:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        
        except stop_exceptions:
            # 停止例外の場合は即座に終了
            raise
        
        except retry_exceptions as e:
            last_exception = e
            
            if attempt == max_attempts - 1:
                # 最後の試行の場合は例外を再発生
                raise
            
            # リトライコールバックの実行
            if on_retry:
                try:
                    if asyncio.iscoroutinefunction(on_retry):
                        await on_retry(attempt + 1, e)
                    else:
                        on_retry(attempt + 1, e)
                except Exception:
                    # コールバックのエラーは無視
                    pass
            
            # 待機時間の計算
            wait_time = _calculate_wait_time(
                attempt,
                wait_strategy,
                wait_min,
                wait_max,
                wait_multiplier,
                jitter
            )
            
            await asyncio.sleep(wait_time)
    
    # ここに到達することはないはずだが、念のため
    if last_exception:
        raise last_exception


def retry_sync(
    func: Callable,
    max_attempts: int = 3,
    wait_strategy: str = "exponential",
    wait_min: float = 1.0,
    wait_max: float = 60.0,
    wait_multiplier: float = 2.0,
    jitter: bool = True,
    retry_exceptions: tuple[Type[Exception], ...] = (Exception,),
    stop_exceptions: tuple[Type[Exception], ...] = (),
    on_retry: Optional[Callable] = None,
    *args,
    **kwargs
) -> Any:
    """同期関数のリトライ実行."""
    last_exception = None
    
    for attempt in range(max_attempts):
        try:
            return func(*args, **kwargs)
        
        except stop_exceptions:
            # 停止例外の場合は即座に終了
            raise
        
        except retry_exceptions as e:
            last_exception = e
            
            if attempt == max_attempts - 1:
                # 最後の試行の場合は例外を再発生
                raise
            
            # リトライコールバックの実行
            if on_retry:
                try:
                    on_retry(attempt + 1, e)
                except Exception:
                    # コールバックのエラーは無視
                    pass
            
            # 待機時間の計算
            wait_time = _calculate_wait_time(
                attempt,
                wait_strategy,
                wait_min,
                wait_max,
                wait_multiplier,
                jitter
            )
            
            time.sleep(wait_time)
    
    # ここに到達することはないはずだが、念のため
    if last_exception:
        raise last_exception


def _calculate_wait_time(
    attempt: int,
    strategy: str,
    wait_min: float,
    wait_max: float,
    multiplier: float,
    jitter: bool
) -> float:
    """待機時間を計算."""
    if strategy == "fixed":
        wait_time = wait_min
    elif strategy == "random":
        wait_time = random.uniform(wait_min, wait_max)
    elif strategy == "exponential":
        wait_time = min(wait_min * (multiplier ** attempt), wait_max)
    else:
        wait_time = min(wait_min * (multiplier ** attempt), wait_max)
    
    # ジッターの追加
    if jitter and strategy != "random":
        jitter_amount = random.uniform(0, min(wait_time * 0.1, 1.0))
        wait_time += jitter_amount
    
    return wait_time


class RetryableError(Exception):
    """リトライ可能なエラー."""
    pass


class NonRetryableError(Exception):
    """リトライ不可能なエラー."""
    pass


def create_retry_decorator(
    max_attempts: int = 3,
    wait_strategy: str = "exponential",
    wait_min: float = 1.0,
    wait_max: float = 60.0,
    wait_multiplier: float = 2.0,
    jitter: bool = True,
    retry_exceptions: tuple[Type[Exception], ...] = (RetryableError,),
    stop_exceptions: tuple[Type[Exception], ...] = (NonRetryableError,),
    on_retry: Optional[Callable] = None
):
    """カスタムリトライデコレータを作成."""
    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await retry_async(
                    func,
                    max_attempts=max_attempts,
                    wait_strategy=wait_strategy,
                    wait_min=wait_min,
                    wait_max=wait_max,
                    wait_multiplier=wait_multiplier,
                    jitter=jitter,
                    retry_exceptions=retry_exceptions,
                    stop_exceptions=stop_exceptions,
                    on_retry=on_retry,
                    *args,
                    **kwargs
                )
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                return retry_sync(
                    func,
                    max_attempts=max_attempts,
                    wait_strategy=wait_strategy,
                    wait_min=wait_min,
                    wait_max=wait_max,
                    wait_multiplier=wait_multiplier,
                    jitter=jitter,
                    retry_exceptions=retry_exceptions,
                    stop_exceptions=stop_exceptions,
                    on_retry=on_retry,
                    *args,
                    **kwargs
                )
            return sync_wrapper
    
    return decorator


# よく使用されるリトライ設定のプリセット
QUICK_RETRY = RetryConfig(
    max_attempts=3,
    wait_strategy="fixed",
    wait_min=0.5,
    wait_max=2.0,
    jitter=True
)

AGGRESSIVE_RETRY = RetryConfig(
    max_attempts=5,
    wait_strategy="exponential",
    wait_min=1.0,
    wait_max=30.0,
    wait_multiplier=2.0,
    jitter=True
)

CONSERVATIVE_RETRY = RetryConfig(
    max_attempts=2,
    wait_strategy="fixed",
    wait_min=2.0,
    wait_max=5.0,
    jitter=False
)

NETWORK_RETRY = RetryConfig(
    max_attempts=4,
    wait_strategy="exponential",
    wait_min=1.0,
    wait_max=60.0,
    wait_multiplier=2.0,
    jitter=True,
    retry_exceptions=(ConnectionError, TimeoutError, RetryableError),
    stop_exceptions=(ValueError, TypeError, NonRetryableError)
) 