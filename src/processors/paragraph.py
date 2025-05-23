"""パラグラフ処理器."""

import re
from typing import List, Dict, Any
import logging

from .base import BaseProcessor, ProcessorType, ProcessingRequest, ProcessingResult
from ..models import Paragraph
from ..config import Config

logger = logging.getLogger(__name__)


class ParagraphProcessor(BaseProcessor):
    """パラグラフを解析・最適化する処理器."""
    
    def __init__(self, config: Config):
        """初期化."""
        super().__init__(config)
        
    def get_processor_type(self) -> ProcessorType:
        """処理器タイプを返す."""
        return ProcessorType.PARAGRAPH
        
    async def process(self, request: ProcessingRequest) -> ProcessingResult:
        """パラグラフを処理・最適化.
        
        Args:
            request: 処理リクエスト
            
        Returns:
            処理結果（最適化されたParagraph）
        """
        if not self.validate_request(request):
            return ProcessingResult(
                content=request.content,
                metadata={},
                processor_type=self.get_processor_type(),
                success=False,
                error="Invalid request"
            )
            
        try:
            paragraph = request.content
            if not isinstance(paragraph, Paragraph):
                return ProcessingResult(
                    content=request.content,
                    metadata={},
                    processor_type=self.get_processor_type(),
                    success=False,
                    error="Content must be a Paragraph instance"
                )
            
            # パラグラフを最適化
            optimized_paragraph = await self._optimize_paragraph(paragraph, request.options)
            
            metadata = self.extract_metadata(request, optimized_paragraph)
            metadata.update(self._analyze_paragraph(optimized_paragraph))
            
            return ProcessingResult(
                content=optimized_paragraph,
                metadata=metadata,
                processor_type=self.get_processor_type(),
                success=True
            )
            
        except Exception as e:
            logger.error(f"Paragraph processing failed: {e}")
            return ProcessingResult(
                content=request.content,
                metadata={},
                processor_type=self.get_processor_type(),
                success=False,
                error=str(e)
            )
            
    async def _optimize_paragraph(self, paragraph: Paragraph, options: Dict[str, Any]) -> Paragraph:
        """パラグラフを最適化."""
        content = paragraph.content
        
        # テキストの正規化
        if options.get("normalize_text", True):
            content = self._normalize_text(content)
        
        # 画像の抽出
        images = []
        if options.get("extract_images", True):
            content, images = self._extract_images(content)
        
        # コードブロックの抽出
        code_blocks = []
        if options.get("extract_code", True):
            content, code_blocks = self._extract_code_blocks(content)
        
        # リンクの抽出
        links = []
        if options.get("extract_links", True):
            content, links = self._extract_links(content)
        
        # メタデータの更新
        metadata = paragraph.metadata.copy()
        metadata.update({
            "images": images,
            "code_blocks": code_blocks,
            "links": links,
            "optimized": True
        })
        
        return Paragraph(
            content=content,
            index=paragraph.index,
            section_index=paragraph.section_index,
            chapter_index=paragraph.chapter_index,
            metadata=metadata
        )
        
    def _normalize_text(self, text: str) -> str:
        """テキストを正規化."""
        # 連続する空白を単一の空白に変換
        text = re.sub(r'\s+', ' ', text)
        
        # 行頭・行末の空白を削除
        text = text.strip()
        
        # 全角・半角の統一
        text = self._normalize_characters(text)
        
        return text
        
    def _normalize_characters(self, text: str) -> str:
        """文字の正規化."""
        # 全角英数字を半角に変換
        import unicodedata
        text = unicodedata.normalize('NFKC', text)
        
        return text
        
    def _extract_images(self, text: str) -> tuple[str, List[Dict[str, Any]]]:
        """画像を抽出."""
        images = []
        
        # Markdown画像パターン
        image_pattern = r'!\[([^\]]*)\]\(([^\)]+)\)'
        matches = re.finditer(image_pattern, text)
        
        for match in matches:
            alt_text = match.group(1)
            url = match.group(2)
            
            images.append({
                "alt_text": alt_text,
                "url": url,
                "type": self._detect_image_type(url),
                "original_markdown": match.group(0)
            })
        
        # 画像タグを除去（または置換）
        cleaned_text = re.sub(image_pattern, '[画像]', text)
        
        return cleaned_text, images
        
    def _extract_code_blocks(self, text: str) -> tuple[str, List[Dict[str, Any]]]:
        """コードブロックを抽出."""
        code_blocks = []
        
        # フェンスコードブロック
        fence_pattern = r'```(\w+)?\n(.*?)\n```'
        matches = re.finditer(fence_pattern, text, re.DOTALL)
        
        for match in matches:
            language = match.group(1) or "text"
            code = match.group(2)
            
            code_blocks.append({
                "language": language,
                "code": code,
                "original_markdown": match.group(0)
            })
        
        # インラインコード
        inline_pattern = r'`([^`]+)`'
        inline_matches = re.finditer(inline_pattern, text)
        
        for match in inline_matches:
            code = match.group(1)
            
            code_blocks.append({
                "language": "inline",
                "code": code,
                "original_markdown": match.group(0)
            })
        
        # コードブロックを除去（または置換）
        cleaned_text = re.sub(fence_pattern, '[コードブロック]', text, flags=re.DOTALL)
        cleaned_text = re.sub(inline_pattern, '[コード]', cleaned_text)
        
        return cleaned_text, code_blocks
        
    def _extract_links(self, text: str) -> tuple[str, List[Dict[str, Any]]]:
        """リンクを抽出."""
        links = []
        
        # Markdownリンク
        link_pattern = r'\[([^\]]+)\]\(([^\)]+)\)'
        matches = re.finditer(link_pattern, text)
        
        for match in matches:
            text_part = match.group(1)
            url = match.group(2)
            
            links.append({
                "text": text_part,
                "url": url,
                "type": self._detect_link_type(url),
                "original_markdown": match.group(0)
            })
        
        # 直接URL
        url_pattern = r'https?://[^\s]+'
        url_matches = re.finditer(url_pattern, text)
        
        for match in url_matches:
            url = match.group(0)
            
            links.append({
                "text": url,
                "url": url,
                "type": self._detect_link_type(url),
                "original_markdown": url
            })
        
        # リンクを除去（または置換）
        cleaned_text = re.sub(link_pattern, r'\1', text)
        cleaned_text = re.sub(url_pattern, '[リンク]', cleaned_text)
        
        return cleaned_text, links
        
    def _detect_image_type(self, url: str) -> str:
        """画像タイプを検出."""
        if '.svg' in url.lower():
            return 'svg'
        elif '.png' in url.lower():
            return 'png'
        elif '.jpg' in url.lower() or '.jpeg' in url.lower():
            return 'jpg'
        elif '.gif' in url.lower():
            return 'gif'
        elif 'draw.io' in url.lower() or 'diagrams.net' in url.lower():
            return 'drawio'
        elif 'mermaid' in url.lower():
            return 'mermaid'
        else:
            return 'unknown'
            
    def _detect_link_type(self, url: str) -> str:
        """リンクタイプを検出."""
        if url.startswith('http'):
            return 'external'
        elif url.startswith('#'):
            return 'anchor'
        elif url.startswith('/'):
            return 'internal'
        else:
            return 'relative'
            
    def _analyze_paragraph(self, paragraph: Paragraph) -> Dict[str, Any]:
        """パラグラフを分析してメタデータを生成."""
        content = paragraph.content
        
        # 基本統計
        word_count = len(content.split())
        char_count = len(content)
        sentence_count = len([s for s in re.split(r'[。．.!?！？]', content) if s.strip()])
        
        # 内容分析
        has_questions = bool(re.search(r'[?？]', content))
        has_code = bool(re.search(r'`[^`]+`|```', content))
        has_links = bool(re.search(r'\[.+\]\(.+\)|https?://', content))
        has_images = bool(re.search(r'!\[.*\]\(.+\)', content))
        
        # 複雑度スコア（簡易版）
        complexity_score = self._calculate_complexity(content)
        
        return {
            "word_count": word_count,
            "char_count": char_count,
            "sentence_count": sentence_count,
            "has_questions": has_questions,
            "has_code": has_code,
            "has_links": has_links,
            "has_images": has_images,
            "complexity_score": complexity_score,
            "readability_level": self._estimate_readability(content)
        }
        
    def _calculate_complexity(self, text: str) -> float:
        """テキストの複雑度スコアを計算."""
        # 簡易版の複雑度計算
        
        # 語彙の多様性
        words = text.split()
        unique_words = set(words)
        vocabulary_diversity = len(unique_words) / len(words) if words else 0
        
        # 平均文長
        sentences = [s.strip() for s in re.split(r'[。．.!?！？]', text) if s.strip()]
        avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences) if sentences else 0
        
        # 複雑な構造の存在
        has_nested_structures = bool(re.search(r'\([^)]*\([^)]*\)[^)]*\)', text))
        has_technical_terms = bool(re.search(r'[A-Z]{2,}|[a-z]+[A-Z][a-z]*', text))
        
        # スコア計算
        complexity = (
            vocabulary_diversity * 0.3 +
            min(avg_sentence_length / 20, 1.0) * 0.4 +
            (0.2 if has_nested_structures else 0) +
            (0.1 if has_technical_terms else 0)
        )
        
        return min(complexity, 1.0)
        
    def _estimate_readability(self, text: str) -> str:
        """読みやすさレベルを推定."""
        complexity = self._calculate_complexity(text)
        
        if complexity < 0.3:
            return "easy"
        elif complexity < 0.6:
            return "medium"
        else:
            return "hard" 