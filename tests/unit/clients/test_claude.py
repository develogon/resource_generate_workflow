"""ClaudeClientクラスのテスト."""

import base64
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.clients.claude import ClaudeClient
from src.clients.base import APIError
from src.config.settings import Config


class TestClaudeClient:
    """ClaudeClientのテスト."""
    
    @pytest.fixture
    def config(self):
        """テスト用設定."""
        config = Config()
        config.api_timeout = 30.0
        config.claude.api_key = "test-api-key"
        config.claude.base_url = "https://api.anthropic.com/v1"
        config.claude.model = "claude-3-sonnet-20240229"
        config.claude.max_tokens = 1000
        config.claude.temperature = 0.7
        config.claude.rate_limit = 50
        config.cache.size = 100
        config.cache.ttl = 3600
        return config
        
    @pytest.fixture
    def client(self, config):
        """テスト用クライアント."""
        return ClaudeClient(config)
        
    def test_initialization(self, client, config):
        """初期化のテスト."""
        assert client.service_name == "claude"
        assert client.api_key == "test-api-key"
        assert client.base_url == config.claude.base_url
        assert client.model == config.claude.model
        assert client.max_tokens == config.claude.max_tokens
        assert client.temperature == config.claude.temperature
        
    def test_initialization_without_api_key(self):
        """APIキーなしでの初期化エラーテスト."""
        config = Config()
        config.claude.api_key = None
        
        with pytest.raises(ValueError, match="Claude API key is required"):
            ClaudeClient(config)
            
    def test_get_headers(self, client):
        """ヘッダー取得のテスト."""
        headers = client._get_headers()
        
        assert headers["Authorization"] == "Bearer test-api-key"
        assert headers["Content-Type"] == "application/json"
        assert "User-Agent" in headers
        
    def test_get_rate_limit(self, client):
        """レート制限取得のテスト."""
        assert client._get_rate_limit() == 50
        
    @pytest.mark.asyncio
    async def test_handle_response_success(self, client):
        """正常レスポンス処理のテスト."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"content": [{"text": "Hello, world!"}]}
        
        result = await client._handle_response(mock_response)
        assert result == {"content": [{"text": "Hello, world!"}]}
        
    @pytest.mark.asyncio
    async def test_handle_response_error(self, client):
        """エラーレスポンス処理のテスト."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": {
                "type": "invalid_request_error",
                "message": "Invalid request"
            }
        }
        
        with pytest.raises(APIError, match="Claude API error: Invalid request"):
            await client._handle_response(mock_response)
            
    @pytest.mark.asyncio
    async def test_handle_response_rate_limit_error(self, client):
        """レート制限エラーレスポンス処理のテスト."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.json.return_value = {
            "error": {
                "type": "rate_limit_error",
                "message": "Rate limit exceeded"
            }
        }
        
        with pytest.raises(APIError, match="Rate limit error: Rate limit exceeded"):
            await client._handle_response(mock_response)
            
    def test_generate_cache_key(self, client):
        """キャッシュキー生成のテスト."""
        # 基本的なテスト
        key1 = client._generate_cache_key("Hello, world!")
        key2 = client._generate_cache_key("Hello, world!")
        assert key1 == key2
        
        # 異なるプロンプトは異なるキー
        key3 = client._generate_cache_key("Different prompt")
        assert key1 != key3
        
        # 画像ありのテスト
        image_data = b"fake_image_data"
        key4 = client._generate_cache_key("Hello", images=[image_data])
        key5 = client._generate_cache_key("Hello", images=[image_data])
        assert key4 == key5
        
        # 画像なしとありで異なる
        key6 = client._generate_cache_key("Hello")
        assert key4 != key6
        
    def test_build_request_text_only(self, client):
        """テキストのみのリクエスト構築テスト."""
        request = client._build_request(
            prompt="Hello, Claude!",
            model="claude-3-sonnet-20240229",
            max_tokens=1000,
            temperature=0.7
        )
        
        expected = {
            "model": "claude-3-sonnet-20240229",
            "max_tokens": 1000,
            "temperature": 0.7,
            "messages": [
                {
                    "role": "user",
                    "content": "Hello, Claude!"
                }
            ]
        }
        
        assert request == expected
        
    def test_build_request_with_system_prompt(self, client):
        """システムプロンプト付きリクエスト構築テスト."""
        request = client._build_request(
            prompt="Hello, Claude!",
            system_prompt="You are a helpful assistant.",
            model="claude-3-sonnet-20240229",
            max_tokens=1000,
            temperature=0.7
        )
        
        assert len(request["messages"]) == 2
        assert request["messages"][0]["role"] == "system"
        assert request["messages"][0]["content"] == "You are a helpful assistant."
        assert request["messages"][1]["role"] == "user"
        assert request["messages"][1]["content"] == "Hello, Claude!"
        
    def test_build_request_with_images(self, client):
        """画像付きリクエスト構築テスト."""
        image_data = b"fake_image_data"
        request = client._build_request(
            prompt="Describe this image",
            images=[image_data],
            model="claude-3-sonnet-20240229",
            max_tokens=1000,
            temperature=0.7
        )
        
        user_message = request["messages"][0]
        assert user_message["role"] == "user"
        assert isinstance(user_message["content"], list)
        assert len(user_message["content"]) == 2
        
        # テキスト部分
        assert user_message["content"][0]["type"] == "text"
        assert user_message["content"][0]["text"] == "Describe this image"
        
        # 画像部分
        assert user_message["content"][1]["type"] == "image"
        assert user_message["content"][1]["source"]["type"] == "base64"
        assert user_message["content"][1]["source"]["media_type"] == "image/png"
        assert user_message["content"][1]["source"]["data"] == base64.b64encode(image_data).decode()
        
    @pytest.mark.asyncio
    async def test_generate_text_success(self, client):
        """テキスト生成成功のテスト."""
        mock_response = {
            "content": [{"text": "Hello, human!"}],
            "model": "claude-3-sonnet-20240229",
            "usage": {"input_tokens": 10, "output_tokens": 5}
        }
        
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            result = await client.generate_text("Hello, Claude!")
            
            assert result == mock_response
            mock_request.assert_called_once()
            
            # リクエストデータの確認
            call_args = mock_request.call_args
            assert call_args[1]["method"] == "POST"
            assert "messages" in call_args[1]["url"]
            assert "json" in call_args[1]
            
    @pytest.mark.asyncio
    async def test_generate_text_with_cache(self, client):
        """キャッシュ機能のテスト."""
        mock_response = {
            "content": [{"text": "Cached response"}],
            "model": "claude-3-sonnet-20240229"
        }
        
        with patch.object(client.cache, 'get', new_callable=AsyncMock) as mock_cache_get:
            with patch.object(client.cache, 'set', new_callable=AsyncMock) as mock_cache_set:
                with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
                    
                    # 最初の呼び出し（キャッシュなし）
                    mock_cache_get.return_value = None
                    mock_request.return_value = mock_response
                    
                    result1 = await client.generate_text("Test prompt")
                    
                    assert result1 == mock_response
                    mock_request.assert_called_once()
                    mock_cache_set.assert_called_once()
                    
                    # 2回目の呼び出し（キャッシュヒット）
                    mock_cache_get.return_value = mock_response
                    mock_request.reset_mock()
                    
                    result2 = await client.generate_text("Test prompt")
                    
                    assert result2 == mock_response
                    mock_request.assert_not_called()  # キャッシュから取得されるため呼ばれない
                    
    @pytest.mark.asyncio
    async def test_generate_structured_content(self, client):
        """構造化コンテンツ生成のテスト."""
        mock_response = {
            "content": [{"text": "# Article Title\n\nArticle content..."}]
        }
        
        with patch.object(client, 'generate_text', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = mock_response
            
            result = await client.generate_structured_content(
                prompt="Write about Python",
                content_type="article"
            )
            
            assert result == mock_response
            mock_generate.assert_called_once()
            
            # システムプロンプトが設定されているかチェック
            call_args = mock_generate.call_args
            assert "system_prompt" in call_args[1]
            assert "記事を生成してください" in call_args[1]["system_prompt"]
            
    @pytest.mark.asyncio
    async def test_batch_generate(self, client):
        """バッチ生成のテスト."""
        prompts = ["Prompt 1", "Prompt 2", "Prompt 3"]
        mock_responses = [
            {"content": [{"text": "Response 1"}]},
            {"content": [{"text": "Response 2"}]},
            {"content": [{"text": "Response 3"}]}
        ]
        
        with patch.object(client, 'generate_structured_content', new_callable=AsyncMock) as mock_generate:
            mock_generate.side_effect = mock_responses
            
            results = await client.batch_generate(prompts, content_type="article")
            
            assert len(results) == 3
            assert results == mock_responses
            assert mock_generate.call_count == 3
            
    @pytest.mark.asyncio
    async def test_batch_generate_with_errors(self, client):
        """エラーを含むバッチ生成のテスト."""
        prompts = ["Prompt 1", "Prompt 2"]
        
        with patch.object(client, 'generate_structured_content', new_callable=AsyncMock) as mock_generate:
            mock_generate.side_effect = [
                {"content": [{"text": "Response 1"}]},
                Exception("API Error")
            ]
            
            results = await client.batch_generate(prompts)
            
            assert len(results) == 2
            assert results[0] == {"content": [{"text": "Response 1"}]}
            assert "error" in results[1]
            assert results[1]["prompt"] == "Prompt 2"
            
    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """健全性チェックのテスト."""
        with patch.object(client, 'generate_text', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = {"content": [{"text": "Hello"}]}
            
            result = await client.health_check()
            
            assert result is True
            mock_generate.assert_called_once_with(
                prompt="Hello",
                max_tokens=10,
                use_cache=False
            )
            
    @pytest.mark.asyncio
    async def test_get_cache_stats(self, client):
        """キャッシュ統計取得のテスト."""
        mock_cache_stats = {"hits": 10, "misses": 5}
        
        with patch.object(client.cache, 'get_stats', new_callable=AsyncMock) as mock_cache_stats_method:
            mock_cache_stats_method.return_value = mock_cache_stats
            
            stats = await client.get_cache_stats()
            
            assert "client_stats" in stats
            assert "cache_stats" in stats
            assert "service_name" in stats
            assert stats["cache_stats"] == mock_cache_stats
            assert stats["service_name"] == "claude" 