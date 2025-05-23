"""AIワーカー."""

import logging
from typing import Set, Dict, Any, Optional
import asyncio
from dataclasses import dataclass

from .base import BaseWorker, Event, EventType
from ..config import Config

logger = logging.getLogger(__name__)


@dataclass
class GenerationRequest:
    """生成リクエストのデータ構造."""
    content_type: str
    input_data: Dict[str, Any]
    context: Dict[str, Any]
    options: Dict[str, Any] = None


class AIWorker(BaseWorker):
    """AI処理ワーカー."""
    
    def __init__(self, config: Config, worker_id: str = "ai_worker"):
        """初期化."""
        super().__init__(config, worker_id)
        self.claude_client = None  # 後で実装
        self.openai_client = None  # 後で実装
        self.rate_limiter = None   # 後で実装
        
    def get_subscriptions(self) -> Set[str]:
        """購読するイベントタイプを返す."""
        return {
            EventType.SECTION_PARSED,
            EventType.PARAGRAPH_PARSED,
            EventType.CHAPTER_AGGREGATED,
            EventType.STRUCTURE_ANALYZED
        }
        
    async def process(self, event: Event) -> None:
        """イベントを処理."""
        try:
            if event.type == EventType.SECTION_PARSED:
                await self._handle_section_parsed(event)
            elif event.type == EventType.PARAGRAPH_PARSED:
                await self._handle_paragraph_parsed(event)
            elif event.type == EventType.CHAPTER_AGGREGATED:
                await self._handle_chapter_aggregated(event)
            elif event.type == EventType.STRUCTURE_ANALYZED:
                await self._handle_structure_analyzed(event)
            else:
                logger.warning(f"Unhandled event type: {event.type}")
                
        except Exception as e:
            logger.error(f"AI worker error: {e}")
            raise
            
    async def _handle_section_parsed(self, event: Event) -> None:
        """セクション解析イベントの処理."""
        section_data = event.data.get('section')
        if not section_data:
            raise ValueError("No section data provided")
            
        logger.info(f"Analyzing structure for section: {section_data.get('title', 'Unknown')}")
        
        # 構造解析を実行
        analysis_result = await self._analyze_section_structure(section_data)
        
        # 構造解析完了イベントを発行
        if self.event_bus:
            analysis_event = Event(
                event_type=EventType.STRUCTURE_ANALYZED,
                workflow_id=event.workflow_id,
                data={
                    'section': section_data,
                    'analysis': analysis_result,
                    'chapter': event.data.get('chapter')
                },
                trace_id=event.trace_id
            )
            await self.event_bus.publish(analysis_event)
            
    async def _handle_paragraph_parsed(self, event: Event) -> None:
        """パラグラフ解析イベントの処理."""
        paragraph_data = event.data.get('paragraph')
        section_data = event.data.get('section')
        
        if not paragraph_data:
            raise ValueError("No paragraph data provided")
            
        logger.info(f"Generating content for paragraph {paragraph_data.get('index', 0)}")
        
        # 並列でコンテンツ生成
        generation_tasks = [
            self._generate_article(paragraph_data, section_data),
            self._generate_script(paragraph_data, section_data),
            self._generate_script_json(paragraph_data, section_data),
            self._generate_tweet(paragraph_data, section_data),
            self._generate_description(paragraph_data, section_data)
        ]
        
        results = await asyncio.gather(*generation_tasks, return_exceptions=True)
        
        # 成功した結果をイベントとして発行
        for idx, result in enumerate(results):
            if not isinstance(result, Exception) and result:
                content_event = Event(
                    event_type=EventType.CONTENT_GENERATED,
                    workflow_id=event.workflow_id,
                    data={
                        'content': result,
                        'paragraph': paragraph_data,
                        'section': section_data
                    },
                    trace_id=event.trace_id
                )
                await self.event_bus.publish(content_event)
            elif isinstance(result, Exception):
                logger.error(f"Content generation failed for task {idx}: {result}")
                
    async def _handle_chapter_aggregated(self, event: Event) -> None:
        """チャプター集約イベントの処理."""
        chapter_data = event.data.get('chapter')
        if not chapter_data:
            raise ValueError("No chapter data provided")
            
        logger.info(f"Generating metadata for chapter: {chapter_data.get('title', 'Unknown')}")
        
        # メタデータ生成
        metadata = await self._generate_chapter_metadata(chapter_data)
        
        # サムネイル生成
        thumbnail_data = await self._generate_thumbnail(chapter_data)
        
        # メタデータ生成完了イベントを発行
        if self.event_bus:
            metadata_event = Event(
                event_type=EventType.METADATA_GENERATED,
                workflow_id=event.workflow_id,
                data={
                    'chapter': chapter_data,
                    'metadata': metadata,
                    'thumbnail': thumbnail_data
                },
                trace_id=event.trace_id
            )
            await self.event_bus.publish(metadata_event)
            
    async def _handle_structure_analyzed(self, event: Event) -> None:
        """構造解析イベントの処理."""
        section_data = event.data.get('section')
        analysis_result = event.data.get('analysis')
        
        if not section_data or not analysis_result:
            logger.warning("Incomplete structure analysis data")
            return
            
        logger.info(f"Structure analysis completed for section: {section_data.get('title', 'Unknown')}")
        
        # 必要に応じて追加の処理を実行
        # 例: 特定の構造パターンに基づく追加のコンテンツ生成
        
    async def _analyze_section_structure(self, section_data: Dict[str, Any]) -> Dict[str, Any]:
        """セクションの構造を解析."""
        # TODO: 実際のAI APIを使用した構造解析
        content = section_data.get('content', '')
        paragraphs = section_data.get('paragraphs', [])
        
        # 基本的な構造解析（実装例）
        analysis = {
            'content_type': self._classify_content_type(content),
            'complexity_level': self._assess_complexity(content),
            'key_concepts': self._extract_key_concepts(content),
            'paragraph_count': len(paragraphs),
            'estimated_reading_time': self._estimate_reading_time(content),
            'recommended_formats': self._recommend_formats(content)
        }
        
        return analysis
        
    async def _generate_article(self, paragraph_data: Dict[str, Any], section_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """記事コンテンツを生成."""
        try:
            # TODO: 実際のAI APIを使用した記事生成
            content = paragraph_data.get('content', '')
            section_title = section_data.get('title', '') if section_data else ''
            
            # シミュレーション: 実際の実装では Claude/OpenAI API を使用
            generated_article = {
                'type': 'article',
                'title': f"記事: {section_title}",
                'content': f"【記事】{content}\n\nこの内容について詳しく解説します...",
                'word_count': len(content.split()) * 3,  # 拡張されたコンテンツの単語数
                'format': 'markdown'
            }
            
            await asyncio.sleep(0.1)  # API呼び出しのシミュレーション
            return generated_article
            
        except Exception as e:
            logger.error(f"Article generation failed: {e}")
            return None
            
    async def _generate_script(self, paragraph_data: Dict[str, Any], section_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """台本コンテンツを生成."""
        try:
            content = paragraph_data.get('content', '')
            section_title = section_data.get('title', '') if section_data else ''
            
            # シミュレーション: 実際の実装では Claude/OpenAI API を使用
            generated_script = {
                'type': 'script',
                'title': f"台本: {section_title}",
                'content': f"【台本】\nナレーター: {content}\n\n（解説を追加）\nこのポイントについて詳しく説明しましょう...",
                'estimated_duration': 120,  # 秒
                'format': 'text'
            }
            
            await asyncio.sleep(0.1)  # API呼び出しのシミュレーション
            return generated_script
            
        except Exception as e:
            logger.error(f"Script generation failed: {e}")
            return None
            
    async def _generate_script_json(self, paragraph_data: Dict[str, Any], section_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """JSON形式の台本を生成."""
        try:
            content = paragraph_data.get('content', '')
            section_title = section_data.get('title', '') if section_data else ''
            
            # シミュレーション: 実際の実装では Claude/OpenAI API を使用
            generated_script_json = {
                'type': 'script_json',
                'title': f"台本JSON: {section_title}",
                'content': {
                    'scenes': [
                        {
                            'id': 1,
                            'speaker': 'ナレーター',
                            'text': content,
                            'duration': 30,
                            'notes': '基本説明'
                        },
                        {
                            'id': 2,
                            'speaker': 'ナレーター',
                            'text': 'より詳しい解説を続けます...',
                            'duration': 60,
                            'notes': '詳細説明'
                        }
                    ],
                    'total_duration': 90
                },
                'format': 'json'
            }
            
            await asyncio.sleep(0.1)  # API呼び出しのシミュレーション
            return generated_script_json
            
        except Exception as e:
            logger.error(f"Script JSON generation failed: {e}")
            return None
            
    async def _generate_tweet(self, paragraph_data: Dict[str, Any], section_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """ツイートコンテンツを生成."""
        try:
            content = paragraph_data.get('content', '')
            section_title = section_data.get('title', '') if section_data else ''
            
            # シミュレーション: 実際の実装では Claude/OpenAI API を使用
            # ツイートは280文字制限
            tweet_content = f"💡 {section_title}: {content[:100]}... #技術書 #学習"
            
            generated_tweet = {
                'type': 'tweet',
                'content': tweet_content,
                'character_count': len(tweet_content),
                'hashtags': ['#技術書', '#学習'],
                'format': 'text'
            }
            
            await asyncio.sleep(0.1)  # API呼び出しのシミュレーション
            return generated_tweet
            
        except Exception as e:
            logger.error(f"Tweet generation failed: {e}")
            return None
            
    async def _generate_description(self, paragraph_data: Dict[str, Any], section_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """説明文を生成."""
        try:
            content = paragraph_data.get('content', '')
            section_title = section_data.get('title', '') if section_data else ''
            
            # シミュレーション: 実際の実装では Claude/OpenAI API を使用
            generated_description = {
                'type': 'description',
                'title': f"説明: {section_title}",
                'content': f"【要約】\n{content}\n\n【詳細説明】\nこの内容は重要なポイントを含んでおり、理解を深めるための具体例や背景情報を提供します。",
                'summary': content[:200] + "..." if len(content) > 200 else content,
                'format': 'markdown'
            }
            
            await asyncio.sleep(0.1)  # API呼び出しのシミュレーション
            return generated_description
            
        except Exception as e:
            logger.error(f"Description generation failed: {e}")
            return None
            
    async def _generate_chapter_metadata(self, chapter_data: Dict[str, Any]) -> Dict[str, Any]:
        """チャプターのメタデータを生成."""
        try:
            title = chapter_data.get('title', '')
            sections = chapter_data.get('sections', [])
            
            # 基本的なメタデータ生成
            metadata = {
                'title': title,
                'section_count': len(sections),
                'total_paragraphs': sum(len(section.get('paragraphs', [])) for section in sections),
                'estimated_reading_time': self._estimate_reading_time(chapter_data.get('content', '')),
                'difficulty_level': 'intermediate',  # TODO: AI分析
                'key_topics': [],  # TODO: AI抽出
                'summary': f"{title}の概要説明",  # TODO: AI生成
                'generated_at': asyncio.get_event_loop().time()
            }
            
            return metadata
            
        except Exception as e:
            logger.error(f"Metadata generation failed: {e}")
            return {}
            
    async def _generate_thumbnail(self, chapter_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """サムネイルデータを生成."""
        try:
            title = chapter_data.get('title', '')
            
            # サムネイル生成指示（実際の画像生成は MediaWorker で行う）
            thumbnail_request = {
                'type': 'thumbnail',
                'title': title,
                'style': 'modern',
                'color_scheme': 'blue',
                'text_overlay': title,
                'dimensions': {
                    'width': 1200,
                    'height': 630
                },
                'format': 'png'
            }
            
            return thumbnail_request
            
        except Exception as e:
            logger.error(f"Thumbnail data generation failed: {e}")
            return None
            
    def _classify_content_type(self, content: str) -> str:
        """コンテンツタイプを分類."""
        content_lower = content.lower()
        
        # 技術用語の検出
        tech_terms = ['api', 'database', 'server', 'client', 'algorithm', 'code']
        if any(term in content_lower for term in tech_terms) or '```' in content:
            return 'technical'
        elif 'example' in content_lower or '例' in content:
            return 'example'
        elif 'overview' in content_lower or '概要' in content:
            return 'overview'
        else:
            return 'general'
            
    def _assess_complexity(self, content: str) -> str:
        """コンテンツの複雑さを評価."""
        word_count = len(content.split())
        
        if word_count < 50:
            return 'simple'
        elif word_count < 200:
            return 'moderate'
        else:
            return 'complex'
            
    def _extract_key_concepts(self, content: str) -> list[str]:
        """キーコンセプトを抽出."""
        # TODO: 実際のAI分析または自然言語処理
        # 簡易的な実装
        keywords = []
        
        # 一般的な技術用語を検索
        tech_terms = ['API', 'database', 'server', 'client', 'algorithm', 'data', 'system']
        for term in tech_terms:
            if term.lower() in content.lower():
                keywords.append(term)
                
        return keywords[:5]  # 最大5個
        
    def _estimate_reading_time(self, content: str) -> int:
        """読書時間を推定（分）."""
        word_count = len(content.split())
        # 平均読書速度: 200単語/分
        return max(1, word_count // 200)
        
    def _recommend_formats(self, content: str) -> list[str]:
        """推奨フォーマットを決定."""
        formats = ['article', 'description']
        
        content_type = self._classify_content_type(content)
        
        if content_type == 'technical':
            formats.extend(['script', 'tutorial'])
        elif content_type == 'overview':
            formats.extend(['tweet', 'summary'])
        else:
            formats.append('script')
            
        return formats 