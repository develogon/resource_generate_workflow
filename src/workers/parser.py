"""パーサーワーカー - コンテンツ解析と分割を担当."""

import asyncio
import logging
from typing import Set, List, Dict, Any
from pathlib import Path

from .base import BaseWorker
from ..core.events import Event, EventType

logger = logging.getLogger(__name__)


class ParserWorker(BaseWorker):
    """コンテンツ解析ワーカー."""
    
    def get_subscriptions(self) -> Set[EventType]:
        """購読するイベントタイプを返す."""
        return {
            EventType.WORKFLOW_STARTED,
            EventType.CHAPTER_PARSED,
            EventType.SECTION_PARSED,
            EventType.STRUCTURE_ANALYZED
        }
        
    async def process(self, event: Event) -> None:
        """イベントを処理."""
        if event.type == EventType.WORKFLOW_STARTED:
            await self._parse_document(event)
        elif event.type == EventType.CHAPTER_PARSED:
            await self._parse_sections(event)
        elif event.type == EventType.SECTION_PARSED:
            await self._request_structure_analysis(event)
        elif event.type == EventType.STRUCTURE_ANALYZED:
            await self._parse_paragraphs(event)
            
    async def _parse_document(self, event: Event):
        """ドキュメントをチャプターに分割."""
        logger.info(f"Starting document parsing for workflow {event.workflow_id}")
        
        # 入力ファイルの取得
        input_file = event.data.get("input_file")
        if not input_file:
            logger.warning("No input file specified, using default content")
            content = self._get_default_content(event.data)
        else:
            content = await self._read_file(input_file)
        
        # チャプターに分割
        chapters = self._split_by_chapters(content)
        
        # 各チャプターでイベントを発行
        for idx, chapter in enumerate(chapters):
            chapter_data = {
                "index": idx,
                "title": chapter["title"],
                "content": chapter["content"],
                "path": self._get_chapter_path(event.data, idx, chapter["title"])
            }
            
            await self.event_bus.publish(Event(
                type=EventType.CHAPTER_PARSED,
                workflow_id=event.workflow_id,
                data=chapter_data,
                priority=idx  # 順序を保持
            ))
            
        logger.info(f"Document parsed into {len(chapters)} chapters")
        
    async def _parse_sections(self, event: Event):
        """チャプターをセクションに分割."""
        chapter_content = event.data.get("content", "")
        chapter_index = event.data.get("index", 0)
        
        logger.info(f"Parsing chapter {chapter_index} into sections")
        
        # セクションに分割
        sections = self._split_by_sections(chapter_content)
        
        # 各セクションでイベントを発行
        for idx, section in enumerate(sections):
            section_data = {
                "chapter_index": chapter_index,
                "section_index": idx,
                "title": section["title"],
                "content": section["content"],
                "level": section["level"]
            }
            
            await self.event_bus.publish(Event(
                type=EventType.SECTION_PARSED,
                workflow_id=event.workflow_id,
                data=section_data
            ))
            
        logger.debug(f"Chapter {chapter_index} parsed into {len(sections)} sections")
        
    async def _request_structure_analysis(self, event: Event):
        """構造解析をリクエスト."""
        # AIワーカーに構造解析を依頼（データをそのまま渡す）
        logger.debug(f"Requesting structure analysis for section: {event.data.get('title', 'Unknown')}")
        # 注意: ここでSTRUCTURE_ANALYZEDイベントを直接発行するのではなく、
        # AIワーカーがセクション解析を完了した後に発行するべき
        # 現在はそのままセクションイベントをAIワーカーに処理させる
        
    async def _parse_paragraphs(self, event: Event):
        """セクションをパラグラフに分割."""
        section_content = event.data.get("content", "")
        chapter_index = event.data.get("chapter_index", 0)
        section_index = event.data.get("section_index", 0)
        
        logger.debug(f"Parsing section {chapter_index}-{section_index} into paragraphs")
        
        # パラグラフに分割
        paragraphs = self._split_by_paragraphs(section_content)
        
        # 各パラグラフでイベントを発行
        for idx, paragraph in enumerate(paragraphs):
            paragraph_data = {
                "chapter_index": chapter_index,
                "section_index": section_index,
                "paragraph_index": idx,
                "content": paragraph,
                "title": event.data.get("title", f"Paragraph {idx+1}")
            }
            
            await self.event_bus.publish(Event(
                type=EventType.PARAGRAPH_PARSED,
                workflow_id=event.workflow_id,
                data=paragraph_data
            ))
            
        logger.debug(f"Section {chapter_index}-{section_index} parsed into {len(paragraphs)} paragraphs")
        
    async def _read_file(self, file_path: str) -> str:
        """ファイルを読み込み."""
        try:
            path = Path(file_path)
            if not path.exists():
                raise FileNotFoundError(f"Input file not found: {file_path}")
                
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            return self._get_default_content({"title": "Error"})
            
    def _get_default_content(self, data: Dict[str, Any]) -> str:
        """デフォルトコンテンツを取得."""
        title = data.get("title", "Sample Content")
        return f"""# {title}

## はじめに

これはサンプルコンテンツです。実際のMarkdownファイルを指定してください。

## 本文

### セクション 1

ここに本文の内容が入ります。

### セクション 2

追加の内容があります。

## まとめ

以上が{title}の内容です。
"""
        
    def _split_by_chapters(self, content: str) -> List[Dict[str, Any]]:
        """コンテンツをチャプターに分割."""
        chapters = []
        lines = content.split('\n')
        current_chapter = None
        current_content = []
        
        for line in lines:
            # H1見出し（チャプター）をチェック
            if line.startswith('# '):
                # 前のチャプターを保存
                if current_chapter:
                    chapters.append({
                        "title": current_chapter,
                        "content": '\n'.join(current_content).strip()
                    })
                
                # 新しいチャプター開始
                current_chapter = line[2:].strip()
                current_content = []
            else:
                current_content.append(line)
        
        # 最後のチャプターを保存
        if current_chapter:
            chapters.append({
                "title": current_chapter,
                "content": '\n'.join(current_content).strip()
            })
        
        # チャプターがない場合は全体を1つのチャプターとする
        if not chapters:
            chapters.append({
                "title": "Main Content",
                "content": content.strip()
            })
            
        return chapters
        
    def _split_by_sections(self, content: str) -> List[Dict[str, Any]]:
        """コンテンツをセクションに分割."""
        sections = []
        lines = content.split('\n')
        current_section = None
        current_content = []
        current_level = 2  # H2レベルから開始
        
        for line in lines:
            # 見出しレベルを判定
            if line.startswith('## '):
                level = 2
                title = line[3:].strip()
            elif line.startswith('### '):
                level = 3
                title = line[4:].strip()
            elif line.startswith('#### '):
                level = 4
                title = line[5:].strip()
            else:
                current_content.append(line)
                continue
            
            # 前のセクションを保存
            if current_section:
                sections.append({
                    "title": current_section,
                    "content": '\n'.join(current_content).strip(),
                    "level": current_level
                })
            
            # 新しいセクション開始
            current_section = title
            current_level = level
            current_content = []
        
        # 最後のセクションを保存
        if current_section:
            sections.append({
                "title": current_section,
                "content": '\n'.join(current_content).strip(),
                "level": current_level
            })
        
        # セクションがない場合は全体を1つのセクションとする
        if not sections:
            sections.append({
                "title": "Main Section",
                "content": content.strip(),
                "level": 2
            })
            
        return sections
        
    def _split_by_paragraphs(self, content: str) -> List[str]:
        """コンテンツをパラグラフに分割."""
        # 空行で分割してパラグラフを作成
        paragraphs = []
        current_paragraph = []
        
        for line in content.split('\n'):
            line = line.strip()
            
            if not line:  # 空行
                if current_paragraph:
                    paragraph_text = '\n'.join(current_paragraph).strip()
                    if paragraph_text:
                        paragraphs.append(paragraph_text)
                    current_paragraph = []
            else:
                current_paragraph.append(line)
        
        # 最後のパラグラフを追加
        if current_paragraph:
            paragraph_text = '\n'.join(current_paragraph).strip()
            if paragraph_text:
                paragraphs.append(paragraph_text)
        
        # パラグラフがない場合は全体を1つのパラグラフとする
        if not paragraphs:
            content_stripped = content.strip()
            if content_stripped:
                paragraphs.append(content_stripped)
            
        return paragraphs
        
    def _get_chapter_path(self, data: Dict[str, Any], index: int, title: str) -> str:
        """チャプターファイルパスを生成."""
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_title = safe_title.replace(' ', '_')
        return f"chapter_{index:02d}_{safe_title}.md" 