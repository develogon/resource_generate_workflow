"""チャプター処理器."""

import re
from typing import List, Dict, Any
import logging

from .base import BaseProcessor, ProcessorType, ProcessingRequest, ProcessingResult
from ..models import Chapter, Section
from ..config import Config

logger = logging.getLogger(__name__)


class ChapterProcessor(BaseProcessor):
    """チャプターをセクションに分割する処理器."""
    
    def __init__(self, config: Config):
        """初期化."""
        super().__init__(config)
        
    def get_processor_type(self) -> ProcessorType:
        """処理器タイプを返す."""
        return ProcessorType.CHAPTER
        
    async def process(self, request: ProcessingRequest) -> ProcessingResult:
        """チャプターを処理してセクションに分割.
        
        Args:
            request: 処理リクエスト
            
        Returns:
            処理結果（Sectionのリスト）
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
            chapter = request.content
            if not isinstance(chapter, Chapter):
                return ProcessingResult(
                    content=request.content,
                    metadata={},
                    processor_type=self.get_processor_type(),
                    success=False,
                    error="Content must be a Chapter instance"
                )
            
            # セクションに分割
            sections = await self._split_into_sections(chapter, request.options)
            
            metadata = self.extract_metadata(request, sections)
            metadata.update({
                "section_count": len(sections),
                "chapter_title": chapter.title,
                "split_method": request.options.get("split_method", "heading")
            })
            
            return ProcessingResult(
                content=sections,
                metadata=metadata,
                processor_type=self.get_processor_type(),
                success=True
            )
            
        except Exception as e:
            logger.error(f"Chapter processing failed: {e}")
            return ProcessingResult(
                content=request.content,
                metadata={},
                processor_type=self.get_processor_type(),
                success=False,
                error=str(e)
            )
            
    async def _split_into_sections(self, chapter: Chapter, options: Dict[str, Any]) -> List[Section]:
        """チャプターをセクションに分割."""
        split_method = options.get("split_method", "heading")
        
        if split_method == "heading":
            return self._split_by_headings(chapter)
        elif split_method == "length":
            max_length = options.get("max_section_length", 2000)
            return self._split_by_length(chapter, max_length)
        elif split_method == "paragraph":
            return self._split_by_paragraphs(chapter)
        else:
            # デフォルトは見出しベース
            return self._split_by_headings(chapter)
            
    def _split_by_headings(self, chapter: Chapter) -> List[Section]:
        """見出しベースでセクションに分割."""
        sections = []
        text = chapter.content
        
        # H3以降の見出しで分割
        section_pattern = r'^(#{3,})\s+(.+)$'
        lines = text.split('\n')
        
        current_section = None
        current_content = []
        section_index = 0
        
        for line in lines:
            match = re.match(section_pattern, line, re.MULTILINE)
            if match:
                # 前のセクションを保存
                if current_section:
                    sections.append(Section(
                        title=current_section,
                        content='\n'.join(current_content),
                        index=section_index,
                        chapter_index=chapter.index,
                        metadata={
                            "chapter_title": chapter.title,
                            "heading_level": len(match.group(1))
                        }
                    ))
                    section_index += 1
                
                # 新しいセクション開始
                current_section = match.group(2).strip()
                current_content = [line]
            else:
                current_content.append(line)
        
        # 最後のセクションを保存
        if current_section and current_content:
            sections.append(Section(
                title=current_section,
                content='\n'.join(current_content),
                index=section_index,
                chapter_index=chapter.index,
                metadata={"chapter_title": chapter.title}
            ))
        
        # セクションが見つからない場合は全体を1つのセクションとする
        if not sections:
            sections.append(Section(
                title=f"{chapter.title} - Section 1",
                content=chapter.content,
                index=0,
                chapter_index=chapter.index,
                metadata={"chapter_title": chapter.title}
            ))
        
        return sections
        
    def _split_by_length(self, chapter: Chapter, max_length: int) -> List[Section]:
        """長さベースでセクションに分割."""
        sections = []
        text = chapter.content
        
        # 段落で分割
        paragraphs = text.split('\n\n')
        
        current_content = []
        current_length = 0
        section_index = 0
        
        for paragraph in paragraphs:
            paragraph_length = len(paragraph)
            
            if current_length + paragraph_length > max_length and current_content:
                # 現在のセクションを保存
                sections.append(Section(
                    title=f"{chapter.title} - Section {section_index + 1}",
                    content='\n\n'.join(current_content),
                    index=section_index,
                    chapter_index=chapter.index,
                    metadata={"chapter_title": chapter.title}
                ))
                
                # 新しいセクション開始
                current_content = [paragraph]
                current_length = paragraph_length
                section_index += 1
            else:
                current_content.append(paragraph)
                current_length += paragraph_length
        
        # 最後のセクションを保存
        if current_content:
            sections.append(Section(
                title=f"{chapter.title} - Section {section_index + 1}",
                content='\n\n'.join(current_content),
                index=section_index,
                chapter_index=chapter.index,
                metadata={"chapter_title": chapter.title}
            ))
        
        return sections
        
    def _split_by_paragraphs(self, chapter: Chapter) -> List[Section]:
        """段落ベースでセクションに分割."""
        sections = []
        text = chapter.content
        
        # 空行で段落を分割
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        for idx, paragraph in enumerate(paragraphs):
            # 各段落を1つのセクションとする
            title = self._extract_paragraph_title(paragraph) or f"{chapter.title} - Paragraph {idx + 1}"
            
            sections.append(Section(
                title=title,
                content=paragraph,
                index=idx,
                chapter_index=chapter.index,
                metadata={
                    "chapter_title": chapter.title,
                    "paragraph_index": idx
                }
            ))
        
        return sections
        
    def _extract_paragraph_title(self, paragraph: str) -> str:
        """段落から適切なタイトルを抽出."""
        lines = paragraph.split('\n')
        first_line = lines[0].strip()
        
        # 見出し形式をチェック
        if first_line.startswith('#'):
            return re.sub(r'^#+\s*', '', first_line)
        
        # 最初の文の一部をタイトルとして使用
        words = first_line.split()
        if len(words) > 10:
            return ' '.join(words[:10]) + '...'
        else:
            return first_line 