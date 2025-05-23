"""外部サービスクライアントの基底クラス."""

import asyncio
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, TypeVar

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config.settings import Config
from ..utils.logger import get_logger
from ..utils.rate_limiter import RateLimiter

logger = get_logger(__name__)

T = TypeVar('T')


class ClientError(Exception):
    """クライアントエラーの基底クラス."""
    pass


class RateLimitError(ClientError):
    """レート制限エラー."""
    pass


class AuthenticationError(ClientError):
    """認証エラー."""
    pass


class APIError(ClientError):
    """API エラー."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[Dict] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class BaseClient(ABC):
    """外部サービスクライアントの基底クラス."""
    
    def __init__(self, config: Config, service_name: str):
        self.config = config
        self.service_name = service_name
        self.logger = get_logger(f"{__name__}.{service_name}")
        
        # HTTPクライアントの初期化
        self.client = httpx.AsyncClient(
            timeout=config.api_timeout,
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
        )
        
        # レート制限器
        self.rate_limiter = RateLimiter(
            requests_per_minute=self._get_rate_limit(),
            service_name=service_name
        )
        
        # メトリクス用の統計
        self.stats = {
            "requests_made": 0,
            "requests_failed": 0,
            "total_time": 0.0,
            "last_request_time": None
        }
        
    @abstractmethod
    def _get_rate_limit(self) -> int:
        """サービス固有のレート制限を取得."""
        pass
        
    @abstractmethod
    def _get_headers(self) -> Dict[str, str]:
        """リクエストヘッダーを取得."""
        pass
        
    @abstractmethod
    async def _handle_response(self, response: httpx.Response) -> Dict[str, Any]:
        """レスポンスを処理."""
        pass
        
    async def __aenter__(self):
        """非同期コンテキストマネージャーの開始."""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """非同期コンテキストマネージャーの終了."""
        await self.close()
        
    async def close(self):
        """クライアントを閉じる."""
        await self.client.aclose()
        
    def _record_stats(self, duration: float, success: bool = True):
        """統計を記録."""
        self.stats["requests_made"] += 1
        self.stats["total_time"] += duration
        self.stats["last_request_time"] = time.time()
        
        if not success:
            self.stats["requests_failed"] += 1
            
    def get_stats(self) -> Dict[str, Any]:
        """統計情報を取得."""
        stats = self.stats.copy()
        if stats["requests_made"] > 0:
            stats["average_time"] = stats["total_time"] / stats["requests_made"]
            stats["failure_rate"] = stats["requests_failed"] / stats["requests_made"]
        else:
            stats["average_time"] = 0.0
            stats["failure_rate"] = 0.0
        return stats
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        reraise=True
    )
    async def _make_request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> Dict[str, Any]:
        """HTTPリクエストを実行（リトライ付き）."""
        # レート制限
        await self.rate_limiter.acquire()
        
        start_time = time.time()
        
        try:
            # ヘッダーの設定
            headers = kwargs.get('headers', {})
            headers.update(self._get_headers())
            kwargs['headers'] = headers
            
            self.logger.debug(f"Making {method} request to {url}")
            
            # リクエスト実行
            response = await self.client.request(method, url, **kwargs)
            
            # ステータスコードチェック
            if response.status_code == 429:
                self.logger.warning("Rate limit exceeded")
                raise RateLimitError("Rate limit exceeded")
            elif response.status_code == 401:
                self.logger.error("Authentication failed")
                raise AuthenticationError("Authentication failed")
            elif response.status_code >= 400:
                error_data = None
                try:
                    error_data = response.json()
                except Exception:
                    pass
                raise APIError(
                    f"API request failed with status {response.status_code}",
                    status_code=response.status_code,
                    response_data=error_data
                )
                
            # レスポンス処理
            result = await self._handle_response(response)
            
            # 統計記録
            duration = time.time() - start_time
            self._record_stats(duration, success=True)
            
            self.logger.debug(f"Request completed in {duration:.2f}s")
            return result
            
        except Exception as e:
            # 統計記録（失敗）
            duration = time.time() - start_time
            self._record_stats(duration, success=False)
            
            self.logger.error(f"Request failed: {e}")
            raise
        finally:
            self.rate_limiter.release()
            
    async def health_check(self) -> bool:
        """サービスの健全性チェック."""
        try:
            await self._perform_health_check()
            return True
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False
            
    @abstractmethod
    async def _perform_health_check(self):
        """サービス固有の健全性チェック."""
        pass 