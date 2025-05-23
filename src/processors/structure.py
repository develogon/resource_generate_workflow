"""構造解析処理器."""

import re
from typing import List, Dict, Any, Optional
import logging
from dataclasses import dataclass

from .base import BaseProcessor, ProcessorType, ProcessingRequest, ProcessingResult
from ..models import Content, Chapter, Section, Paragraph
from ..config import Config

logger = logging.getLogger(__name__)


@dataclass
class StructureElement:
    """構造要素."""
    type: str  # heading, paragraph, list, code, image, table
    level: int  # 見出しレベル（1-6）、その他は0
    content: str
    metadata: Dict[str, Any]


@dataclass
class DocumentStructure:
    """文書構造."""
    title: str
    elements: List[StructureElement]
    hierarchy: Dict[str, Any]
    metadata: Dict[str, Any]


class StructureProcessor(BaseProcessor):
    """文書構造を解析する処理器."""
    
    def __init__(self, config: Config):
        """初期化."""
        super().__init__(config)
        
    def get_processor_type(self) -> ProcessorType:
        """処理器タイプを返す."""
        return ProcessorType.STRUCTURE
        
    async def process(self, request: ProcessingRequest) -> ProcessingResult:
        """文書構造を解析.
        
        Args:
            request: 処理リクエスト
            
        Returns:
            処理結果（DocumentStructure）
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
            
            # 入力タイプに応じて処理
            if isinstance(content, str):
                text = content
                title = request.options.get("title", "Untitled")
            elif hasattr(content, 'content'):
                text = content.content
                title = getattr(content, 'title', "Untitled")
            else:
                return ProcessingResult(
                    content=request.content,
                    metadata={},
                    processor_type=self.get_processor_type(),
                    success=False,
                    error="Invalid content type"
                )
            
            # 構造解析
            structure = await self._analyze_structure(text, title, request.options)
            
            metadata = self.extract_metadata(request, structure)
            metadata.update({
                "element_count": len(structure.elements),
                "title": structure.title,
                "analysis_method": request.options.get("analysis_method", "markdown")
            })
            
            return ProcessingResult(
                content=structure,
                metadata=metadata,
                processor_type=self.get_processor_type(),
                success=True
            )
            
        except Exception as e:
            logger.error(f"Structure analysis failed: {e}")
            return ProcessingResult(
                content=request.content,
                metadata={},
                processor_type=self.get_processor_type(),
                success=False,
                error=str(e)
            )
            
    async def _analyze_structure(self, text: str, title: str, options: Dict[str, Any]) -> DocumentStructure:
        """文書構造を解析."""
        analysis_method = options.get("analysis_method", "markdown")
        
        if analysis_method == "markdown":
            return self._analyze_markdown_structure(text, title)
        elif analysis_method == "plain_text":
            return self._analyze_plain_text_structure(text, title)
        else:
            # デフォルトはMarkdown
            return self._analyze_markdown_structure(text, title)
            
    def _analyze_markdown_structure(self, text: str, title: str) -> DocumentStructure:
        """Markdown文書の構造を解析."""
        elements = []
        lines = text.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            if not line:
                i += 1
                continue
                
            # 見出し
            if line.startswith('#'):
                element = self._parse_heading(line)
                elements.append(element)
                
            # コードブロック
            elif line.startswith('```'):
                code_element, skip_lines = self._parse_code_block(lines, i)
                elements.append(code_element)
                i += skip_lines
                
            # リスト
            elif line.startswith(('-', '*', '+')):
                list_element, skip_lines = self._parse_list(lines, i)
                elements.append(list_element)
                i += skip_lines
                
            # 画像
            elif line.startswith('!['):
                element = self._parse_image(line)
                elements.append(element)
                
            # テーブル
            elif '|' in line:
                table_element, skip_lines = self._parse_table(lines, i)
                if table_element:
                    elements.append(table_element)
                    i += skip_lines
                else:
                    # 通常の段落として処理
                    element = self._parse_paragraph(line)
                    elements.append(element)
                    
            # 通常の段落
            else:
                paragraph_element, skip_lines = self._parse_paragraph_block(lines, i)
                elements.append(paragraph_element)
                i += skip_lines
                
            i += 1
        
        # 階層構造の構築
        hierarchy = self._build_hierarchy(elements)
        
        # メタデータの生成
        metadata = self._analyze_document_metadata(elements)
        
        return DocumentStructure(
            title=title,
            elements=elements,
            hierarchy=hierarchy,
            metadata=metadata
        )
        
    def _parse_heading(self, line: str) -> StructureElement:
        """見出しを解析."""
        match = re.match(r'^(#{1,6})\s+(.+)$', line)
        if match:
            level = len(match.group(1))
            content = match.group(2).strip()
        else:
            level = 1
            content = line.lstrip('#').strip()
            
        return StructureElement(
            type="heading",
            level=level,
            content=content,
            metadata={
                "original_line": line,
                "word_count": len(content.split())
            }
        )
        
    def _parse_code_block(self, lines: List[str], start: int) -> tuple[StructureElement, int]:
        """コードブロックを解析."""
        first_line = lines[start].strip()
        language = first_line[3:].strip() if len(first_line) > 3 else "text"
        
        code_lines = []
        i = start + 1
        
        while i < len(lines):
            if lines[i].strip().startswith('```'):
                break
            code_lines.append(lines[i])
            i += 1
            
        code_content = '\n'.join(code_lines)
        
        return StructureElement(
            type="code",
            level=0,
            content=code_content,
            metadata={
                "language": language,
                "line_count": len(code_lines),
                "char_count": len(code_content)
            }
        ), i - start
        
    def _parse_list(self, lines: List[str], start: int) -> tuple[StructureElement, int]:
        """リストを解析."""
        list_items = []
        i = start
        
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue
            if not line.startswith(('-', '*', '+')):
                break
                
            # リストアイテムの内容を抽出
            item_content = line[1:].strip()
            list_items.append(item_content)
            i += 1
            
        return StructureElement(
            type="list",
            level=0,
            content='\n'.join(list_items),
            metadata={
                "item_count": len(list_items),
                "list_type": "unordered"
            }
        ), i - start - 1
        
    def _parse_image(self, line: str) -> StructureElement:
        """画像を解析."""
        match = re.match(r'!\[([^\]]*)\]\(([^\)]+)\)', line)
        if match:
            alt_text = match.group(1)
            url = match.group(2)
        else:
            alt_text = ""
            url = ""
            
        return StructureElement(
            type="image",
            level=0,
            content=alt_text,
            metadata={
                "url": url,
                "alt_text": alt_text,
                "original_line": line
            }
        )
        
    def _parse_table(self, lines: List[str], start: int) -> tuple[Optional[StructureElement], int]:
        """テーブルを解析."""
        table_lines = []
        i = start
        
        # テーブルの行を収集
        while i < len(lines):
            line = lines[i].strip()
            if not line or '|' not in line:
                break
            table_lines.append(line)
            i += 1
            
        if len(table_lines) < 2:
            return None, 0
            
        # ヘッダーとデータを分離
        header = table_lines[0]
        separator = table_lines[1] if len(table_lines) > 1 else ""
        data_rows = table_lines[2:] if len(table_lines) > 2 else []
        
        # 区切り行の検証
        if not re.match(r'^[\|\-\s:]+$', separator):
            return None, 0
            
        columns = [col.strip() for col in header.split('|')[1:-1]]
        
        return StructureElement(
            type="table",
            level=0,
            content='\n'.join(table_lines),
            metadata={
                "columns": columns,
                "column_count": len(columns),
                "row_count": len(data_rows),
                "has_header": True
            }
        ), i - start - 1
        
    def _parse_paragraph(self, line: str) -> StructureElement:
        """単一行の段落を解析."""
        return StructureElement(
            type="paragraph",
            level=0,
            content=line,
            metadata={
                "word_count": len(line.split()),
                "char_count": len(line)
            }
        )
        
    def _parse_paragraph_block(self, lines: List[str], start: int) -> tuple[StructureElement, int]:
        """複数行の段落ブロックを解析."""
        paragraph_lines = []
        i = start
        
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                break
            # 特殊な行（見出し、リストなど）でない場合のみ追加
            if not self._is_special_line(line):
                paragraph_lines.append(line)
                i += 1
            else:
                break
                
        content = ' '.join(paragraph_lines)
        
        return StructureElement(
            type="paragraph",
            level=0,
            content=content,
            metadata={
                "word_count": len(content.split()),
                "char_count": len(content),
                "line_count": len(paragraph_lines)
            }
        ), i - start - 1
        
    def _is_special_line(self, line: str) -> bool:
        """特殊な行（見出し、リスト等）かどうかを判定."""
        return (
            line.startswith('#') or
            line.startswith(('-', '*', '+')) or
            line.startswith('```') or
            line.startswith('![') or
            '|' in line
        )
        
    def _build_hierarchy(self, elements: List[StructureElement]) -> Dict[str, Any]:
        """要素から階層構造を構築."""
        hierarchy = {"sections": []}
        current_section = None
        
        for element in elements:
            if element.type == "heading":
                if element.level <= 2:  # H1, H2はメインセクション
                    current_section = {
                        "title": element.content,
                        "level": element.level,
                        "subsections": [],
                        "content": []
                    }
                    hierarchy["sections"].append(current_section)
                elif current_section:  # H3以降はサブセクション
                    subsection = {
                        "title": element.content,
                        "level": element.level,
                        "content": []
                    }
                    current_section["subsections"].append(subsection)
            else:
                # 見出し以外の要素をコンテンツとして追加
                if current_section:
                    if current_section["subsections"]:
                        # 最新のサブセクションに追加
                        current_section["subsections"][-1]["content"].append(element)
                    else:
                        # メインセクションに追加
                        current_section["content"].append(element)
                        
        return hierarchy
        
    def _analyze_document_metadata(self, elements: List[StructureElement]) -> Dict[str, Any]:
        """文書のメタデータを分析."""
        # 要素タイプ別の統計
        type_counts = {}
        for element in elements:
            type_counts[element.type] = type_counts.get(element.type, 0) + 1
            
        # 見出しレベルの分布
        heading_levels = {}
        for element in elements:
            if element.type == "heading":
                level = element.level
                heading_levels[level] = heading_levels.get(level, 0) + 1
                
        # 総文字数・語数
        total_chars = sum(len(e.content) for e in elements)
        total_words = sum(len(e.content.split()) for e in elements)
        
        return {
            "total_elements": len(elements),
            "element_types": type_counts,
            "heading_levels": heading_levels,
            "total_characters": total_chars,
            "total_words": total_words,
            "has_code": "code" in type_counts,
            "has_images": "image" in type_counts,
            "has_tables": "table" in type_counts,
            "has_lists": "list" in type_counts
        }
        
    def _analyze_plain_text_structure(self, text: str, title: str) -> DocumentStructure:
        """プレーンテキストの構造を解析."""
        # 簡易的な解析（段落分割のみ）
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        elements = []
        for i, paragraph in enumerate(paragraphs):
            elements.append(StructureElement(
                type="paragraph",
                level=0,
                content=paragraph,
                metadata={
                    "index": i,
                    "word_count": len(paragraph.split()),
                    "char_count": len(paragraph)
                }
            ))
            
        hierarchy = {"sections": [{"title": title, "level": 1, "content": elements}]}
        
        metadata = {
            "total_elements": len(elements),
            "element_types": {"paragraph": len(elements)},
            "total_characters": sum(len(e.content) for e in elements),
            "total_words": sum(len(e.content.split()) for e in elements)
        }
        
        return DocumentStructure(
            title=title,
            elements=elements,
            hierarchy=hierarchy,
            metadata=metadata
        ) 