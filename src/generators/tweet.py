"""ツイート生成器."""

import asyncio
import logging
import re
from typing import Dict, Any, Optional, List

from .base import BaseGenerator, GenerationType, GenerationRequest, GenerationResult
from ..config import Config

logger = logging.getLogger(__name__)


class TweetGenerator(BaseGenerator):
    """パラグラフからツイート（短文投稿）を生成する生成器."""
    
    def __init__(self, config: Config):
        """初期化."""
        super().__init__(config)
        self.ai_client = None  # AI客户端将在运行时注入
        self.max_tweet_length = 280  # Twitter の文字数制限
        
    def get_generation_type(self) -> GenerationType:
        """生成タイプを返す."""
        return GenerationType.TWEET
        
    def get_prompt_template(self) -> str:
        """プロンプトテンプレートを返す."""
        return """あなたは経験豊富なソーシャルメディアマーケターです。以下のコンテンツをもとに、魅力的なツイートを作成してください。

# 元コンテンツ
タイトル: {title}
内容: {content}

# ツイート作成の要件
1. 文字数は280文字以内に収める
2. エンゲージメントを高めるキャッチーな表現を使う
3. 適切なハッシュタグを2-3個含める
4. 絵文字を効果的に使用する
5. アクションを促す文言を含める（いいね、RT、リプライなど）
6. 内容の要点を分かりやすく要約する

# 出力形式
以下のJSON形式で出力してください：
```json
{{
    "tweets": [
        {{
            "content": "ツイート内容",
            "character_count": 文字数,
            "hashtags": ["ハッシュタグ1", "ハッシュタグ2"],
            "emojis": ["使用した絵文字"],
            "call_to_action": "アクション促進の文言",
            "engagement_type": "like|retweet|reply|share"
        }}
    ],
    "thread_sequence": [
        "複数ツイートの場合の順序説明"
    ],
    "target_audience": "ターゲット層",
    "posting_time": "推奨投稿時間帯"
}}
```

ツイートを作成してください："""

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        """ツイートを生成.
        
        Args:
            request: 生成リクエスト
            
        Returns:
            生成結果
        """
        if not self.validate_request(request):
            return GenerationResult(
                content="",
                metadata={},
                generation_type=self.get_generation_type(),
                success=False,
                error="Invalid request"
            )
            
        try:
            # プロンプトを構築
            prompt = self.build_prompt(request)
            
            # AI生成を実行
            tweet_content = await self._generate_tweet_content(prompt, request.options)
            
            # 結果の後処理
            processed_tweets = self._post_process_tweets(tweet_content, request)
            
            # メタデータ生成
            metadata = self.extract_metadata(request, processed_tweets)
            metadata.update(self._analyze_tweets(processed_tweets))
            
            return GenerationResult(
                content=processed_tweets,
                metadata=metadata,
                generation_type=self.get_generation_type(),
                success=True
            )
            
        except Exception as e:
            logger.error(f"Tweet generation failed: {e}")
            return GenerationResult(
                content="",
                metadata={},
                generation_type=self.get_generation_type(),
                success=False,
                error=str(e)
            )
            
    async def _generate_tweet_content(self, prompt: str, options: Dict[str, Any]) -> str:
        """AIを使用してツイートコンテンツを生成."""
        if not self.ai_client:
            # AI客户端未设置时使用模拟生成
            return await self._simulate_tweet_generation(prompt, options)
            
        try:
            # AI呼び出し
            response = await self.ai_client.generate(
                prompt=prompt,
                max_tokens=options.get("max_tokens", 800),
                temperature=options.get("temperature", 0.8)  # ツイートは創造性を重視
            )
            
            if response and "content" in response:
                return response["content"]
            else:
                raise ValueError("Invalid AI response")
                
        except Exception as e:
            logger.warning(f"AI generation failed, using fallback: {e}")
            return await self._simulate_tweet_generation(prompt, options)
            
    async def _simulate_tweet_generation(self, prompt: str, options: Dict[str, Any]) -> str:
        """AI生成のシミュレーション（テスト用）."""
        import json
        
        title = options.get("title", "技術トピック")
        
        # 複数のツイートバリエーションを生成
        tweet_templates = [
            {
                "content": f"🚀 {title}について学んだことをシェア！\n\n実際に試してみて分かったポイントをまとめました💡\n\n詳細はコメントで質問お待ちしています👇\n\n#{title} #技術 #学習",
                "character_count": 95,
                "hashtags": [title, "技術", "学習"],
                "emojis": ["🚀", "💡", "👇"],
                "call_to_action": "コメントで質問お待ちしています",
                "engagement_type": "reply"
            },
            {
                "content": f"💭 {title}で知っておくべき3つのポイント\n\n✅ ポイント1\n✅ ポイント2\n✅ ポイント3\n\n同じ経験をした人はいいね👍\n\n#{title} #まとめ #技術Tips",
                "character_count": 85,
                "hashtags": [title, "まとめ", "技術Tips"],
                "emojis": ["💭", "✅", "👍"],
                "call_to_action": "同じ経験をした人はいいね",
                "engagement_type": "like"
            }
        ]
        
        tweet_data = {
            "tweets": tweet_templates,
            "thread_sequence": [
                "1. 概要ツイート（興味を引く）",
                "2. 詳細ツイート（具体的な内容）",
                "3. まとめツイート（アクション促進）"
            ],
            "target_audience": "技術に興味のある人、学習者",
            "posting_time": "平日19-21時、土日13-15時"
        }
        
        # 非同期処理のシミュレーション
        await asyncio.sleep(0.1)
        
        return json.dumps(tweet_data, ensure_ascii=False, indent=2)
        
    def _post_process_tweets(self, tweet_content: str, request: GenerationRequest) -> str:
        """ツイートの後処理."""
        import json
        import re
        
        try:
            # JSONブロックを抽出
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', tweet_content, re.DOTALL)
            if json_match:
                json_content = json_match.group(1)
            else:
                json_content = tweet_content.strip()
                
            # JSON解析
            tweet_data = json.loads(json_content)
            
            # 各ツイートの文字数チェックと修正
            if "tweets" in tweet_data:
                for tweet in tweet_data["tweets"]:
                    content = tweet.get("content", "")
                    
                    # 文字数チェック
                    if len(content) > self.max_tweet_length:
                        # 文字数オーバーの場合は短縮
                        tweet["content"] = self._truncate_tweet(content)
                        tweet["character_count"] = len(tweet["content"])
                        logger.warning(f"Tweet truncated due to character limit: {len(content)} -> {len(tweet['content'])}")
                    else:
                        tweet["character_count"] = len(content)
                        
                    # ハッシュタグとemojisの更新
                    tweet["hashtags"] = self._extract_hashtags(tweet["content"])
                    tweet["emojis"] = self._extract_emojis(tweet["content"])
                    
            return json.dumps(tweet_data, ensure_ascii=False, indent=2)
            
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in tweets, returning raw content: {e}")
            return tweet_content
            
    def _truncate_tweet(self, content: str) -> str:
        """ツイートを文字数制限内に短縮."""
        if len(content) <= self.max_tweet_length:
            return content
            
        # 単純に文字数制限内に切り詰める
        truncated = content[:self.max_tweet_length - 3] + "..."
        return truncated
        
    def _extract_hashtags(self, content: str) -> List[str]:
        """ツイートからハッシュタグを抽出."""
        hashtags = re.findall(r'#(\w+)', content)
        return hashtags
        
    def _extract_emojis(self, content: str) -> List[str]:
        """ツイートから絵文字を抽出."""
        # より正確な絵文字パターン（主要な絵文字のみ）
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # 顔文字
            "\U0001F300-\U0001F5FF"  # 記号&絵文字
            "\U0001F680-\U0001F6FF"  # 乗り物&建物
            "\U0001F1E0-\U0001F1FF"  # 国旗
            "\U00002600-\U000026FF"  # その他記号
            "\U0001F900-\U0001F9FF"  # 補助絵文字
            "]", flags=re.UNICODE
        )
        
        emojis = emoji_pattern.findall(content)
        return emojis
        
    def _remove_emojis(self, content: str) -> str:
        """テキストから絵文字を除去."""
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # 顔文字
            "\U0001F300-\U0001F5FF"  # 記号&絵文字
            "\U0001F680-\U0001F6FF"  # 乗り物&建物
            "\U0001F1E0-\U0001F1FF"  # 国旗
            "\U00002600-\U000026FF"  # その他記号
            "\U0001F900-\U0001F9FF"  # 補助絵文字
            "]", flags=re.UNICODE
        )
        
        return emoji_pattern.sub(' ', content).strip()
        
    def _analyze_tweets(self, tweet_content: str) -> Dict[str, Any]:
        """ツイートを分析してメタデータを生成."""
        import json
        
        try:
            tweet_data = json.loads(tweet_content)
            tweets = tweet_data.get("tweets", [])
            
            # 統計情報の計算
            total_tweets = len(tweets)
            total_characters = sum(tweet.get("character_count", 0) for tweet in tweets)
            avg_characters = total_characters / total_tweets if total_tweets > 0 else 0
            
            # ハッシュタグ分析
            all_hashtags = []
            for tweet in tweets:
                all_hashtags.extend(tweet.get("hashtags", []))
            unique_hashtags = list(set(all_hashtags))
            
            # 絵文字分析
            all_emojis = []
            for tweet in tweets:
                all_emojis.extend(tweet.get("emojis", []))
            unique_emojis = list(set(all_emojis))
            
            # エンゲージメントタイプ分析
            engagement_types = {}
            for tweet in tweets:
                eng_type = tweet.get("engagement_type", "unknown")
                engagement_types[eng_type] = engagement_types.get(eng_type, 0) + 1
                
            return {
                "total_tweets": total_tweets,
                "total_characters": total_characters,
                "average_characters": round(avg_characters, 1),
                "hashtag_count": len(unique_hashtags),
                "unique_hashtags": unique_hashtags,
                "emoji_count": len(unique_emojis),
                "unique_emojis": unique_emojis,
                "engagement_types": engagement_types,
                "target_audience": tweet_data.get("target_audience", ""),
                "is_thread": len(tweets) > 1
            }
            
        except json.JSONDecodeError:
            return {
                "content_length": len(tweet_content),
                "line_count": len(tweet_content.split('\n')),
                "estimated_tweets": tweet_content.count('content":') if 'content":' in tweet_content else 1
            }
            
    def set_ai_client(self, ai_client):
        """AI客户端を設定."""
        self.ai_client = ai_client 