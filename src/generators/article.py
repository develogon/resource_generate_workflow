"""記事生成器."""

import logging
from typing import Dict, Any

from .base import BaseGenerator, GenerationType, GenerationRequest, GenerationResult

# Config のインポートをオプション化
try:
    from ..config import Config
except ImportError:
    # テスト環境など、config が利用できない場合のフォールバック
    class Config:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

logger = logging.getLogger(__name__)


class ArticleGenerator(BaseGenerator):
    """記事生成器."""
    
    def __init__(self, config: Config):
        """初期化."""
        super().__init__(config)
        
    def get_generation_type(self) -> GenerationType:
        """生成タイプを返す."""
        return GenerationType.ARTICLE
        
    async def generate(self, request: GenerationRequest) -> GenerationResult:
        """記事の生成.
        
        Args:
            request: 生成リクエスト
            
        Returns:
            生成結果
        """
        try:
            # リクエストの検証
            if not self.validate_request(request):
                return GenerationResult(
                    content="",
                    metadata={},
                    generation_type=self.get_generation_type(),
                    success=False,
                    error="Invalid generation request"
                )
                
            # プロンプトの構築
            prompt = self.build_prompt(request)
            
            # 記事生成の実行
            generated_content = await self._generate_article_content(prompt, request)
            
            # メタデータの抽出
            metadata = self.extract_metadata(request, generated_content)
            
            # 記事固有のメタデータを追加
            metadata.update(self._extract_article_metadata(generated_content, request))
            
            return GenerationResult(
                content=generated_content,
                metadata=metadata,
                generation_type=self.get_generation_type(),
                success=True
            )
            
        except Exception as e:
            logger.error(f"Article generation failed: {e}")
            return GenerationResult(
                content="",
                metadata={},
                generation_type=self.get_generation_type(),
                success=False,
                error=str(e)
            )
            
    async def _generate_article_content(self, prompt: str, request: GenerationRequest) -> str:
        """記事コンテンツの生成."""
        # 簡単な記事生成のシミュレーション
        import asyncio
        
        title = request.title
        content = request.content
        lang = request.lang
        
        # 基本的な記事構造を生成
        article_template = f"""# {title}

## はじめに

{title}について詳しく解説します。この記事では、{content}について分かりやすく説明していきます。

## 詳細説明

{content}

これらのポイントについて、以下で詳しく見ていきましょう。

### 重要なポイント1

{title}における最初の重要なポイントは、基本的な理解です。

### 重要なポイント2

次に重要なのは、実践的な応用方法です。

### 重要なポイント3

最後に、注意すべき点について説明します。

## まとめ

{title}について説明しました。この内容を参考に、理解を深めていただければと思います。

## 参考資料

- 関連ドキュメント
- 参考リンク
- 追加情報
"""
        
        # 非同期処理のシミュレーション
        await asyncio.sleep(0.1)
        
        return article_template
        
    def _extract_article_metadata(self, content: str, request: GenerationRequest) -> Dict[str, Any]:
        """記事固有のメタデータを抽出."""
        # 見出しの数をカウント
        h1_count = content.count('# ')
        h2_count = content.count('## ')
        h3_count = content.count('### ')
        
        # 段落数をカウント
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        paragraph_count = len(paragraphs)
        
        # リンクの数をカウント
        import re
        links = re.findall(r'\[.*?\]\(.*?\)', content)
        link_count = len(links)
        
        return {
            "article_structure": {
                "h1_count": h1_count,
                "h2_count": h2_count,
                "h3_count": h3_count,
                "paragraph_count": paragraph_count,
                "link_count": link_count
            },
            "estimated_reading_time": max(1, len(content.split()) // 200),  # 分
            "content_complexity": "basic" if len(content) < 1000 else "intermediate" if len(content) < 3000 else "advanced"
        } 