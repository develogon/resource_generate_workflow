import pytest
from unittest.mock import patch, MagicMock

from services.client import APIClient
from tests.fixtures.sample_api_responses import SAMPLE_API_RESPONSE, SAMPLE_API_ERROR_RESPONSE


class TestAPIClient:
    """APIクライアント基底クラスのテスト"""

    @pytest.fixture
    def api_client(self):
        """APIクライアントインスタンス"""
        # 具象クラスのインスタンス化
        class ConcreteAPIClient(APIClient):
            def __init__(self, config):
                super().__init__(config)
                self.base_url = "https://api.example.com"
                self.headers = {"Authorization": f"Bearer {config['api_key']}"}
            
            def handle_response(self, response):
                return super().handle_response(response)
            
            def handle_error(self, error):
                return super().handle_error(error)
        
        config = {"api_key": "test_api_key"}
        return ConcreteAPIClient(config)

    @patch('requests.request')
    def test_request_success(self, mock_request, api_client):
        """正常なAPI通信のテスト"""
        # モックレスポンス設定
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_API_RESPONSE
        mock_request.return_value = mock_response
        
        # リクエスト実行
        response = api_client.request(
            endpoint="/test",
            method="GET",
            payload={"param": "value"}
        )
        
        # リクエストの検証
        mock_request.assert_called_once_with(
            method="GET",
            url="https://api.example.com/test",
            headers={"Authorization": "Bearer test_api_key"},
            json={"param": "value"},
            timeout=30
        )
        
        # レスポンスの検証
        assert response["status"] == "success"
        assert "data" in response
        assert response["data"]["id"] == "response_123"

    @patch('requests.request')
    def test_request_error(self, mock_request, api_client):
        """エラー応答のテスト"""
        # モックレスポンス設定
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.json.return_value = SAMPLE_API_ERROR_RESPONSE
        mock_request.return_value = mock_response
        
        # リクエスト実行
        with pytest.raises(Exception) as excinfo:
            api_client.request(
                endpoint="/test",
                method="GET"
            )
        
        # エラーメッセージの検証
        assert "API error" in str(excinfo.value)
        assert "rate_limit_exceeded" in str(excinfo.value)

    @patch('requests.request')
    def test_request_network_error(self, mock_request, api_client):
        """ネットワークエラーのテスト"""
        # リクエスト例外のモック
        mock_request.side_effect = Exception("Network error")
        
        # リクエスト実行
        with pytest.raises(Exception) as excinfo:
            api_client.request(
                endpoint="/test",
                method="GET"
            )
        
        # エラーメッセージの検証
        assert "Network error" in str(excinfo.value)

    def test_handle_response(self, api_client):
        """レスポンス処理のテスト"""
        # 正常なレスポンス
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_API_RESPONSE
        
        result = api_client.handle_response(mock_response)
        assert result == SAMPLE_API_RESPONSE
        
        # エラーレスポンス
        mock_error_response = MagicMock()
        mock_error_response.status_code = 429
        mock_error_response.json.return_value = SAMPLE_API_ERROR_RESPONSE
        
        with pytest.raises(Exception) as excinfo:
            api_client.handle_response(mock_error_response)
        
        assert "API error" in str(excinfo.value)
        
        # JSON解析エラー
        mock_invalid_response = MagicMock()
        mock_invalid_response.status_code = 200
        mock_invalid_response.json.side_effect = ValueError("Invalid JSON")
        
        with pytest.raises(ValueError) as excinfo:
            api_client.handle_response(mock_invalid_response)
        
        assert "Invalid JSON" in str(excinfo.value)

    def test_handle_error(self, api_client):
        """エラー処理のテスト"""
        error = Exception("Test error")
        
        with pytest.raises(Exception) as excinfo:
            api_client.handle_error(error)
        
        assert "Test error" in str(excinfo.value)

    @patch('requests.request')
    @patch('time.sleep')
    def test_retry_request_decorator(self, mock_sleep, mock_request, api_client):
        """リトライデコレータのテスト"""
        # リトライ用のメソッド
        @api_client.retry_request(max_attempts=3)
        def test_api_call(client):
            return client.request(endpoint="/test", method="GET")
        
        # 最初の2回は失敗、3回目に成功するようにモック
        mock_error_response = MagicMock()
        mock_error_response.status_code = 500
        mock_error_response.json.return_value = {"error": "Server error"}
        
        mock_success_response = MagicMock()
        mock_success_response.status_code = 200
        mock_success_response.json.return_value = SAMPLE_API_RESPONSE
        
        mock_request.side_effect = [mock_error_response, mock_error_response, mock_success_response]
        
        # リトライ付きAPI呼び出し
        result = test_api_call(api_client)
        
        # リクエストが3回行われたことを確認
        assert mock_request.call_count == 3
        
        # sleepが2回呼ばれたことを確認
        assert mock_sleep.call_count == 2
        
        # 最終的に成功レスポンスが返されたことを確認
        assert result["status"] == "success" 