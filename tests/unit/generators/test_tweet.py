import pytest
import pytest_asyncio
import csv
import io
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
    async def test_generate_async(self, tweet_generator, sample_structure_data):
        """非同期ツイート生成のテスト"""
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
        
        # 非同期メソッドのテスト
        result = await tweet_generator.generate(sample_structure_data, article_content)
        
        # 結果が正しいことを確認
        assert result is not None
        assert isinstance(result, str)
        assert "「メインタイトル」で取り上げた基本概念について解説しています！" in result
        assert "#プログラミング" in result
        
        # API呼び出しの準備が行われたことを確認
        mock_client.prepare_request.assert_called_once()
    
    def test_generate_tweets(self, tweet_generator, sample_structure_data, monkeypatch):
        """同期版ツイート生成のテスト"""
        # モックレスポンス用のCSV文字列
        expected_result = """tweet_text,hashtags,media_suggestion
「メインタイトル」で取り上げた基本概念について解説しています！,#プログラミング #初心者向け,
実際に手を動かして学べる「メインタイトル」の実践編をチェック！,#プログラミング学習 #ハンズオン,https://example.com/image1.jpg
「メインタイトル」のポイントを5分でまとめました。,#5分解説 #初心者歓迎,
"""
        
        # モック化して同期メソッドが非同期メソッドを呼び出すことをシミュレート
        async def mock_generate(*args, **kwargs):
            return expected_result
        
        # 非同期メソッドをモック
        monkeypatch.setattr(tweet_generator, 'generate', mock_generate)
        
        article_content = "# メインタイトル\n\nこれは記事の内容です..."
        
        # 同期メソッドのテスト
        result = tweet_generator.generate_tweets(sample_structure_data, article_content)
        
        # 結果が正しいことを確認
        assert result == expected_result
        
        # CSVとして解析可能かチェック
        try:
            csv_file = io.StringIO(result)
            reader = csv.DictReader(csv_file)
            rows = list(reader)
            assert len(rows) == 3
            assert "tweet_text" in rows[0]
            assert "hashtags" in rows[0]
            assert "media_suggestion" in rows[0]
        except Exception:
            assert False, "結果は有効なCSV形式ではありません" 