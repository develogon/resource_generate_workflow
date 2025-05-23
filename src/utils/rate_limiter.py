"""レート制限ユーティリティ."""

import asyncio
import time
from typing import Dict, Optional

from .logger import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """レート制限器."""
    
    def __init__(self, requests_per_minute: int, service_name: str = "default"):
        self.requests_per_minute = requests_per_minute
        self.service_name = service_name
        self.request_times: list[float] = []
        self.lock = asyncio.Lock()
        
        # 1分間を秒に変換
        self.window_seconds = 60.0
        self.min_interval = self.window_seconds / requests_per_minute if requests_per_minute > 0 else 0
        
        logger.debug(f"RateLimiter initialized for {service_name}: {requests_per_minute} req/min")
        
    async def acquire(self) -> None:
        """レート制限チェックとリクエスト許可."""
        async with self.lock:
            current_time = time.time()
            
            # 古いリクエスト時間を削除（1分より古いもの）
            cutoff_time = current_time - self.window_seconds
            self.request_times = [t for t in self.request_times if t > cutoff_time]
            
            # レート制限チェック
            if len(self.request_times) >= self.requests_per_minute:
                # 最古のリクエストから1分経過するまで待機
                oldest_request = self.request_times[0]
                wait_time = self.window_seconds - (current_time - oldest_request)
                
                if wait_time > 0:
                    logger.debug(
                        f"Rate limit reached for {self.service_name}. "
                        f"Waiting {wait_time:.2f} seconds"
                    )
                    await asyncio.sleep(wait_time)
                    
                    # 再度古いリクエスト時間を削除
                    current_time = time.time()
                    cutoff_time = current_time - self.window_seconds
                    self.request_times = [t for t in self.request_times if t > cutoff_time]
            
            # 最小間隔制限
            if self.request_times and self.min_interval > 0:
                last_request = self.request_times[-1]
                interval_wait = self.min_interval - (current_time - last_request)
                
                if interval_wait > 0:
                    logger.debug(
                        f"Enforcing minimum interval for {self.service_name}. "
                        f"Waiting {interval_wait:.2f} seconds"
                    )
                    await asyncio.sleep(interval_wait)
                    current_time = time.time()
            
            # リクエスト時間を記録
            self.request_times.append(current_time)
            
    def release(self) -> None:
        """リクエスト完了通知（現在は何もしない）."""
        pass
        
    def get_stats(self) -> Dict[str, any]:
        """統計情報を取得."""
        current_time = time.time()
        cutoff_time = current_time - self.window_seconds
        
        # 現在のウィンドウ内のリクエスト数
        recent_requests = [t for t in self.request_times if t > cutoff_time]
        
        return {
            "service_name": self.service_name,
            "requests_per_minute": self.requests_per_minute,
            "current_requests_in_window": len(recent_requests),
            "remaining_requests": max(0, self.requests_per_minute - len(recent_requests)),
            "last_request_time": self.request_times[-1] if self.request_times else None,
        }
        
    def reset(self) -> None:
        """レート制限をリセット."""
        self.request_times.clear()
        logger.debug(f"Rate limiter reset for {self.service_name}")


class GlobalRateLimiter:
    """グローバルレート制限管理."""
    
    _limiters: Dict[str, RateLimiter] = {}
    
    @classmethod
    def get_limiter(cls, service_name: str, requests_per_minute: int) -> RateLimiter:
        """サービス用のレート制限器を取得または作成."""
        if service_name not in cls._limiters:
            cls._limiters[service_name] = RateLimiter(requests_per_minute, service_name)
        return cls._limiters[service_name]
        
    @classmethod
    def get_all_stats(cls) -> Dict[str, Dict[str, any]]:
        """全サービスの統計情報を取得."""
        return {name: limiter.get_stats() for name, limiter in cls._limiters.items()}
        
    @classmethod
    def reset_all(cls) -> None:
        """全てのレート制限をリセット."""
        for limiter in cls._limiters.values():
            limiter.reset()
        cls._limiters.clear() 