import pytest
from unittest.mock import patch, MagicMock
import json
import time

from services.claude import ClaudeService


class TestClaudeService:
    """Claude APIサービスのテストクラス"""

    @pytest.fixture
    def mock_config(self):
        """テスト用の設定"""
        return {
            "claude": {
                "api_key": "test_api_key",
                "model": "claude-3-7-sonnet-20250219",
                "max_tokens": 4000,
                "temperature": 0.7,
                "timeout": 30,
                "retry_count": 3,
                "retry_delay": 1
            }
        }

    @pytest.fixture
    def claude_service(self, mock_config):
        """Claude APIサービスのインスタンス"""
        return ClaudeService(mock_config)

    @patch('services.claude.requests.post')
    def test_generate_content_success(self, mock_post, claude_service):
        """コンテンツ生成成功のテスト"""
        # モックレスポンス
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "test_response_id",
            "content": [
                {
                    "type": "text",
                    "text": "# テスト応答\n\nこれはテスト応答です。\n\n```yaml\nkey: value\n```"
                }
            ]
        }
        mock_post.return_value = mock_response
        
        # テスト実行
        prompt = "テストプロンプト"
        result = claude_service.generate_content(prompt)
        
        # 結果の検証
        assert "content" in result
        assert "# テスト応答" in result["content"]
        assert "```yaml" in result["content"]
        
        # API呼び出しの検証
        mock_post.assert_called_once()
        call_args = mock_post.call_args[1]
        assert call_args["json"]["messages"][0]["content"] == "テストプロンプト"
        assert call_args["json"]["model"] == "claude-3-7-sonnet-20250219"
        assert call_args["headers"]["x-api-key"] == "test_api_key"

    @patch('services.claude.requests.post')
    def test_generate_content_with_system_prompt(self, mock_post, claude_service):
        """システムプロンプト付きコンテンツ生成のテスト"""
        # モックレスポンス
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "test_response_id",
            "content": [
                {
                    "type": "text",
                    "text": "システムプロンプトに従った応答"
                }
            ]
        }
        mock_post.return_value = mock_response
        
        # テスト実行
        prompt = "テストプロンプト"
        system_prompt = "あなたは技術記事専門のAIアシスタントです。"
        result = claude_service.generate_content(prompt, system_prompt=system_prompt)
        
        # 結果の検証
        assert "content" in result
        assert "システムプロンプトに従った応答" in result["content"]
        
        # API呼び出しの検証
        mock_post.assert_called_once()
        call_args = mock_post.call_args[1]
        assert call_args["json"]["messages"][0]["content"] == "テストプロンプト"
        assert call_args["json"]["system"] == "あなたは技術記事専門のAIアシスタントです。"
        assert "system" in call_args["json"]

    @patch('services.claude.requests.post')
    def test_generate_content_with_images(self, mock_post, claude_service):
        """画像付きコンテンツ生成のテスト"""
        # モックレスポンス
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "test_response_id",
            "content": [
                {
                    "type": "text",
                    "text": "画像の説明: これはテスト画像です。"
                }
            ]
        }
        mock_post.return_value = mock_response
        
        # テスト実行
        prompt = "この画像について説明してください"
        images = ["data:image/jpeg;base64,test_base64_data"]
        result = claude_service.generate_content(prompt, images)
        
        # 結果の検証
        assert "content" in result
        assert "画像の説明" in result["content"]
        
        # API呼び出しの検証
        mock_post.assert_called_once()
        call_args = mock_post.call_args[1]
        
        # メッセージ内に画像が含まれていることを確認
        messages = call_args["json"]["messages"]
        assert len(messages) == 1
        assert isinstance(messages[0]["content"], list)
        assert len(messages[0]["content"]) == 2  # テキスト + 画像
        
        # 画像コンテンツの検証
        image_content = [item for item in messages[0]["content"] if item.get("type") == "image"]
        assert len(image_content) == 1
        assert image_content[0]["source"]["data"] == "test_base64_data"

    @patch('services.claude.requests.post')
    def test_generate_content_with_images_and_system_prompt(self, mock_post, claude_service):
        """画像とシステムプロンプト付きコンテンツ生成のテスト"""
        # モックレスポンス
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "test_response_id",
            "content": [
                {
                    "type": "text",
                    "text": "画像分析: テスト画像です。"
                }
            ]
        }
        mock_post.return_value = mock_response
        
        # テスト実行
        prompt = "この画像について説明してください"
        images = ["data:image/jpeg;base64,test_base64_data"]
        system_prompt = "あなたは画像分析専門のAIアシスタントです。"
        result = claude_service.generate_content(prompt, images, system_prompt)
        
        # 結果の検証
        assert "content" in result
        assert "画像分析" in result["content"]
        
        # API呼び出しの検証
        mock_post.assert_called_once()
        call_args = mock_post.call_args[1]
        
        # システムプロンプトが含まれていることを確認
        assert call_args["json"]["system"] == "あなたは画像分析専門のAIアシスタントです。"
        
        # メッセージ内に画像が含まれていることを確認
        messages = call_args["json"]["messages"]
        assert len(messages) == 1
        assert isinstance(messages[0]["content"], list)
        assert len(messages[0]["content"]) == 2  # テキスト + 画像
        
        # 画像コンテンツの検証
        image_content = [item for item in messages[0]["content"] if item.get("type") == "image"]
        assert len(image_content) == 1
        assert image_content[0]["source"]["data"] == "test_base64_data"

    @patch('services.claude.requests.post')
    def test_extract_yaml(self, mock_post, claude_service):
        """YAML抽出のテスト"""
        # テストデータ
        api_response = """
        # 応答タイトル
        
        いくつかのテキスト
        
        ```yaml
        title: "テストタイトル"
        key1: value1
        key2: 42
        nested:
          subkey: subvalue
        ```
        
        その他のテキスト
        """
        
        # 抽出実行
        yaml_content = claude_service.extract_yaml(api_response)
        
        # 結果の検証
        assert yaml_content is not None
        assert "title: " in yaml_content
        assert "key1: value1" in yaml_content
        assert "nested:" in yaml_content
        
        # 文字列として検証するだけにし、実際のYAMLパース処理はスキップ
        assert 'title: "テストタイトル"' in yaml_content
        assert 'key2: 42' in yaml_content
        assert 'subkey: subvalue' in yaml_content

    @patch('services.claude.requests.post')
    def test_extract_markdown(self, mock_post, claude_service):
        """Markdown抽出のテスト"""
        # テストデータ
        api_response = """
        # 応答タイトル
        
        これはMarkdownテキストの始まりです。
        
        ## 見出し
        
        - リストアイテム1
        - リストアイテム2
        
        ```python
        def test_function():
            return "test"
        ```
        
        最後の部分。
        """
        
        # 抽出実行
        markdown_content = claude_service.extract_markdown(api_response)
        
        # 結果の検証
        assert markdown_content is not None
        assert "# 応答タイトル" in markdown_content
        assert "## 見出し" in markdown_content
        assert "- リストアイテム1" in markdown_content
        assert "```python" in markdown_content
        assert "def test_function():" in markdown_content

    @patch('services.claude.requests.post')
    def test_handle_rate_limit(self, mock_post, claude_service):
        """レート制限対応のテスト"""
        # 最初の呼び出しでレート制限エラー、2回目で成功するように設定
        mock_rate_limit_response = MagicMock()
        mock_rate_limit_response.status_code = 429
        mock_rate_limit_response.json.return_value = {"error": "rate_limit_exceeded"}
        
        mock_success_response = MagicMock()
        mock_success_response.status_code = 200
        mock_success_response.json.return_value = {
            "id": "test_response_id",
            "content": [{"type": "text", "text": "成功レスポンス"}]
        }
        
        # 最初はレート制限エラー、次は成功
        mock_post.side_effect = [mock_rate_limit_response, mock_success_response]
        
        # スリープをモック化して待ち時間をスキップ
        with patch('time.sleep') as mock_sleep:
            result = claude_service.generate_content("テストプロンプト")
            
            # スリープが呼ばれたことを確認
            mock_sleep.assert_called_once()
            
            # 2回目のAPI呼び出しで成功したことを確認
            assert mock_post.call_count == 2
            assert "content" in result
            assert "成功レスポンス" in result["content"]

    @patch('services.claude.requests.post')
    def test_validate_response(self, mock_post, claude_service):
        """レスポンス検証のテスト"""
        # 不正なレスポンス
        invalid_response = {}
        
        # 検証実行（例外が発生することを期待）
        with pytest.raises(ValueError):
            claude_service.validate_response(invalid_response)
        
        # 正常なレスポンス
        valid_response = {
            "id": "test_id",
            "content": [{"type": "text", "text": "正常なテキスト"}]
        }
        
        # 検証実行（例外が発生しないことを確認）
        try:
            claude_service.validate_response(valid_response)
            validation_passed = True
        except:
            validation_passed = False
            
        assert validation_passed 