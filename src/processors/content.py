"""コンテンツ処理器."""

import re
from typing import List, Dict, Any
import logging

from .base import BaseProcessor, ProcessorType, ProcessingRequest, ProcessingResult
from ..models import Content, Chapter
from ..config import Config

logger = logging.getLogger(__name__)


class ContentProcessor(BaseProcessor):
    """メインコンテンツを処理する処理器."""
    
    def __init__(self, config: Config):
        """初期化."""
        super().__init__(config)
        
    def get_processor_type(self) -> ProcessorType:
        """処理器タイプを返す."""
        return ProcessorType.CONTENT
        
    async def process(self, request: ProcessingRequest) -> ProcessingResult:
        """コンテンツを処理してチャプターに分割.
        
        Args:
            request: 処理リクエスト
            
        Returns:
            処理結果（Chapterのリスト）
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
            content = request.content
            if isinstance(content, str):
                # 文字列の場合はContentオブジェクトを作成
                content = Content(
                    id="auto-generated-content",
                    title=request.options.get("title", "Untitled"),
                    content=content,
                    metadata=request.context
                )
            
            # チャプターに分割
            chapters = await self._split_into_chapters(content, request.options)
            
            metadata = self.extract_metadata(request, chapters)
            metadata.update({
                "chapter_count": len(chapters),
                "total_length": len(content.content),
                "split_method": request.options.get("split_method", "heading")
            })
            
            return ProcessingResult(
                content=chapters,
                metadata=metadata,
                processor_type=self.get_processor_type(),
                success=True
            )
            
        except Exception as e:
            logger.error(f"Content processing failed: {e}")
            return ProcessingResult(
                content=request.content,
                metadata={},
                processor_type=self.get_processor_type(),
                success=False,
                error=str(e)
            )
            
    async def _split_into_chapters(self, content: Content, options: Dict[str, Any]) -> List[Chapter]:
        """コンテンツをチャプターに分割."""
        split_method = options.get("split_method", "heading")
        
        if split_method == "heading":
            return self._split_by_headings(content)
        elif split_method == "length":
            max_length = options.get("max_chapter_length", 5000)
            return self._split_by_length(content, max_length)
        else:
            # デフォルトは見出しベース
            return self._split_by_headings(content)
            
    def _split_by_headings(self, content: Content) -> List[Chapter]:
        """見出しベースでチャプターに分割."""
        chapters = []
        text = content.content
        
        # H1またはH2見出しで分割
        chapter_pattern = r'^(#{1,2})\s+(.+)$'
        lines = text.split('\n')
        
        current_chapter = None
        current_content = []
        
        for line in lines:
            match = re.match(chapter_pattern, line, re.MULTILINE)
            if match:
                # 前のチャプターを保存
                if current_chapter:
                    chapters.append(Chapter(
                        id=f"chapter-{len(chapters)}",
                        title=current_chapter,
                        content='\n'.join(current_content),
                        index=len(chapters),
                        metadata={"source_title": content.title}
                    ))
                
                # 新しいチャプター開始
                current_chapter = match.group(2).strip()
                current_content = [line]
            else:
                if current_content:
                    current_content.append(line)
        
        # 最後のチャプターを保存
        if current_chapter and current_content:
            chapters.append(Chapter(
                id=f"chapter-{len(chapters)}",
                title=current_chapter,
                content='\n'.join(current_content),
                index=len(chapters),
                metadata={"source_title": content.title}
            ))
        
        # チャプターが見つからない場合は全体を1つのチャプターとする
        if not chapters:
            chapters.append(Chapter(
                id="chapter-0",
                title=content.title,
                content=content.content,
                index=0,
                metadata={"source_title": content.title}
            ))
        
        return chapters
        
    def _split_by_length(self, content: Content, max_length: int) -> List[Chapter]:
        """長さベースでチャプターに分割."""
        chapters = []
        text = content.content
        
        # 段落で分割
        paragraphs = text.split('\n\n')
        
        current_content = []
        current_length = 0
        chapter_index = 0
        
        for paragraph in paragraphs:
            paragraph_length = len(paragraph)
            
            if current_length + paragraph_length > max_length and current_content:
                # 現在のチャプターを保存
                chapters.append(Chapter(
                    id=f"chapter-{chapter_index}",
                    title=f"{content.title} - Part {chapter_index + 1}",
                    content='\n\n'.join(current_content),
                    index=chapter_index,
                    metadata={"source_title": content.title}
                ))
                
                # 新しいチャプター開始
                current_content = [paragraph]
                current_length = paragraph_length
                chapter_index += 1
            else:
                current_content.append(paragraph)
                current_length += paragraph_length
        
        # 最後のチャプターを保存
        if current_content:
            chapters.append(Chapter(
                id=f"chapter-{chapter_index}",
                title=f"{content.title} - Part {chapter_index + 1}",
                content='\n\n'.join(current_content),
                index=chapter_index,
                metadata={"source_title": content.title}
            ))
        
        return chapters 