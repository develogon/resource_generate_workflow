"""記事生成器."""

import logging
from typing import Dict, Any

from .base import BaseGenerator, GenerationType, GenerationRequest, GenerationResult
from ..config import Config

logger = logging.getLogger(__name__)


class ArticleGenerator(BaseGenerator):
    """記事生成器."""
    
    def __init__(self, config: Config):
        """初期化."""
        super().__init__(config)
        
    def get_generation_type(self) -> GenerationType:
        """生成タイプを返す."""
        return GenerationType.ARTICLE
        
    def get_prompt_template(self) -> str:
        """プロンプトテンプレートを返す."""
        return """以下のコンテンツを基に、詳細で読みやすい記事を生成してください。

タイトル: {title}
元のコンテンツ: {content}

記事の要件:
- 読者にとって理解しやすい構成にする
- 具体例や詳細な説明を含める
- 適切な見出しと段落構成を使用する
- 専門用語には説明を加える
- 読み手の興味を引く導入部を含める

スタイル: {style}
言語: {lang}

記事:"""
        
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
        """記事コンテンツの生成.
        
        Args:
            prompt: 生成用プロンプト
            request: 生成リクエスト
            
        Returns:
            生成された記事コンテンツ
        """
        # 実際のAI APIを使用した生成処理
        # ここでは簡易的な実装を提供
        
        # オプションから設定を取得
        style = request.options.get('style', 'formal')
        target_length = request.options.get('target_length', 'medium')
        include_examples = request.options.get('include_examples', True)
        
        # 基本的な記事構造を生成
        article_parts = []
        
        # 導入部
        intro = self._generate_introduction(request.content.title, request.content.content, style)
        article_parts.append(intro)
        
        # 本文
        main_content = self._generate_main_content(
            request.content.content, 
            style, 
            target_length,
            include_examples
        )
        article_parts.append(main_content)
        
        # 結論
        conclusion = self._generate_conclusion(request.content.title, style)
        article_parts.append(conclusion)
        
        return "\n\n".join(article_parts)
        
    def _generate_introduction(self, title: str, content: str, style: str) -> str:
        """導入部の生成."""
        if style == 'casual':
            return f"# {title}\n\n今回は「{title}」について詳しく見ていきましょう。{content[:100]}...について、わかりやすく解説していきます。"
        else:
            return f"# {title}\n\n本記事では、{title}について詳細に解説いたします。{content[:100]}...に関する重要なポイントを整理し、理解を深めていただけるよう構成しております。"
            
    def _generate_main_content(self, content: str, style: str, target_length: str, include_examples: bool) -> str:
        """本文の生成."""
        sections = []
        
        # コンテンツを分析して主要なポイントを抽出
        key_points = self._extract_key_points(content)
        
        for i, point in enumerate(key_points, 1):
            section_title = f"## {i}. {point['title']}"
            section_content = point['content']
            
            if include_examples and point.get('example'):
                section_content += f"\n\n**例：** {point['example']}"
                
            sections.append(f"{section_title}\n\n{section_content}")
            
        return "\n\n".join(sections)
        
    def _generate_conclusion(self, title: str, style: str) -> str:
        """結論の生成."""
        if style == 'casual':
            return f"## まとめ\n\n{title}について解説してきました。これらのポイントを押さえることで、より深い理解が得られるはずです。"
        else:
            return f"## 結論\n\n本記事では{title}について詳細に検討いたしました。これらの知見が皆様の理解促進に寄与することを期待しております。"
            
    def _extract_key_points(self, content: str) -> list[Dict[str, str]]:
        """コンテンツから主要なポイントを抽出."""
        # 簡易的な実装：文章を分割して主要ポイントとして扱う
        sentences = content.split('。')
        key_points = []
        
        for i, sentence in enumerate(sentences[:3]):  # 最大3つのポイント
            if sentence.strip():
                key_points.append({
                    'title': f"ポイント{i+1}",
                    'content': sentence.strip() + '。',
                    'example': f"具体例として、{sentence.strip()[:30]}...が挙げられます。"
                })
                
        return key_points
        
    def _extract_article_metadata(self, content: str, request: GenerationRequest) -> Dict[str, Any]:
        """記事固有のメタデータを抽出."""
        # 見出しの数を数える
        heading_count = content.count('#')
        
        # 段落数を数える
        paragraph_count = len([p for p in content.split('\n\n') if p.strip()])
        
        # 推定読了時間（1分間に200文字として計算）
        estimated_reading_time = max(1, len(content) // 200)
        
        return {
            'article_type': 'generated',
            'heading_count': heading_count,
            'paragraph_count': paragraph_count,
            'estimated_reading_time_minutes': estimated_reading_time,
            'style': request.options.get('style', 'formal'),
            'target_length': request.options.get('target_length', 'medium'),
            'include_examples': request.options.get('include_examples', True)
        } 