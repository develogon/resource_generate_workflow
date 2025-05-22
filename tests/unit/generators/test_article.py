import pytest
import pytest_asyncio
from unittest.mock import patch, MagicMock

# テスト対象のモジュールをインポート
from app.generators.article import ArticleGenerator

class TestArticleGenerator:
    """記事ジェネレータのテストクラス"""
    
    @pytest_asyncio.fixture
    async def article_generator(self):
        """テスト用の記事ジェネレータインスタンスを作成"""
        return ArticleGenerator()
    
    @pytest.fixture
    def sample_structure_data(self):
        """テスト用の構造データを作成"""
        return {
            "title": "メインタイトル",
            "sections": [
                {"title": "セクション1", "content": "セクション1の内容..."},
                {"title": "セクション2", "content": "セクション2の内容..."}
            ]
        }
    
    def test_prepare_article_prompt(self, article_generator, sample_structure_data):
        """記事生成用プロンプト準備のテスト"""
        # get_system_promptとget_message_promptをモック化
        with patch.object(article_generator, 'get_system_prompt', return_value="モックシステムプロンプト") as mock_system, \
             patch.object(article_generator, 'get_message_prompt', return_value="モックメッセージプロンプト{{SECTIONS}}") as mock_message:
            
            prompt = article_generator.prepare_prompt(sample_structure_data)
            
            # プロンプトが正しく生成されることを確認
            assert prompt is not None
            assert isinstance(prompt, str)
            assert "記事作成" in prompt
            assert "システムプロンプト" in prompt
            assert "メッセージプロンプト" in prompt
            assert "記事タイトル" in prompt
            assert sample_structure_data["title"] in prompt
            assert "モックシステムプロンプト" in prompt
            assert "モックメッセージプロンプト" in prompt
            
            # 正しいパラメータでモックメソッドが呼ばれたことを確認
            mock_system.assert_called_once_with('article')
            mock_message.assert_called_once_with('article')
    
    @pytest.mark.asyncio
    async def test_generate_async(self, article_generator, sample_structure_data):
        """非同期記事生成のテスト"""
        # モックの非同期メソッド定義
        async def mock_call_api(request):
            return {
                "content": [
                    {
                        "type": "text",
                        "text": """# メインタイトル

## セクション1
これはセクション1の内容です。

## セクション2
これはセクション2の内容です。
"""
                    }
                ]
            }
        
        # クライアントのモック設定
        mock_client = MagicMock()
        mock_client.prepare_request.return_value = {"prompt": "テスト用プロンプト"}
        mock_client.call_api = mock_call_api
        mock_client.extract_content.return_value = """# メインタイトル

## セクション1
これはセクション1の内容です。

## セクション2
これはセクション2の内容です。
"""
        # モッククライアントを注入
        article_generator.client = mock_client
        
        # 非同期メソッドのテスト
        result = await article_generator.generate(sample_structure_data)
        
        # 結果が正しいことを確認
        assert result is not None
        assert isinstance(result, str)
        assert "# メインタイトル" in result
        assert "## セクション1" in result
        assert "## セクション2" in result
        
        # API呼び出しの準備が行われたことを確認
        mock_client.prepare_request.assert_called_once()
    
    def test_generate_article(self, article_generator, sample_structure_data, monkeypatch):
        """同期版記事生成のテスト"""
        # モックレスポンス用の文字列
        expected_result = """# メインタイトル

## セクション1
これはセクション1の内容です。

## セクション2
これはセクション2の内容です。
"""
        
        # モック化して同期メソッドが非同期メソッドを呼び出すことをシミュレート
        async def mock_generate(*args, **kwargs):
            return expected_result
        
        # 非同期メソッドをモック
        monkeypatch.setattr(article_generator, 'generate', mock_generate)
        
        # 同期メソッドのテスト
        result = article_generator.generate_article(sample_structure_data)
        
        # 結果が正しいことを確認
        assert result == expected_result 