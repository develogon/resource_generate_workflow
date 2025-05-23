"""Markdownパーサー."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import frontmatter
import yaml

from ..models.content import Chapter, Content, Paragraph, Section
from ..utils.validation import validate_markdown_content


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


class MarkdownParser:
    """Markdownパーサー."""
    
    def __init__(self):
        """初期化."""
        self.reset()
    
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
                    # ヘッダー行の処理
                    headers = self._parse_table_row(line)
                    current_table.headers = headers
                    current_table.content += line + "\n"
                else:
                    # テーブル行の追加
                    if line.strip().replace('|', '').replace('-', '').replace(' ', ''):
                        # 区切り線でない場合
                        if not line.strip().replace('|', '').replace('-', '').replace(' ', '').replace(':', ''):
                            # 区切り線の場合はスキップ
                            pass
                        else:
                            row = self._parse_table_row(line)
                            current_table.rows.append(row)
                    current_table.content += line + "\n"
            else:
                # テーブル終了チェック
                if in_table and current_table:
                    in_table = False
                    self.tables.append(current_table)
                    self.elements.append(current_table)
                    current_table = None
                
                # 画像とリンクの処理
                self._parse_images_and_links(line, line_number)
            
            i += 1
        
        # 最後のテーブルの処理
        if in_table and current_table:
            self.tables.append(current_table)
            self.elements.append(current_table)
    
    def _parse_heading(self, line: str, line_number: int) -> Optional[ParsedHeading]:
        """見出しの解析."""
        match = re.match(r'^(#{1,6})\s*(.*)', line.strip())
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
        """テーブル行の解析."""
        # 前後の|を除去して分割
        cells = line.strip().split('|')
        if cells and not cells[0]:
            cells = cells[1:]  # 最初の空文字を除去
        if cells and not cells[-1]:
            cells = cells[:-1]  # 最後の空文字を除去
        
        return [cell.strip() for cell in cells]
    
    def _parse_images_and_links(self, line: str, line_number: int) -> None:
        """画像とリンクの解析."""
        # 画像の処理: ![alt](url "title")
        image_pattern = r'!\[([^\]]*)\]\(([^)]+?)(?:\s+"([^"]*)")?\)'
        for match in re.finditer(image_pattern, line):
            alt_text = match.group(1)
            url = match.group(2).strip()
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
        
        # リンクの処理: [text](url "title")
        # 画像以外のリンクを検出
        link_pattern = r'(?<!!)\[([^\]]+)\]\(([^)]+?)(?:\s+"([^"]*)")?\)'
        for match in re.finditer(link_pattern, line):
            text = match.group(1)
            url = match.group(2).strip()
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
        """文書構造の構築."""
        structure = {
            "chapters": [],
            "sections": [],
            "hierarchy": []
        }
        
        current_chapter = None
        current_section = None
        current_paragraphs = []
        
        for heading in self.headings:
            if heading.level == 1:
                # 前のセクションを完了
                if current_section and current_paragraphs:
                    current_section["paragraphs"] = current_paragraphs.copy()
                    current_paragraphs.clear()
                
                # 前のチャプターを完了
                if current_chapter:
                    structure["chapters"].append(current_chapter)
                
                # 新しいチャプター開始
                current_chapter = {
                    "id": str(uuid.uuid4()),
                    "title": heading.content,
                    "anchor": heading.anchor,
                    "line_number": heading.line_number,
                    "sections": []
                }
                current_section = None
                
            elif heading.level == 2:
                # 前のセクションを完了
                if current_section and current_paragraphs:
                    current_section["paragraphs"] = current_paragraphs.copy()
                    current_paragraphs.clear()
                
                # 新しいセクション開始
                current_section = {
                    "id": str(uuid.uuid4()),
                    "title": heading.content,
                    "anchor": heading.anchor,
                    "line_number": heading.line_number,
                    "learning_objectives": [],
                    "paragraphs": []
                }
                
                if current_chapter:
                    current_chapter["sections"].append(current_section)
                else:
                    structure["sections"].append(current_section)
        
        # 最後のセクションとチャプターを完了
        if current_section and current_paragraphs:
            current_section["paragraphs"] = current_paragraphs
        
        if current_chapter:
            structure["chapters"].append(current_chapter)
        
        # 階層構造の構築
        structure["hierarchy"] = self._build_hierarchy()
        
        return structure
    
    def _build_hierarchy(self) -> List[Dict[str, Any]]:
        """見出しの階層構造を構築."""
        hierarchy = []
        stack: List[Dict[str, Any]] = []
        
        for heading in self.headings:
            node = {
                "level": heading.level,
                "title": heading.content,
                "anchor": heading.anchor,
                "line_number": heading.line_number,
                "children": []
            }
            
            # 適切な位置を見つける
            while stack and stack[-1]["level"] >= heading.level:
                stack.pop()
            
            if stack:
                stack[-1]["children"].append(node)
            else:
                hierarchy.append(node)
            
            stack.append(node)
        
        return hierarchy
    
    def to_content_models(self, parsed_data: Dict[str, Any]) -> List[Content]:
        """パース結果をContentモデルに変換."""
        content_models = []
        
        structure = parsed_data["structure"]
        
        # チャプターの変換
        for chapter_data in structure["chapters"]:
            sections = []
            
            for section_data in chapter_data["sections"]:
                paragraphs = []
                
                # セクションの段落を作成（仮実装）
                for i, para_data in enumerate(section_data.get("paragraphs", [])):
                    paragraph = Paragraph(
                        title=f"段落{i+1}",
                        content=str(para_data),
                        type="text",
                        order=i+1,
                        metadata={"line_number": para_data.get("line_number", 0)}
                    )
                    paragraphs.append(paragraph)
                
                section = Section(
                    id=str(uuid.uuid4()),
                    title=section_data["title"],
                    content="",  # セクションの概要
                    learning_objectives=section_data.get("learning_objectives", []),
                    paragraphs=paragraphs,
                    metadata={
                        "anchor": section_data["anchor"],
                        "line_number": section_data["line_number"]
                    }
                )
                sections.append(section)
            
            chapter = Chapter(
                id=str(uuid.uuid4()),
                title=chapter_data["title"],
                content="",  # チャプターの概要
                sections=sections,
                metadata={
                    "anchor": chapter_data["anchor"],
                    "line_number": chapter_data["line_number"]
                }
            )
            content_models.append(chapter)
        
        return content_models
    
    def extract_metadata(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """メタデータの抽出."""
        metadata = {}
        
        # front matterからメタデータを取得
        metadata.update(parsed_data["front_matter"])
        
        # 統計情報を追加
        validation_stats = parsed_data["validation"]["stats"]
        metadata.update({
            "word_count": validation_stats["word_count"],
            "character_count": validation_stats["character_count"],
            "heading_count": validation_stats["heading_count"],
            "code_block_count": validation_stats["code_block_count"],
            "image_count": validation_stats["image_count"],
            "link_count": validation_stats["link_count"],
            "table_count": len(parsed_data["tables"])
        })
        
        # 構造情報を追加
        structure = parsed_data["structure"]
        metadata.update({
            "chapter_count": len(structure["chapters"]),
            "section_count": sum(len(ch["sections"]) for ch in structure["chapters"]),
            "max_heading_level": max((h.level for h in self.headings), default=0)
        })
        
        return metadata 