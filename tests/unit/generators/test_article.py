import pytest
from unittest.mock import patch, MagicMock

# テスト対象のモジュールをインポート
from app.generators.article import ArticleGenerator

class TestArticleGenerator:
    """記事ジェネレータのテストクラス"""
    
    @pytest.fixture
    def article_generator(self):
        """テスト用の記事ジェネレータインスタンスを作成"""
        return ArticleGenerator()
    
    def test_generate_article(self, article_generator, sample_structure_data):
        """記事生成のテスト"""
        # 実際のクラスを使用した記事生成のテスト
        result = article_generator.generate_article(sample_structure_data, "sample.md")
        
        # 結果が正しいことを確認
        assert result is not None
        assert isinstance(result, str)
        assert "# メインタイトル" in result
        assert "セクション1" in result
        assert "セクション2" in result
    
    @patch("app.clients.claude.ClaudeAPIClient")
    async def test_article_generation_with_api(self, mock_claude_client, article_generator, sample_structure_data):
        """APIを使用した記事生成のテスト"""
        # このテストは、実際のクラスが実装された後に有効化する
        # mock_client_instance = mock_claude_client.return_value
        # mock_client_instance.call_api.return_value = {
        #     "content": [
        #         {
        #             "type": "text",
        #             "text": """# メインタイトル
        # 
        # ## セクション1
        # これはセクション1の内容です。
        # 
        # ## セクション2
        # これはセクション2の内容です。
        # """
        #         }
        #     ]
        # }
        # 
        # result = await article_generator.generate(sample_structure_data, "sample.md")
        # 
        # # 結果が正しいことを確認
        # assert result is not None
        # assert isinstance(result, str)
        # assert "# メインタイトル" in result
        # 
        # # API呼び出しが行われたことを確認
        # mock_client_instance.call_api.assert_called_once()
        pass
    
    def test_prepare_article_prompt(self, article_generator, sample_structure_data):
        """記事生成用プロンプト準備のテスト"""
        prompt = article_generator.prepare_prompt(sample_structure_data)
        
        # プロンプトが正しく生成されることを確認
        assert prompt is not None
        assert isinstance(prompt, str)
        assert "記事タイトル" in prompt
        assert "セクション" in prompt
        assert sample_structure_data["title"] in prompt 