import pytest
from unittest.mock import patch, MagicMock, mock_open
import pytest_asyncio
import asyncio

# テスト対象のモジュールをインポート
from app.generators.base import BaseGenerator

class TestBaseGenerator:
    """ベースジェネレータのテストクラス"""
    
    @pytest.fixture
    def sample_structure_data(self):
        """サンプル構造データ"""
        return {
            "title": "サンプルタイトル",
            "sections": [
                {
                    "title": "セクション1",
                    "paragraphs": [
                        {
                            "content": "これはセクション1の内容です。"
                        }
                    ]
                },
                {
                    "title": "セクション2",
                    "paragraphs": [
                        {
                            "content": "これはセクション2の内容です。"
                        }
                    ]
                }
            ]
        }
    
    @pytest_asyncio.fixture
    async def base_generator(self):
        """テスト用のベースジェネレータインスタンスを作成"""
        # 実際のクラスインスタンスを返す
        return BaseGenerator()
    
    def test_prepare_prompt(self, base_generator, sample_structure_data):
        """プロンプト準備のテスト"""
        prompt = base_generator.prepare_prompt(sample_structure_data)
        
        # プロンプトが正しく生成されることを確認
        assert prompt is not None
        assert isinstance(prompt, str)
        assert sample_structure_data["title"] in prompt
        
        # 構造データの要素がプロンプトに含まれていることを確認
        for section in sample_structure_data["sections"]:
            assert section["title"] in prompt
    
    def test_process_response(self, base_generator):
        """API応答の処理テスト"""
        response = {
            "content": [
                {
                    "type": "text",
                    "text": "# 生成されたコンテンツ\n\nこれはAPIによって生成されたコンテンツです。"
                }
            ]
        }
        
        result = base_generator.process_response(response)
        
        # レスポンスが正しく処理されることを確認
        assert result is not None
        assert isinstance(result, str)
        assert "# 生成されたコンテンツ" in result
    
    @pytest.mark.asyncio
    async def test_generate(self, base_generator, sample_structure_data):
        """コンテンツ生成の実行テスト"""
        async def mock_call_api(request):
            return {
                "content": [
                    {
                        "type": "text",
                        "text": "# 生成されたコンテンツ\n\nこれはAPIによって生成されたコンテンツです。"
                    }
                ]
            }
        
        # モックをインスタンス変数として設定
        mock_client = MagicMock()
        mock_client.prepare_request.return_value = {"prompt": "テスト用プロンプト"}
        mock_client.call_api = mock_call_api
        mock_client.extract_content.return_value = "# 生成されたコンテンツ\n\nこれはAPIによって生成されたコンテンツです。"
        
        base_generator.client = mock_client
        
        additional_context = {"style": "技術解説"}
        
        result = await base_generator.generate(sample_structure_data, additional_context)
        
        # コンテンツが正しく生成されることを確認
        assert result is not None
        assert isinstance(result, str)
        assert "生成されたコンテンツ" in result
        mock_client.prepare_request.assert_called_once()
    
    @patch("builtins.open", new_callable=mock_open)
    def test_load_prompt_template(self, mock_file, base_generator):
        """プロンプトテンプレート読込のテスト"""
        mock_file.return_value.read.return_value = "# {{title}}\n\n{{content}}"
        
        template = base_generator.load_prompt_template("system", "article")
        
        # テンプレートが正しく読み込まれることを確認
        assert template is not None
        assert isinstance(template, str)
        assert "{{title}}" in template
        assert "{{content}}" in template 