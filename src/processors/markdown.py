"""Markdownプロセッサー."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import frontmatter
import yaml

from .base import BaseProcessor, ProcessorType, ProcessingRequest, ProcessingResult
from ..models.content import Chapter, Content, Paragraph, Section
from ..utils.validation import validate_markdown_content
from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ParsedElement:
    """パースされた要素の基底クラス."""
    
    element_type: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    line_number: int = 0


@dataclass 
class ParsedHeading(ParsedElement):
    """パースされた見出し."""
    
    level: int = 1
    anchor: str = ""
    
    def __post_init__(self):
        self.element_type = "heading"
        if not self.anchor:
            # アンカーIDを自動生成
            clean_text = re.sub(r'[^\w\s-]', '', self.content.lower())
            self.anchor = re.sub(r'[-\s]+', '-', clean_text).strip('-')


@dataclass
class ParsedCodeBlock(ParsedElement):
    """パースされたコードブロック."""
    
    language: str = ""
    filename: str = ""
    
    def __post_init__(self):
        self.element_type = "code_block"


@dataclass
class ParsedImage(ParsedElement):
    """パースされた画像."""
    
    alt_text: str = ""
    url: str = ""
    title: str = ""
    
    def __post_init__(self):
        self.element_type = "image"


@dataclass
class ParsedLink(ParsedElement):
    """パースされたリンク."""
    
    text: str = ""
    url: str = ""
    title: str = ""
    
    def __post_init__(self):
        self.element_type = "link"


@dataclass
class ParsedTable(ParsedElement):
    """パースされたテーブル."""
    
    headers: List[str] = field(default_factory=list)
    rows: List[List[str]] = field(default_factory=list)
    
    def __post_init__(self):
        self.element_type = "table"


class MarkdownProcessor(BaseProcessor):
    """Markdownプロセッサー."""
    
    def __init__(self, config):
        """初期化."""
        super().__init__(config)
        self.reset()
    
    def get_processor_type(self) -> ProcessorType:
        """処理器タイプを返す."""
        return ProcessorType.MARKDOWN
    
    def reset(self):
        """パーサーの状態をリセット."""
        self.elements: List[ParsedElement] = []
        self.headings: List[ParsedHeading] = []
        self.code_blocks: List[ParsedCodeBlock] = []
        self.images: List[ParsedImage] = []
        self.links: List[ParsedLink] = []
        self.tables: List[ParsedTable] = []
        self.front_matter: Dict[str, Any] = {}
        self.content_without_frontmatter: str = ""
    
    async def process(self, request: ProcessingRequest) -> ProcessingResult:
        """Markdownコンテンツを処理."""
        try:
            if hasattr(request.content, 'content'):
                content_text = request.content.content
            else:
                content_text = str(request.content)
                
            parsed_data = self.parse(content_text)
            
            # 処理オプションに応じた変換
            if request.options.get("output_format") == "content_models":
                result_content = self.to_content_models(parsed_data)
            else:
                result_content = parsed_data
                
            metadata = self.extract_processing_metadata(request, parsed_data)
            
            return ProcessingResult(
                content=result_content,
                metadata=metadata,
                processor_type=self.get_processor_type(),
                success=True
            )
            
        except Exception as e:
            logger.error(f"Markdown processing failed: {e}")
            return ProcessingResult(
                content=request.content,
                metadata={},
                processor_type=self.get_processor_type(),
                success=False,
                error=str(e)
            )
    
    def parse_file(self, file_path: Path) -> Dict[str, Any]:
        """ファイルからMarkdownをパース."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return self.parse(content)
    
    def parse(self, content: str) -> Dict[str, Any]:
        """Markdownコンテンツをパース."""
        self.reset()
        
        # バリデーション
        validation_result = validate_markdown_content(content)
        
        # front matterの処理
        try:
            post = frontmatter.loads(content)
            self.front_matter = post.metadata
            self.content_without_frontmatter = post.content
        except yaml.YAMLError:
            # front matterが無い場合
            self.front_matter = {}
            self.content_without_frontmatter = content
        
        # 行ごとに解析
        lines = self.content_without_frontmatter.split('\n')
        self._parse_lines(lines)
        
        return {
            "validation": validation_result,
            "front_matter": self.front_matter,
            "content": self.content_without_frontmatter,
            "elements": self.elements,
            "headings": self.headings,
            "code_blocks": self.code_blocks,
            "images": self.images,
            "links": self.links,
            "tables": self.tables,
            "structure": self._build_structure()
        }
    
    def _parse_lines(self, lines: List[str]) -> None:
        """行ごとの解析."""
        i = 0
        in_code_block = False
        current_code_block = None
        in_table = False
        current_table = None
        
        while i < len(lines):
            line = lines[i]
            line_number = i + 1
            
            # コードブロックの処理
            if line.strip().startswith('```'):
                if not in_code_block:
                    # コードブロック開始
                    in_code_block = True
                    language = line.strip()[3:].strip()
                    current_code_block = ParsedCodeBlock(
                        element_type="code_block",
                        content="",
                        language=language,
                        line_number=line_number
                    )
                else:
                    # コードブロック終了
                    in_code_block = False
                    if current_code_block:
                        self.code_blocks.append(current_code_block)
                        self.elements.append(current_code_block)
                    current_code_block = None
                i += 1
                continue
            
            if in_code_block and current_code_block:
                current_code_block.content += line + "\n"
                i += 1
                continue
            
            # 見出しの処理
            if line.strip().startswith('#'):
                heading = self._parse_heading(line, line_number)
                if heading:
                    self.headings.append(heading)
                    self.elements.append(heading)
            
            # テーブルの処理
            elif '|' in line and line.strip().startswith('|'):
                if not in_table:
                    # テーブル開始
                    in_table = True
                    current_table = ParsedTable(
                        element_type="table",
                        content="",
                        line_number=line_number
                    )
                    # ヘッダー行として処理
                    current_table.headers = self._parse_table_row(line)
                else:
                    # テーブル継続
                    if not line.strip().startswith('|---') and not line.strip().startswith('|-'):
                        # セパレーター行ではない場合
                        row = self._parse_table_row(line)
                        current_table.rows.append(row)
                        
                current_table.content += line + "\n"
                
            else:
                # テーブル終了チェック
                if in_table and current_table:
                    self.tables.append(current_table)
                    self.elements.append(current_table)
                    in_table = False
                    current_table = None
                
                # 画像とリンクの解析
                self._parse_images_and_links(line, line_number)
                
            i += 1
        
        # 最後のテーブルが終了していない場合
        if in_table and current_table:
            self.tables.append(current_table)
            self.elements.append(current_table)
    
    def _parse_heading(self, line: str, line_number: int) -> Optional[ParsedHeading]:
        """見出しをパース."""
        match = re.match(r'^(#{1,6})\s+(.+)$', line.strip())
        if match:
            level = len(match.group(1))
            content = match.group(2).strip()
            
            return ParsedHeading(
                element_type="heading",
                content=content,
                level=level,
                line_number=line_number
            )
        return None
    
    def _parse_table_row(self, line: str) -> List[str]:
        """テーブルの行をパース."""
        # パイプ文字で分割し、前後の空白を除去
        cells = [cell.strip() for cell in line.split('|')[1:-1]]
        return cells
    
    def _parse_images_and_links(self, line: str, line_number: int) -> None:
        """画像とリンクをパース."""
        # 画像パターン: ![alt](url "title")
        image_pattern = r'!\[([^\]]*)\]\(([^)]+)(?:\s+"([^"]*)")?\)'
        for match in re.finditer(image_pattern, line):
            alt_text = match.group(1)
            url = match.group(2)
            title = match.group(3) or ""
            
            image = ParsedImage(
                element_type="image",
                content=match.group(0),
                alt_text=alt_text,
                url=url,
                title=title,
                line_number=line_number
            )
            self.images.append(image)
            self.elements.append(image)
        
        # リンクパターン: [text](url "title")
        link_pattern = r'\[([^\]]+)\]\(([^)]+)(?:\s+"([^"]*)")?\)'
        for match in re.finditer(link_pattern, line):
            # 画像リンクでない場合のみ
            if not line[max(0, match.start() - 1):match.start()] == '!':
                text = match.group(1)
                url = match.group(2)
                title = match.group(3) or ""
                
                link = ParsedLink(
                    element_type="link",
                    content=match.group(0),
                    text=text,
                    url=url,
                    title=title,
                    line_number=line_number
                )
                self.links.append(link)
                self.elements.append(link)
    
    def _build_structure(self) -> Dict[str, Any]:
        """構造化されたドキュメント情報を構築."""
        structure = {
            "document": {
                "title": self.front_matter.get("title", ""),
                "has_front_matter": bool(self.front_matter),
                "total_lines": len(self.content_without_frontmatter.split('\n')),
                "total_characters": len(self.content_without_frontmatter)
            },
            "hierarchy": self._build_hierarchy(),
            "statistics": {
                "heading_count": len(self.headings),
                "code_block_count": len(self.code_blocks),
                "image_count": len(self.images),
                "link_count": len(self.links),
                "table_count": len(self.tables),
                "max_heading_level": max([h.level for h in self.headings], default=0),
                "heading_distribution": self._get_heading_distribution()
            },
            "sections": self._identify_sections(),
            "outline": [
                {
                    "level": h.level,
                    "title": h.content,
                    "anchor": h.anchor,
                    "line": h.line_number
                }
                for h in self.headings
            ]
        }
        
        return structure
    
    def _build_hierarchy(self) -> List[Dict[str, Any]]:
        """見出しの階層構造を構築."""
        hierarchy = []
        stack = []
        
        for heading in self.headings:
            node = {
                "level": heading.level,
                "title": heading.content,
                "anchor": heading.anchor,
                "line": heading.line_number,
                "children": []
            }
            
            # スタックを調整
            while stack and stack[-1]["level"] >= heading.level:
                stack.pop()
            
            if stack:
                # 親の子として追加
                stack[-1]["children"].append(node)
            else:
                # ルートレベルとして追加
                hierarchy.append(node)
            
            stack.append(node)
        
        return hierarchy
    
    def _get_heading_distribution(self) -> Dict[int, int]:
        """見出しレベルの分布を取得."""
        distribution = {}
        for heading in self.headings:
            distribution[heading.level] = distribution.get(heading.level, 0) + 1
        return distribution
    
    def _identify_sections(self) -> List[Dict[str, Any]]:
        """セクションを識別."""
        sections = []
        current_section = None
        
        for heading in self.headings:
            if heading.level <= 2:  # H1またはH2をセクション境界とする
                if current_section:
                    sections.append(current_section)
                
                current_section = {
                    "title": heading.content,
                    "level": heading.level,
                    "anchor": heading.anchor,
                    "start_line": heading.line_number,
                    "subsections": []
                }
            elif current_section and heading.level == 3:
                # H3はサブセクション
                current_section["subsections"].append({
                    "title": heading.content,
                    "anchor": heading.anchor,
                    "line": heading.line_number
                })
        
        if current_section:
            sections.append(current_section)
        
        return sections
    
    def to_content_models(self, parsed_data: Dict[str, Any]) -> List[Content]:
        """パースデータをContentモデルに変換."""
        contents = []
        sections = parsed_data.get("sections", [])
        
        if not sections:
            # セクションがない場合は全体を1つのコンテンツとする
            contents.append(Content(
                id=str(uuid.uuid4()),
                title=parsed_data["document"]["title"] or "Untitled",
                content=parsed_data["content"],
                metadata={
                    "front_matter": parsed_data["front_matter"],
                    "statistics": parsed_data["statistics"]
                }
            ))
        else:
            # セクションごとにContentを作成
            content_text = parsed_data["content"]
            lines = content_text.split('\n')
            
            for i, section in enumerate(sections):
                start_line = section["start_line"] - 1
                end_line = len(lines)
                
                if i + 1 < len(sections):
                    end_line = sections[i + 1]["start_line"] - 1
                
                section_content = '\n'.join(lines[start_line:end_line])
                
                contents.append(Content(
                    id=f"section-{i}",
                    title=section["title"],
                    content=section_content,
                    metadata={
                        "section_index": i,
                        "level": section["level"],
                        "anchor": section["anchor"],
                        "subsections": section["subsections"]
                    }
                ))
        
        return contents
    
    def extract_processing_metadata(self, request: ProcessingRequest, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """処理メタデータを抽出."""
        metadata = self.extract_metadata(request, parsed_data)
        metadata.update({
            "parsing_statistics": parsed_data["statistics"],
            "document_structure": parsed_data["document"],
            "validation_result": parsed_data["validation"]
        })
        return metadata 