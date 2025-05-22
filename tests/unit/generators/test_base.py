import pytest
from unittest.mock import patch, MagicMock, mock_open
import pytest_asyncio
import asyncio
import os

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
    
    @pytest.fixture
    def sample_structure_with_chapter(self):
        """チャプター情報を含むサンプル構造データ"""
        return {
            "title": "サンプルタイトル",
            "chapter_name": "チャプター1",
            "sections": [
                {
                    "title": "セクション1",
                    "paragraphs": [
                        {
                            "content": "これはセクション1の内容です。"
                        }
                    ]
                }
            ]
        }
    
    @pytest.fixture
    def sample_structure_with_section(self):
        """セクション情報を含むサンプル構造データ"""
        return {
            "title": "サンプルタイトル",
            "chapter_name": "チャプター1",
            "section_name": "セクション1",
            "paragraphs": [
                {
                    "content": "これはセクション1の内容です。"
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
    
    def test_get_output_path_title_level(self, base_generator, sample_structure_data):
        """タイトルレベルの出力パス生成テスト"""
        file_name = "article.md"
        level = "title"
        
        output_path = base_generator.get_output_path(sample_structure_data, level, file_name)
        
        # 出力パスが正しく生成されることを確認
        expected_path = os.path.join("サンプルタイトル", file_name)
        assert output_path == expected_path
    
    def test_get_output_path_chapter_level(self, base_generator, sample_structure_with_chapter):
        """チャプターレベルの出力パス生成テスト"""
        file_name = "article.md"
        level = "chapter"
        
        output_path = base_generator.get_output_path(sample_structure_with_chapter, level, file_name)
        
        # 出力パスが正しく生成されることを確認
        expected_path = os.path.join("サンプルタイトル", "チャプター1", file_name)
        assert output_path == expected_path
    
    def test_get_output_path_section_level(self, base_generator, sample_structure_with_section):
        """セクションレベルの出力パス生成テスト"""
        file_name = "article.md"
        level = "section"
        
        output_path = base_generator.get_output_path(sample_structure_with_section, level, file_name)
        
        # 出力パスが正しく生成されることを確認
        expected_path = os.path.join("サンプルタイトル", "チャプター1", "セクション1", file_name)
        assert output_path == expected_path
    
    def test_get_output_path_unknown_level(self, base_generator, sample_structure_data):
        """不明なレベルの出力パス生成テスト"""
        file_name = "article.md"
        level = "unknown"
        
        output_path = base_generator.get_output_path(sample_structure_data, level, file_name)
        
        # デフォルトのパスが生成されることを確認
        expected_path = os.path.join("サンプルタイトル", file_name)
        assert output_path == expected_path
    
    @pytest.mark.asyncio
    async def test_generate(self, base_generator, sample_structure_data):
        """コンテンツ生成の実行テスト"""
        mock_response = {
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
        # 非同期関数を同期的に返すようにモック
        mock_client.call_api = MagicMock(return_value=mock_response)
        mock_client.extract_content.return_value = "# 生成されたコンテンツ\n\nこれはAPIによって生成されたコンテンツです。"
        
        base_generator.client = mock_client
        
        additional_context = {"style": "技術解説"}
        output_path = "test_output.md"
        
        result = await base_generator.generate(sample_structure_data, additional_context, output_path)
        
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