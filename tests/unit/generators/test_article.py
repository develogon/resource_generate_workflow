import pytest
import pytest_asyncio
import os
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
    
    @pytest.fixture
    def sample_structure_with_chapter(self):
        """チャプター情報を含むサンプル構造データ"""
        return {
            "title": "メインタイトル",
            "chapter_name": "チャプター1",
            "sections": [
                {"title": "セクション1", "content": "セクション1の内容..."}
            ]
        }
    
    @pytest.fixture
    def sample_structure_with_section(self):
        """セクション情報を含むサンプル構造データ"""
        return {
            "title": "メインタイトル",
            "chapter_name": "チャプター1",
            "section_name": "セクション1",
            "content": "セクション1の内容..."
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
    async def test_generate_async_with_output_path(self, article_generator, sample_structure_data):
        """出力パスを指定した非同期記事生成のテスト"""
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
        
        # os.makedirsをモック化
        with patch('os.makedirs') as mock_makedirs:
            # 出力パスを指定
            output_path = "output/article.md"
            
            # 非同期メソッドのテスト
            result = await article_generator.generate(sample_structure_data, output_path)
            
            # 結果が正しいことを確認
            assert result is not None
            assert isinstance(result, str)
            assert "# メインタイトル" in result
            assert "## セクション1" in result
            assert "## セクション2" in result
            
            # os.makedirsが呼ばれたことを確認
            mock_makedirs.assert_called_once_with(os.path.dirname(output_path), exist_ok=True)
            
            # API呼び出しの準備が行われたことを確認
            mock_client.prepare_request.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_async_auto_output_path(self, article_generator, sample_structure_with_chapter):
        """出力パスが自動生成される非同期記事生成のテスト"""
        # モックの非同期メソッド定義
        async def mock_call_api(request):
            return {
                "content": [
                    {
                        "type": "text",
                        "text": """# メインタイトル

## セクション1
これはセクション1の内容です。
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
"""
        # モッククライアントを注入
        article_generator.client = mock_client
        
        # get_output_pathとos.makedirsをモック化
        expected_path = "メインタイトル/チャプター1/article.md"
        with patch.object(article_generator, 'get_output_path', return_value=expected_path) as mock_get_path, \
             patch('os.makedirs') as mock_makedirs:
            
            # 出力パスを指定せずに非同期メソッドを呼び出し
            result = await article_generator.generate(sample_structure_with_chapter)
            
            # 結果が正しいことを確認
            assert result is not None
            assert isinstance(result, str)
            assert "# メインタイトル" in result
            
            # get_output_pathが正しく呼ばれたことを確認
            mock_get_path.assert_called_once_with(sample_structure_with_chapter, 'chapter', 'article.md')
            
            # os.makedirsが呼ばれたことを確認
            mock_makedirs.assert_called_once_with(os.path.dirname(expected_path), exist_ok=True)
    
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
        async def mock_generate(structure, output_path=None):
            assert structure == sample_structure_data
            assert output_path is None or output_path == "test_output.md"
            return expected_result
        
        # 非同期メソッドをモック
        monkeypatch.setattr(article_generator, 'generate', mock_generate)
        
        # 出力パスなしでテスト
        result1 = article_generator.generate_article(sample_structure_data)
        assert result1 == expected_result
        
        # 出力パスありでテスト
        result2 = article_generator.generate_article(sample_structure_data, "test_output.md")
        assert result2 == expected_result 