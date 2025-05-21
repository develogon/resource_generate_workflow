import pytest
import csv
from io import StringIO
from unittest.mock import patch, MagicMock, mock_open

from generators.tweets import TweetsGenerator
from tests.fixtures.sample_tweets_data import (
    SAMPLE_TWEETS_INPUT,
    SAMPLE_TWEETS_TEMPLATE,
    SAMPLE_GENERATED_TWEETS
)


class TestTweetsGenerator:
    """ツイート生成器のテスト"""

    @pytest.fixture
    def mock_claude_service(self):
        """モックClaudeサービス"""
        mock = MagicMock()
        mock.generate_content.return_value = {
            "content": SAMPLE_GENERATED_TWEETS
        }
        return mock

    @pytest.fixture
    def tweets_generator(self, mock_claude_service):
        """TweetsGeneratorインスタンス"""
        file_manager = MagicMock()
        return TweetsGenerator(claude_service=mock_claude_service, file_manager=file_manager)

    def test_generate(self, tweets_generator, mock_claude_service):
        """ツイート生成のテスト"""
        # テスト用入力データ
        input_data = SAMPLE_TWEETS_INPUT
        
        # テンプレート読み込みのモック
        with patch('builtins.open', mock_open(read_data=SAMPLE_TWEETS_TEMPLATE)):
            # ツイート生成実行
            result = tweets_generator.generate(input_data)
            
            # Claude APIが呼ばれたことを確認
            mock_claude_service.generate_content.assert_called_once()
            
            # 結果の検証
            assert "tweet_text,hashtags,topic,character_count" in result
            assert "Goの並行処理の魅力は軽量なgoroutineにあります" in result
            assert "#Go #golang #programming" in result

    def test_format_output(self, tweets_generator):
        """出力フォーマットのテスト"""
        # 生成されたツイートテキスト
        csv_text = SAMPLE_GENERATED_TWEETS
        
        # フォーマット実行
        formatted = tweets_generator.format_output(csv_text)
        
        # CSVとして解析可能であることを確認
        csv_reader = csv.DictReader(StringIO(formatted))
        tweets = list(csv_reader)
        
        # CSV形式が正しいことを確認
        assert len(tweets) == 5
        assert "tweet_text" in tweets[0]
        assert "hashtags" in tweets[0]
        assert "topic" in tweets[0]
        assert "character_count" in tweets[0]
        
        # 各ツイートの内容が正しいことを確認
        assert "goroutine" in tweets[0]["tweet_text"]
        assert "#Go" in tweets[0]["hashtags"]
        assert "並行処理" in tweets[0]["topic"]
        
        # 無効なCSV
        invalid_csv = "invalid,csv,format\nwithout,proper,headers"
        formatted_invalid = tweets_generator.format_output(invalid_csv)
        assert "tweet_text,hashtags,topic,character_count" in formatted_invalid
        
        # 空のCSV
        empty_csv = ""
        formatted_empty = tweets_generator.format_output(empty_csv)
        assert "tweet_text,hashtags,topic,character_count" in formatted_empty

    def test_validate_content(self, tweets_generator):
        """ツイート検証のテスト"""
        # 有効なツイートCSV
        valid_csv = SAMPLE_GENERATED_TWEETS
        assert tweets_generator.validate_content(valid_csv) is True
        
        # 無効なツイートCSV（空）
        assert tweets_generator.validate_content("") is False
        
        # 無効なツイートCSV（ヘッダーがない）
        invalid_csv = "これはCSVではないテキスト"
        assert tweets_generator.validate_content(invalid_csv) is False
        
        # ヘッダーはあるが内容がない
        header_only = "tweet_text,hashtags,topic,character_count\n"
        assert tweets_generator.validate_content(header_only) is False

    def test_check_tweet_length(self, tweets_generator):
        """ツイート長さチェックのテスト"""
        # 適切な長さのツイート
        valid_tweet = "これは280文字以内のツイートです。 #test"
        assert tweets_generator.check_tweet_length(valid_tweet) is True
        
        # 長すぎるツイート（281文字）
        long_tweet = "あ" * 281
        assert tweets_generator.check_tweet_length(long_tweet) is False
        
        # 境界値テスト（280文字ちょうど）
        edge_tweet = "あ" * 280
        assert tweets_generator.check_tweet_length(edge_tweet) is True
        
        # 境界値テスト（281文字）
        over_edge_tweet = "あ" * 281
        assert tweets_generator.check_tweet_length(over_edge_tweet) is False

    def test_format_hashtags(self, tweets_generator):
        """ハッシュタグフォーマットのテスト"""
        # 複数のハッシュタグ
        hashtags = ["Go", "golang", "programming"]
        formatted = tweets_generator.format_hashtags(hashtags)
        assert formatted == "#Go #golang #programming"
        
        # 空のハッシュタグリスト
        empty_hashtags = []
        formatted_empty = tweets_generator.format_hashtags(empty_hashtags)
        assert formatted_empty == ""
        
        # 特殊文字を含むハッシュタグ
        special_hashtags = ["Go-lang", "test/programming", "a b c"]
        formatted_special = tweets_generator.format_hashtags(special_hashtags)
        assert formatted_special == "#Golang #testprogramming #abc" 