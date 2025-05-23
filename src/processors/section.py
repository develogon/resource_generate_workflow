"""セクション処理器."""

import re
from typing import List, Dict, Any
import logging

from .base import BaseProcessor, ProcessorType, ProcessingRequest, ProcessingResult
from ..models import Section, Paragraph
from ..config import Config

logger = logging.getLogger(__name__)


class SectionProcessor(BaseProcessor):
    """セクションをパラグラフに分割する処理器."""
    
    def __init__(self, config: Config):
        """初期化."""
        super().__init__(config)
        
    def get_processor_type(self) -> ProcessorType:
        """処理器タイプを返す."""
        return ProcessorType.SECTION
        
    async def process(self, request: ProcessingRequest) -> ProcessingResult:
        """セクションを処理してパラグラフに分割.
        
        Args:
            request: 処理リクエスト
            
        Returns:
            処理結果（Paragraphのリスト）
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
            section = request.content
            if not isinstance(section, Section):
                return ProcessingResult(
                    content=request.content,
                    metadata={},
                    processor_type=self.get_processor_type(),
                    success=False,
                    error="Content must be a Section instance"
                )
            
            # パラグラフに分割
            paragraphs = await self._split_into_paragraphs(section, request.options)
            
            metadata = self.extract_metadata(request, paragraphs)
            metadata.update({
                "paragraph_count": len(paragraphs),
                "section_title": section.title,
                "split_method": request.options.get("split_method", "empty_line")
            })
            
            return ProcessingResult(
                content=paragraphs,
                metadata=metadata,
                processor_type=self.get_processor_type(),
                success=True
            )
            
        except Exception as e:
            logger.error(f"Section processing failed: {e}")
            return ProcessingResult(
                content=request.content,
                metadata={},
                processor_type=self.get_processor_type(),
                success=False,
                error=str(e)
            )
            
    async def _split_into_paragraphs(self, section: Section, options: Dict[str, Any]) -> List[Paragraph]:
        """セクションをパラグラフに分割."""
        split_method = options.get("split_method", "empty_line")
        
        if split_method == "empty_line":
            return self._split_by_empty_lines(section)
        elif split_method == "sentence":
            return self._split_by_sentences(section)
        elif split_method == "length":
            max_length = options.get("max_paragraph_length", 500)
            return self._split_by_length(section, max_length)
        else:
            # デフォルトは空行ベース
            return self._split_by_empty_lines(section)
            
    def _split_by_empty_lines(self, section: Section) -> List[Paragraph]:
        """空行ベースでパラグラフに分割."""
        paragraphs = []
        text = section.content
        
        # 空行で分割
        paragraph_texts = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        for idx, paragraph_text in enumerate(paragraph_texts):
            # 見出し行を除外するかチェック
            if self._is_heading(paragraph_text):
                continue
                
            paragraphs.append(Paragraph(
                content=paragraph_text,
                index=idx,
                section_index=section.index,
                chapter_index=section.chapter_index,
                metadata={
                    "section_title": section.title,
                    "word_count": len(paragraph_text.split()),
                    "char_count": len(paragraph_text)
                }
            ))
        
        return paragraphs
        
    def _split_by_sentences(self, section: Section) -> List[Paragraph]:
        """文ベースでパラグラフに分割."""
        paragraphs = []
        text = section.content
        
        # 文を分割（簡易版）
        sentences = self._split_sentences(text)
        
        current_paragraph = []
        max_sentences = 3  # 1パラグラフあたりの最大文数
        
        for sentence in sentences:
            current_paragraph.append(sentence)
            
            if len(current_paragraph) >= max_sentences or sentence.endswith(('。', '.', '!', '?')):
                paragraph_text = ' '.join(current_paragraph)
                
                paragraphs.append(Paragraph(
                    content=paragraph_text,
                    index=len(paragraphs),
                    section_index=section.index,
                    chapter_index=section.chapter_index,
                    metadata={
                        "section_title": section.title,
                        "sentence_count": len(current_paragraph),
                        "word_count": len(paragraph_text.split()),
                        "char_count": len(paragraph_text)
                    }
                ))
                
                current_paragraph = []
        
        # 残りの文があれば最後のパラグラフとして追加
        if current_paragraph:
            paragraph_text = ' '.join(current_paragraph)
            paragraphs.append(Paragraph(
                content=paragraph_text,
                index=len(paragraphs),
                section_index=section.index,
                chapter_index=section.chapter_index,
                metadata={
                    "section_title": section.title,
                    "sentence_count": len(current_paragraph),
                    "word_count": len(paragraph_text.split()),
                    "char_count": len(paragraph_text)
                }
            ))
        
        return paragraphs
        
    def _split_by_length(self, section: Section, max_length: int) -> List[Paragraph]:
        """長さベースでパラグラフに分割."""
        paragraphs = []
        text = section.content
        
        # 文で分割
        sentences = self._split_sentences(text)
        
        current_paragraph = []
        current_length = 0
        
        for sentence in sentences:
            sentence_length = len(sentence)
            
            if current_length + sentence_length > max_length and current_paragraph:
                # 現在のパラグラフを保存
                paragraph_text = ' '.join(current_paragraph)
                paragraphs.append(Paragraph(
                    content=paragraph_text,
                    index=len(paragraphs),
                    section_index=section.index,
                    chapter_index=section.chapter_index,
                    metadata={
                        "section_title": section.title,
                        "word_count": len(paragraph_text.split()),
                        "char_count": len(paragraph_text)
                    }
                ))
                
                # 新しいパラグラフ開始
                current_paragraph = [sentence]
                current_length = sentence_length
            else:
                current_paragraph.append(sentence)
                current_length += sentence_length
        
        # 最後のパラグラフを保存
        if current_paragraph:
            paragraph_text = ' '.join(current_paragraph)
            paragraphs.append(Paragraph(
                content=paragraph_text,
                index=len(paragraphs),
                section_index=section.index,
                chapter_index=section.chapter_index,
                metadata={
                    "section_title": section.title,
                    "word_count": len(paragraph_text.split()),
                    "char_count": len(paragraph_text)
                }
            ))
        
        return paragraphs
        
    def _is_heading(self, text: str) -> bool:
        """テキストが見出しかどうかを判定."""
        text = text.strip()
        
        # Markdown見出し
        if text.startswith('#'):
            return True
            
        # 短すぎる行は見出しの可能性が高い
        if len(text) < 50 and not text.endswith(('。', '.', '!', '?')):
            return True
            
        return False
        
    def _split_sentences(self, text: str) -> List[str]:
        """テキストを文に分割."""
        # 簡易的な文分割
        # より高度な分割には専用ライブラリ（spaCy、NLTK等）を使用
        
        # 句読点で分割
        sentences = re.split(r'[。．.!?！？\n]+', text)
        
        # 空文字列を除外し、前後の空白を削除
        sentences = [s.strip() for s in sentences if s.strip()]
        
        return sentences 