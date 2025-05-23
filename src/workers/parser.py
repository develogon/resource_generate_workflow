"""パーサーワーカー."""

import logging
from typing import Set, Dict, Any

from .base import BaseWorker, Event, EventType
from ..config import Config

logger = logging.getLogger(__name__)


class ParserWorker(BaseWorker):
    """パーサーワーカー."""
    
    def __init__(self, config: Config, worker_id: str = "parser_worker"):
        """初期化."""
        super().__init__(config, worker_id)
        
    def get_subscriptions(self) -> Set[str]:
        """購読するイベントタイプを返す."""
        return {
            EventType.WORKFLOW_STARTED,
            EventType.CHAPTER_PARSED,
            EventType.SECTION_PARSED
        }
        
    async def process(self, event: Event) -> None:
        """イベントを処理."""
        try:
            if event.type == EventType.WORKFLOW_STARTED:
                await self._handle_workflow_started(event)
            elif event.type == EventType.CHAPTER_PARSED:
                await self._handle_chapter_parsed(event)
            elif event.type == EventType.SECTION_PARSED:
                await self._handle_section_parsed(event)
            else:
                logger.warning(f"Unhandled event type: {event.type}")
                
        except Exception as e:
            logger.error(f"Parser worker error: {e}")
            raise
            
    async def _handle_workflow_started(self, event: Event) -> None:
        """ワークフロー開始イベントの処理."""
        logger.info(f"Starting content parsing for workflow {event.workflow_id}")
        
        # イベントデータから必要な情報を取得
        content_data = event.data.get('content')
        if not content_data:
            raise ValueError("No content data provided")
            
        # コンテンツの構造解析
        structure = await self._analyze_content_structure(content_data)
        
        # 構造解析完了イベントを発行
        if self.event_bus:
            structure_event = Event(
                event_type=EventType.STRUCTURE_ANALYZED,
                workflow_id=event.workflow_id,
                data={
                    'structure': structure,
                    'original_content': content_data
                },
                trace_id=event.trace_id
            )
            await self.event_bus.publish(structure_event)
            
        # チャプター解析の開始
        for chapter_data in structure.get('chapters', []):
            chapter_event = Event(
                event_type=EventType.CHAPTER_PARSED,
                workflow_id=event.workflow_id,
                data={
                    'chapter': chapter_data,
                    'structure': structure
                },
                trace_id=event.trace_id
            )
            await self.event_bus.publish(chapter_event)
            
    async def _handle_chapter_parsed(self, event: Event) -> None:
        """チャプター解析イベントの処理."""
        chapter_data = event.data.get('chapter')
        if not chapter_data:
            raise ValueError("No chapter data provided")
            
        logger.info(f"Processing chapter: {chapter_data.get('title', 'Unknown')}")
        
        # チャプター内のセクションを解析
        sections = await self._parse_chapter_sections(chapter_data)
        
        # 各セクションに対してイベントを発行
        for section_data in sections:
            section_event = Event(
                event_type=EventType.SECTION_PARSED,
                workflow_id=event.workflow_id,
                data={
                    'section': section_data,
                    'chapter': chapter_data
                },
                trace_id=event.trace_id
            )
            await self.event_bus.publish(section_event)
            
    async def _handle_section_parsed(self, event: Event) -> None:
        """セクション解析イベントの処理."""
        section_data = event.data.get('section')
        if not section_data:
            raise ValueError("No section data provided")
            
        logger.info(f"Processing section: {section_data.get('title', 'Unknown')}")
        
        # セクション内のパラグラフを解析
        paragraphs = await self._parse_section_paragraphs(section_data)
        
        # 各パラグラフに対してイベントを発行
        for paragraph_data in paragraphs:
            paragraph_event = Event(
                event_type=EventType.PARAGRAPH_PARSED,
                workflow_id=event.workflow_id,
                data={
                    'paragraph': paragraph_data,
                    'section': section_data
                },
                trace_id=event.trace_id
            )
            await self.event_bus.publish(paragraph_event)
            
    async def _analyze_content_structure(self, content_data: Dict[str, Any]) -> Dict[str, Any]:
        """コンテンツの構造を解析."""
        content_text = content_data.get('text', '')
        
        # 簡易的な構造解析
        structure = {
            'type': 'document',
            'title': content_data.get('title', 'Untitled'),
            'chapters': [],
            'metadata': {
                'total_length': len(content_text),
                'estimated_chapters': 0,
                'estimated_sections': 0
            }
        }
        
        # チャプターの検出（見出しレベル1）
        chapters = self._extract_chapters(content_text)
        structure['chapters'] = chapters
        structure['metadata']['estimated_chapters'] = len(chapters)
        
        # セクション数の推定
        total_sections = sum(len(chapter.get('sections', [])) for chapter in chapters)
        structure['metadata']['estimated_sections'] = total_sections
        
        return structure
        
    def _extract_chapters(self, content: str) -> list[Dict[str, Any]]:
        """コンテンツからチャプターを抽出."""
        chapters = []
        lines = content.split('\n')
        current_chapter = None
        current_content = []
        
        for line in lines:
            line = line.strip()
            
            # レベル1見出し（チャプター）の検出
            if line.startswith('# ') and not line.startswith('## '):
                # 前のチャプターを保存
                if current_chapter:
                    current_chapter['content'] = '\n'.join(current_content)
                    current_chapter['sections'] = self._extract_sections('\n'.join(current_content))
                    chapters.append(current_chapter)
                
                # 新しいチャプターを開始
                current_chapter = {
                    'title': line[2:].strip(),
                    'level': 1,
                    'content': '',
                    'sections': []
                }
                current_content = []
            else:
                if current_chapter:
                    current_content.append(line)
                    
        # 最後のチャプターを保存
        if current_chapter:
            current_chapter['content'] = '\n'.join(current_content)
            current_chapter['sections'] = self._extract_sections('\n'.join(current_content))
            chapters.append(current_chapter)
            
        # チャプターが見つからない場合は、全体を1つのチャプターとして扱う
        if not chapters:
            chapters.append({
                'title': 'Main Content',
                'level': 1,
                'content': content,
                'sections': self._extract_sections(content)
            })
            
        return chapters
        
    def _extract_sections(self, content: str) -> list[Dict[str, Any]]:
        """コンテンツからセクションを抽出."""
        sections = []
        lines = content.split('\n')
        current_section = None
        current_content = []
        
        for line in lines:
            line = line.strip()
            
            # レベル2見出し（セクション）の検出
            if line.startswith('## ') and not line.startswith('### '):
                # 前のセクションを保存
                if current_section:
                    current_section['content'] = '\n'.join(current_content)
                    current_section['paragraphs'] = self._extract_paragraphs('\n'.join(current_content))
                    sections.append(current_section)
                
                # 新しいセクションを開始
                current_section = {
                    'title': line[3:].strip(),
                    'level': 2,
                    'content': '',
                    'paragraphs': []
                }
                current_content = []
            else:
                if current_section:
                    current_content.append(line)
                    
        # 最後のセクションを保存
        if current_section:
            current_section['content'] = '\n'.join(current_content)
            current_section['paragraphs'] = self._extract_paragraphs('\n'.join(current_content))
            sections.append(current_section)
            
        # セクションが見つからない場合は、全体を1つのセクションとして扱う
        if not sections:
            sections.append({
                'title': 'Main Section',
                'level': 2,
                'content': content,
                'paragraphs': self._extract_paragraphs(content)
            })
            
        return sections
        
    def _extract_paragraphs(self, content: str) -> list[Dict[str, Any]]:
        """コンテンツからパラグラフを抽出."""
        paragraphs = []
        
        # 空行で分割してパラグラフを作成
        raw_paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        
        for i, paragraph_text in enumerate(raw_paragraphs):
            if paragraph_text:
                paragraphs.append({
                    'index': i,
                    'content': paragraph_text,
                    'type': self._classify_paragraph_type(paragraph_text),
                    'word_count': len(paragraph_text.split())
                })
                
        return paragraphs
        
    def _classify_paragraph_type(self, text: str) -> str:
        """パラグラフのタイプを分類."""
        text = text.strip()
        
        if text.startswith('###'):
            return 'heading3'
        elif text.startswith('- ') or text.startswith('* '):
            return 'list'
        elif text.startswith('> '):
            return 'quote'
        elif '```' in text:
            return 'code'
        elif len(text.split()) < 10:
            return 'short'
        else:
            return 'paragraph'
            
    async def _parse_chapter_sections(self, chapter_data: Dict[str, Any]) -> list[Dict[str, Any]]:
        """チャプター内のセクションを解析."""
        # 既に解析済みのセクションデータを返す
        return chapter_data.get('sections', [])
        
    async def _parse_section_paragraphs(self, section_data: Dict[str, Any]) -> list[Dict[str, Any]]:
        """セクション内のパラグラフを解析."""
        # 既に解析済みのパラグラフデータを返す
        return section_data.get('paragraphs', []) 