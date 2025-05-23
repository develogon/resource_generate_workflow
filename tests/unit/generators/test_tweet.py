"""Tweet generator tests."""

import pytest
import json
from unittest.mock import Mock, AsyncMock, MagicMock

from src.generators.tweet import TweetGenerator
from src.generators.base import GenerationType, GenerationRequest, GenerationResult
from src.models import Content
from src.config import Config


class TestTweetGenerator:
    """TweetGenerator tests."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock config."""
        config = MagicMock()
        # Mock workers config
        workers_mock = MagicMock()
        workers_mock.max_concurrent_tasks = 5
        config.workers = workers_mock
        return config
        
    @pytest.fixture
    def generator(self, mock_config):
        """Create TweetGenerator instance."""
        return TweetGenerator(mock_config)
        
    def test_get_generation_type(self, generator):
        """Test generation type."""
        assert generator.get_generation_type() == GenerationType.TWEET
        
    def test_get_prompt_template(self, generator):
        """Test prompt template."""
        template = generator.get_prompt_template()
        assert "ツイート" in template
        assert "{title}" in template
        assert "{content}" in template
        assert "280文字" in template
        
    def test_max_tweet_length(self, generator):
        """Test maximum tweet length constant."""
        assert generator.max_tweet_length == 280
        
    @pytest.mark.asyncio
    async def test_generate_success(self, generator):
        """Test successful tweet generation."""
        content = Content(
            id="test-1",
            title="技術テスト",
            content="テスト用のコンテンツです。技術的な内容を含みます。",
            metadata={}
        )
        request = GenerationRequest(
            content=content,
            generation_type=GenerationType.TWEET,
            options={"title": "技術テスト"},
            context={}
        )
        
        result = await generator.generate(request)
        
        assert result.success is True
        assert result.content != ""
        assert result.generation_type == GenerationType.TWEET
        
        # JSON形式の確認
        try:
            tweet_data = json.loads(result.content)
            assert "tweets" in tweet_data
            assert isinstance(tweet_data["tweets"], list)
            assert len(tweet_data["tweets"]) > 0
        except json.JSONDecodeError:
            pytest.fail("Generated tweet is not valid JSON")
            
    @pytest.mark.asyncio
    async def test_generate_with_ai_client(self, generator):
        """Test generation with AI client."""
        # Mock AI client
        mock_ai_client = AsyncMock()
        mock_response = {
            "content": json.dumps({
                "tweets": [
                    {
                        "content": "🚀 AI生成のテストツイートです！ #AI #テスト",
                        "character_count": 25,
                        "hashtags": ["AI", "テスト"],
                        "emojis": ["🚀"],
                        "call_to_action": "いいねお願いします",
                        "engagement_type": "like"
                    }
                ],
                "target_audience": "AI技術者"
            })
        }
        mock_ai_client.generate.return_value = mock_response
        generator.set_ai_client(mock_ai_client)
        
        content = Content(
            id="test-2",
            title="AI",
            content="AI技術について",
            metadata={}
        )
        request = GenerationRequest(
            content=content,
            generation_type=GenerationType.TWEET,
            options={"title": "AI"},
            context={}
        )
        
        result = await generator.generate(request)
        
        assert result.success is True
        tweet_data = json.loads(result.content)
        assert len(tweet_data["tweets"]) == 1
        assert "AI生成" in tweet_data["tweets"][0]["content"]
        mock_ai_client.generate.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_simulate_tweet_generation(self, generator):
        """Test tweet simulation."""
        prompt = "テストプロンプト"
        options = {"title": "シミュレーションテスト"}
        
        result = await generator._simulate_tweet_generation(prompt, options)
        
        assert result != ""
        
        # JSON形式の確認
        tweet_data = json.loads(result)
        assert "tweets" in tweet_data
        assert len(tweet_data["tweets"]) == 2  # Default template has 2 tweets
        
    def test_extract_hashtags(self, generator):
        """Test hashtag extraction."""
        content = "これはテストです #技術 #プログラミング #AI"
        hashtags = generator._extract_hashtags(content)
        
        assert "技術" in hashtags
        assert "プログラミング" in hashtags
        assert "AI" in hashtags
        assert len(hashtags) == 3
        
    def test_extract_emojis(self, generator):
        """Test emoji extraction."""
        content = "🚀 テストです 💡 素晴らしい 👍"
        emojis = generator._extract_emojis(content)
        
        assert "🚀" in emojis
        assert "💡" in emojis
        assert "👍" in emojis
        
    def test_remove_emojis(self, generator):
        """Test emoji removal."""
        content = "🚀 テストです 💡 素晴らしい 👍"
        clean_content = generator._remove_emojis(content)
        
        assert "🚀" not in clean_content
        assert "💡" not in clean_content
        assert "👍" not in clean_content
        assert "テストです" in clean_content
        assert "素晴らしい" in clean_content
        
    def test_truncate_tweet_within_limit(self, generator):
        """Test tweet truncation when within limit."""
        content = "短いツイートです #テスト"
        result = generator._truncate_tweet(content)
        
        assert result == content  # Should remain unchanged
        assert len(result) <= generator.max_tweet_length
        
    def test_truncate_tweet_over_limit(self, generator):
        """Test tweet truncation when over limit."""
        # Create content over 280 characters
        long_content = "これは非常に長いツイートのテストです。" * 20  # Much longer
        long_content += " #テスト #プログラミング 🚀"
        
        result = generator._truncate_tweet(long_content)
        
        assert len(result) <= generator.max_tweet_length
        assert "..." in result  # Truncation indicator
        
    def test_post_process_tweets_valid_json(self, generator):
        """Test post-processing valid tweet JSON."""
        tweet_json = json.dumps({
            "tweets": [
                {
                    "content": "テストツイート #テスト 🚀",
                    "hashtags": ["テスト"],
                    "emojis": ["🚀"]
                }
            ]
        })
        
        content = Content(
            id="test-3",
            title="test",
            content="test",
            metadata={}
        )
        request = GenerationRequest(
            content=content,
            generation_type=GenerationType.TWEET,
            options={},
            context={}
        )
        
        result = generator._post_process_tweets(tweet_json, request)
        
        # Should return valid JSON
        parsed = json.loads(result)
        assert "tweets" in parsed
        assert len(parsed["tweets"]) == 1
        
    def test_post_process_tweets_character_count(self, generator):
        """Test character count calculation in post-processing."""
        tweet_json = json.dumps({
            "tweets": [
                {
                    "content": "テストツイート",
                    "hashtags": [],
                    "emojis": []
                }
            ]
        })
        
        content = Content(
            id="test-4",
            title="test",
            content="test",
            metadata={}
        )
        request = GenerationRequest(
            content=content,
            generation_type=GenerationType.TWEET,
            options={},
            context={}
        )
        
        result = generator._post_process_tweets(tweet_json, request)
        parsed = json.loads(result)
        
        tweet = parsed["tweets"][0]
        assert tweet["character_count"] == len(tweet["content"])
        
    def test_post_process_tweets_over_limit(self, generator):
        """Test post-processing when tweet is over character limit."""
        # Create tweet over limit
        long_content = "非常に長いツイートテスト。" * 20  # Over 280 chars
        
        tweet_json = json.dumps({
            "tweets": [
                {
                    "content": long_content,
                    "hashtags": ["テスト"],
                    "emojis": ["🚀"]
                }
            ]
        })
        
        content = Content(
            id="test-5",
            title="test",
            content="test",
            metadata={}
        )
        request = GenerationRequest(
            content=content,
            generation_type=GenerationType.TWEET,
            options={},
            context={}
        )
        
        result = generator._post_process_tweets(tweet_json, request)
        parsed = json.loads(result)
        
        tweet = parsed["tweets"][0]
        assert tweet["character_count"] <= generator.max_tweet_length
        
    def test_analyze_tweets_valid(self, generator):
        """Test tweet analysis with valid JSON."""
        tweet_data = json.dumps({
            "tweets": [
                {
                    "content": "ツイート1 #tech",
                    "character_count": 10,
                    "hashtags": ["tech"],
                    "emojis": ["🚀"],
                    "engagement_type": "like"
                },
                {
                    "content": "ツイート2 #coding",
                    "character_count": 12,
                    "hashtags": ["coding"],
                    "emojis": ["💡"],
                    "engagement_type": "retweet"
                }
            ],
            "target_audience": "エンジニア"
        })
        
        metadata = generator._analyze_tweets(tweet_data)
        
        assert metadata["total_tweets"] == 2
        assert metadata["total_characters"] == 22
        assert metadata["average_characters"] == 11.0
        assert metadata["hashtag_count"] == 2
        assert "tech" in metadata["unique_hashtags"]
        assert "coding" in metadata["unique_hashtags"]
        assert metadata["emoji_count"] == 2
        assert metadata["engagement_types"]["like"] == 1
        assert metadata["engagement_types"]["retweet"] == 1
        assert metadata["target_audience"] == "エンジニア"
        assert metadata["is_thread"] is True  # More than 1 tweet
        
    def test_analyze_tweets_invalid(self, generator):
        """Test tweet analysis with invalid JSON."""
        invalid_tweet = "not json content"
        
        metadata = generator._analyze_tweets(invalid_tweet)
        
        # Should return basic stats
        assert "content_length" in metadata
        assert "line_count" in metadata
        
    @pytest.mark.asyncio
    async def test_generate_invalid_request(self, generator):
        """Test generation with invalid request."""
        content = Content(
            id="test-6",
            title="",
            content="",  # Empty content
            metadata={}
        )
        request = GenerationRequest(
            content=content,
            generation_type=GenerationType.TWEET,
            options={},
            context={}
        )
        
        result = await generator.generate(request)
        
        assert result.success is False
        assert result.error == "Invalid request"
        
    @pytest.mark.asyncio
    async def test_generate_wrong_type(self, generator):
        """Test generation with wrong type."""
        content = Content(
            id="test-7",
            title="test",
            content="test",
            metadata={}
        )
        request = GenerationRequest(
            content=content,
            generation_type=GenerationType.SCRIPT,  # Wrong type
            options={},
            context={}
        )
        
        result = await generator.generate(request)
        
        assert result.success is False
        assert result.error == "Invalid request"
        
    def test_hashtag_extraction_edge_cases(self, generator):
        """Test hashtag extraction edge cases."""
        # No hashtags
        assert generator._extract_hashtags("ハッシュタグなし") == []
        
        # Multiple same hashtags
        content = "#test #テスト #test"
        hashtags = generator._extract_hashtags(content)
        assert hashtags.count("test") == 2
        
        # Hashtags with numbers
        content = "#tech2024 #AI4all"
        hashtags = generator._extract_hashtags(content)
        assert "tech2024" in hashtags
        assert "AI4all" in hashtags
        
    def test_emoji_extraction_edge_cases(self, generator):
        """Test emoji extraction edge cases."""
        # No emojis
        assert generator._extract_emojis("絵文字なし") == []
        
        # Multiple same emojis
        content = "🚀🚀💡🚀"
        emojis = generator._extract_emojis(content)
        assert len(emojis) >= 1  # At least one emoji found
        
    def test_character_limit_constants(self, generator):
        """Test character limit handling."""
        # Test with exactly 280 characters
        content = "a" * 280
        result = generator._truncate_tweet(content)
        assert len(result) <= 280
        
        # Test with 281 characters
        content = "a" * 281
        result = generator._truncate_tweet(content)
        assert len(result) <= 280 