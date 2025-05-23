"""BaseClientクラスのテスト."""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.clients.base import (
    APIError,
    AuthenticationError,
    BaseClient,
    ClientError,
    RateLimitError,
)
from src.config.settings import Config


class MockClient(BaseClient):
    """テスト用のクライアント実装."""
    
    def _get_rate_limit(self) -> int:
        return 60  # 60 requests per minute
        
    def _get_headers(self) -> dict[str, str]:
        return {"Authorization": "Bearer test-token"}
        
    async def _handle_response(self, response: httpx.Response) -> dict[str, any]:
        return response.json()
        
    async def _perform_health_check(self):
        await self._make_request("GET", "https://api.example.com/health")


class TestBaseClient:
    """BaseClientのテスト."""
    
    @pytest.fixture
    def config(self):
        """テスト用設定."""
        config = Config()
        config.api_timeout = 30.0
        return config
        
    @pytest.fixture
    def client(self, config):
        """テスト用クライアント."""
        return MockClient(config, "test-service")
        
    def test_initialization(self, client):
        """初期化のテスト."""
        assert client.service_name == "test-service"
        assert client.config.api_timeout == 30.0
        assert client.stats["requests_made"] == 0
        assert client.stats["requests_failed"] == 0
        
    def test_get_headers(self, client):
        """ヘッダー取得のテスト."""
        headers = client._get_headers()
        assert headers == {"Authorization": "Bearer test-token"}
        
    def test_get_rate_limit(self, client):
        """レート制限取得のテスト."""
        assert client._get_rate_limit() == 60
        
    def test_record_stats(self, client):
        """統計記録のテスト."""
        # 成功ケース
        client._record_stats(1.5, success=True)
        stats = client.get_stats()
        
        assert stats["requests_made"] == 1
        assert stats["requests_failed"] == 0
        assert stats["total_time"] == 1.5
        assert stats["average_time"] == 1.5
        assert stats["failure_rate"] == 0.0
        
        # 失敗ケース
        client._record_stats(2.0, success=False)
        stats = client.get_stats()
        
        assert stats["requests_made"] == 2
        assert stats["requests_failed"] == 1
        assert stats["total_time"] == 3.5
        assert stats["average_time"] == 1.75
        assert stats["failure_rate"] == 0.5
        
    @pytest.mark.asyncio
    async def test_context_manager(self, client):
        """コンテキストマネージャーのテスト."""
        async with client as c:
            assert c is client
            
        # closeが呼ばれることを確認
        with patch.object(client, 'close', new_callable=AsyncMock) as mock_close:
            async with client:
                pass
                
            mock_close.assert_called_once()
            
    @pytest.mark.asyncio
    async def test_make_request_success(self, client):
        """正常なリクエストのテスト."""
        # モックレスポンス
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}
        
        with patch.object(client.client, 'request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            result = await client._make_request("GET", "https://api.example.com/test")
            
            assert result == {"status": "success"}
            mock_request.assert_called_once()
            
            # 統計が記録されているかチェック
            stats = client.get_stats()
            assert stats["requests_made"] == 1
            assert stats["requests_failed"] == 0
            
    @pytest.mark.asyncio
    async def test_make_request_rate_limit_error(self, client):
        """レート制限エラーのテスト."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        
        with patch.object(client.client, 'request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            with pytest.raises(RateLimitError, match="Rate limit exceeded"):
                await client._make_request("GET", "https://api.example.com/test")
                
    @pytest.mark.asyncio
    async def test_make_request_auth_error(self, client):
        """認証エラーのテスト."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        
        with patch.object(client.client, 'request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            with pytest.raises(AuthenticationError, match="Authentication failed"):
                await client._make_request("GET", "https://api.example.com/test")
                
    @pytest.mark.asyncio
    async def test_make_request_api_error(self, client):
        """APIエラーのテスト."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": "Internal server error"}
        
        with patch.object(client.client, 'request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            with pytest.raises(APIError) as exc_info:
                await client._make_request("GET", "https://api.example.com/test")
                
            assert exc_info.value.status_code == 500
            assert exc_info.value.response_data == {"error": "Internal server error"}
            
    @pytest.mark.asyncio
    async def test_make_request_retry(self, client):
        """リトライ機能のテスト."""
        # 最初の2回は失敗、3回目は成功
        mock_responses = [
            MagicMock(status_code=500),
            MagicMock(status_code=500),
            MagicMock(status_code=200)
        ]
        mock_responses[2].json.return_value = {"status": "success"}
        
        with patch.object(client.client, 'request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = mock_responses
            
            result = await client._make_request("GET", "https://api.example.com/test")
            
            assert result == {"status": "success"}
            assert mock_request.call_count == 3
            
    @pytest.mark.asyncio
    async def test_health_check_success(self, client):
        """健全性チェック成功のテスト."""
        with patch.object(client, '_perform_health_check', new_callable=AsyncMock) as mock_health:
            mock_health.return_value = None
            
            result = await client.health_check()
            
            assert result is True
            mock_health.assert_called_once()
            
    @pytest.mark.asyncio
    async def test_health_check_failure(self, client):
        """健全性チェック失敗のテスト."""
        with patch.object(client, '_perform_health_check', new_callable=AsyncMock) as mock_health:
            mock_health.side_effect = Exception("Health check failed")
            
            result = await client.health_check()
            
            assert result is False
            
    @pytest.mark.asyncio
    async def test_rate_limiting(self, client):
        """レート制限のテスト."""
        # レート制限器をモック
        with patch.object(client.rate_limiter, 'acquire', new_callable=AsyncMock) as mock_acquire:
            with patch.object(client.rate_limiter, 'release') as mock_release:
                with patch.object(client.client, 'request', new_callable=AsyncMock) as mock_request:
                    mock_response = MagicMock()
                    mock_response.status_code = 200
                    mock_response.json.return_value = {"status": "success"}
                    mock_request.return_value = mock_response
                    
                    await client._make_request("GET", "https://api.example.com/test")
                    
                    mock_acquire.assert_called_once()
                    mock_release.assert_called_once() 