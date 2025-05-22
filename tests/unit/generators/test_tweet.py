import pytest
import pytest_asyncio
import csv
import io
import os
from unittest.mock import patch, MagicMock

# テスト対象のモジュールをインポート
from app.generators.tweet import TweetGenerator

class TestTweetGenerator:
    """ツイートジェネレータのテストクラス"""
    
    @pytest_asyncio.fixture
    async def tweet_generator(self):
        """テスト用のツイートジェネレータインスタンスを作成"""
        return TweetGenerator()
    
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
    
    def test_prepare_tweets_prompt(self, tweet_generator, sample_structure_data):
        """ツイート生成用プロンプト準備のテスト"""
        # get_system_promptとget_message_promptをモック化
        with patch.object(tweet_generator, 'get_system_prompt', return_value="モックシステムプロンプト") as mock_system, \
             patch.object(tweet_generator, 'get_message_prompt', return_value="モックメッセージプロンプト{{ARTICLE_CONTENT}}{{TWEET_COUNT}}{{MAX_LENGTH}}") as mock_message:
            
            article_content = "# メインタイトル\n\nこれは記事の内容です..."
            
            prompt = tweet_generator.prepare_prompt(sample_structure_data, article_content)
            
            # プロンプトが正しく生成されることを確認
            assert prompt is not None
            assert isinstance(prompt, str)
            assert "ツイート生成" in prompt
            assert "システムプロンプト" in prompt
            assert "メッセージプロンプト" in prompt
            assert "記事タイトル" in prompt
            assert sample_structure_data["title"] in prompt
            assert "モックシステムプロンプト" in prompt
            assert "モックメッセージプロンプト" in prompt
            
            # 正しいパラメータでモックメソッドが呼ばれたことを確認
            mock_system.assert_called_once_with('tweet')
            mock_message.assert_called_once_with('tweet')
    
    @pytest.mark.asyncio
    async def test_generate_async_with_output_path(self, tweet_generator, sample_structure_data):
        """出力パスを指定した非同期ツイート生成のテスト"""
        # モックの非同期メソッド定義
        async def mock_call_api(request):
            return {
                "content": [
                    {
                        "type": "text",
                        "text": """```csv
tweet_text,hashtags,media_suggestion
「メインタイトル」で取り上げた基本概念について解説しています！,#プログラミング #初心者向け,
実際に手を動かして学べる「メインタイトル」の実践編をチェック！,#プログラミング学習 #ハンズオン,https://example.com/image1.jpg
「メインタイトル」のポイントを5分でまとめました。,#5分解説 #初心者歓迎,
```"""
                    }
                ]
            }
        
        # クライアントのモック設定
        mock_client = MagicMock()
        mock_client.prepare_request.return_value = {"prompt": "テスト用プロンプト"}
        mock_client.call_api = mock_call_api
        mock_client.extract_content.return_value = """```csv
tweet_text,hashtags,media_suggestion
「メインタイトル」で取り上げた基本概念について解説しています！,#プログラミング #初心者向け,
実際に手を動かして学べる「メインタイトル」の実践編をチェック！,#プログラミング学習 #ハンズオン,https://example.com/image1.jpg
「メインタイトル」のポイントを5分でまとめました。,#5分解説 #初心者歓迎,
```"""
        # モッククライアントを注入
        tweet_generator.client = mock_client
        
        article_content = "# メインタイトル\n\nこれは記事の内容です..."
        
        # os.makedirsをモック化
        with patch('os.makedirs') as mock_makedirs:
            # 出力パスを指定
            output_path = "output/tweets.csv"
            
            # 非同期メソッドのテスト
            result = await tweet_generator.generate(sample_structure_data, article_content, 5, 280, output_path)
            
            # 結果が正しいことを確認
            assert result is not None
            assert isinstance(result, str)
            assert "「メインタイトル」で取り上げた基本概念について解説しています！" in result
            assert "#プログラミング" in result
            
            # os.makedirsが呼ばれたことを確認
            mock_makedirs.assert_called_once_with(os.path.dirname(output_path), exist_ok=True)
            
            # API呼び出しの準備が行われたことを確認
            mock_client.prepare_request.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_async_auto_output_path(self, tweet_generator, sample_structure_with_section):
        """出力パスが自動生成される非同期ツイート生成のテスト"""
        # モックの非同期メソッド定義
        async def mock_call_api(request):
            return {
                "content": [
                    {
                        "type": "text",
                        "text": """```csv
tweet_text,hashtags,media_suggestion
「メインタイトル」で取り上げた基本概念について解説しています！,#プログラミング #初心者向け,
実際に手を動かして学べる「メインタイトル」の実践編をチェック！,#プログラミング学習 #ハンズオン,https://example.com/image1.jpg
「メインタイトル」のポイントを5分でまとめました。,#5分解説 #初心者歓迎,
```"""
                    }
                ]
            }
        
        # クライアントのモック設定
        mock_client = MagicMock()
        mock_client.prepare_request.return_value = {"prompt": "テスト用プロンプト"}
        mock_client.call_api = mock_call_api
        mock_client.extract_content.return_value = """```csv
tweet_text,hashtags,media_suggestion
「メインタイトル」で取り上げた基本概念について解説しています！,#プログラミング #初心者向け,
実際に手を動かして学べる「メインタイトル」の実践編をチェック！,#プログラミング学習 #ハンズオン,https://example.com/image1.jpg
「メインタイトル」のポイントを5分でまとめました。,#5分解説 #初心者歓迎,
```"""
        # モッククライアントを注入
        tweet_generator.client = mock_client
        
        article_content = "# メインタイトル\n\nこれは記事の内容です..."
        
        # get_output_pathとos.makedirsをモック化
        expected_path = "メインタイトル/チャプター1/セクション1/tweets.csv"
        with patch.object(tweet_generator, 'get_output_path', return_value=expected_path) as mock_get_path, \
             patch('os.makedirs') as mock_makedirs:
            
            # 出力パスを指定せずに非同期メソッドを呼び出し
            result = await tweet_generator.generate(sample_structure_with_section, article_content)
            
            # 結果が正しいことを確認
            assert result is not None
            assert isinstance(result, str)
            assert "「メインタイトル」" in result
            
            # get_output_pathが正しく呼ばれたことを確認
            mock_get_path.assert_called_once_with(sample_structure_with_section, 'section', 'tweets.csv')
            
            # os.makedirsが呼ばれたことを確認
            mock_makedirs.assert_called_once_with(os.path.dirname(expected_path), exist_ok=True)
    
    def test_generate_tweets(self, tweet_generator, sample_structure_data, monkeypatch):
        """同期版ツイート生成のテスト"""
        # モックレスポンス用のCSV文字列
        expected_result = """tweet_text,hashtags,media_suggestion
「メインタイトル」で取り上げた基本概念について解説しています！,#プログラミング #初心者向け,
実際に手を動かして学べる「メインタイトル」の実践編をチェック！,#プログラミング学習 #ハンズオン,https://example.com/image1.jpg
「メインタイトル」のポイントを5分でまとめました。,#5分解説 #初心者歓迎,
"""
        
        # モック化して同期メソッドが非同期メソッドを呼び出すことをシミュレート
        async def mock_generate(structure, article_content, tweet_count=5, max_length=280, output_path=None):
            assert structure == sample_structure_data
            assert "記事の内容" in article_content
            assert tweet_count == 5
            assert max_length == 280
            assert output_path is None or output_path == "test_output.csv"
            return expected_result
        
        # 非同期メソッドをモック
        monkeypatch.setattr(tweet_generator, 'generate', mock_generate)
        
        article_content = "# メインタイトル\n\nこれは記事の内容です..."
        
        # 出力パスなしでテスト
        result1 = tweet_generator.generate_tweets(sample_structure_data, article_content)
        assert result1 == expected_result
        
        # 出力パスありでテスト
        result2 = tweet_generator.generate_tweets(sample_structure_data, article_content, 5, 280, "test_output.csv")
        assert result2 == expected_result
        
        # CSVとして解析可能かチェック
        try:
            csv_file = io.StringIO(result1)
            reader = csv.DictReader(csv_file)
            rows = list(reader)
            assert len(rows) == 3
            assert "tweet_text" in rows[0]
            assert "hashtags" in rows[0]
            assert "media_suggestion" in rows[0]
        except Exception:
            assert False, "結果は有効なCSV形式ではありません" 