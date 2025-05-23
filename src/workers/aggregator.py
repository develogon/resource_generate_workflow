"""集約ワーカー."""

import logging
from typing import Set, Dict, Any, Optional, List
import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import os
from pathlib import Path

from .base import BaseWorker, Event, EventType
from ..config import Config

logger = logging.getLogger(__name__)


@dataclass
class AggregationResult:
    """集約結果のデータ構造."""
    workflow_id: str
    status: str
    total_content_items: int
    processed_images: int
    generated_thumbnails: int
    metadata_entries: int
    aggregated_at: datetime
    content_summary: Dict[str, Any] = field(default_factory=dict)
    processing_stats: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


@dataclass
class WorkflowState:
    """ワークフローの状態管理."""
    workflow_id: str
    status: str = "initialized"
    chapters: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    sections: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    paragraphs: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    content_items: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    processed_images: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    metadata: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


class AggregatorWorker(BaseWorker):
    """結果集約ワーカー."""
    
    def __init__(self, config: Config, worker_id: str = "aggregator_worker"):
        """初期化."""
        super().__init__(config, worker_id)
        self.workflow_states: Dict[str, WorkflowState] = {}
        self.completion_thresholds = {
            'min_chapters': 1,
            'min_sections_per_chapter': 1,
            'min_paragraphs_per_section': 1,
            'min_content_per_paragraph': 3  # article, script, tweet等
        }
        
    def get_subscriptions(self) -> Set[str]:
        """購読するイベントタイプを返す."""
        return {
            EventType.STRUCTURE_ANALYZED,
            EventType.CONTENT_GENERATED,
            EventType.IMAGE_PROCESSED,
            EventType.METADATA_GENERATED,
            EventType.PARAGRAPH_PARSED,
            EventType.SECTION_PARSED,
            EventType.CHAPTER_PARSED
        }
        
    async def process(self, event: Event) -> None:
        """イベントを処理."""
        try:
            # ワークフローの状態を初期化/取得
            workflow_state = self._get_or_create_workflow_state(event.workflow_id)
            
            # イベントタイプ別の処理
            if event.type == EventType.STRUCTURE_ANALYZED:
                await self._handle_structure_analyzed(event, workflow_state)
            elif event.type == EventType.CONTENT_GENERATED:
                await self._handle_content_generated(event, workflow_state)
            elif event.type == EventType.IMAGE_PROCESSED:
                await self._handle_image_processed(event, workflow_state)
            elif event.type == EventType.METADATA_GENERATED:
                await self._handle_metadata_generated(event, workflow_state)
            elif event.type == EventType.PARAGRAPH_PARSED:
                await self._handle_paragraph_parsed(event, workflow_state)
            elif event.type == EventType.SECTION_PARSED:
                await self._handle_section_parsed(event, workflow_state)
            elif event.type == EventType.CHAPTER_PARSED:
                await self._handle_chapter_parsed(event, workflow_state)
            else:
                logger.warning(f"Unhandled event type: {event.type}")
                
            # 完了チェックと最終集約
            await self._check_completion_and_aggregate(workflow_state)
                
        except Exception as e:
            logger.error(f"Aggregator worker error: {e}")
            raise
            
    def _get_or_create_workflow_state(self, workflow_id: str) -> WorkflowState:
        """ワークフロー状態を取得または作成."""
        if workflow_id not in self.workflow_states:
            self.workflow_states[workflow_id] = WorkflowState(workflow_id=workflow_id)
        return self.workflow_states[workflow_id]
        
    async def _handle_structure_analyzed(self, event: Event, workflow_state: WorkflowState) -> None:
        """構造解析イベントの処理."""
        structure = event.data.get('structure')
        if structure:
            logger.info(f"Processing structure analysis for workflow {workflow_state.workflow_id}")
            
            # 章構造の記録
            chapters = structure.get('chapters', [])
            for chapter in chapters:
                chapter_id = self._generate_chapter_id(chapter)
                workflow_state.chapters[chapter_id] = {
                    'data': chapter,
                    'status': 'analyzed',
                    'sections_count': len(chapter.get('sections', [])),
                    'received_at': datetime.now()
                }
                
        workflow_state.updated_at = datetime.now()
        
    async def _handle_content_generated(self, event: Event, workflow_state: WorkflowState) -> None:
        """コンテンツ生成イベントの処理."""
        content = event.data.get('content')
        paragraph = event.data.get('paragraph')
        
        if content and paragraph:
            paragraph_id = self._generate_paragraph_id(paragraph)
            content_key = f"{paragraph_id}_{content.get('type', 'unknown')}"
            
            workflow_state.content_items[content_key] = {
                'content': content,
                'paragraph': paragraph,
                'section': event.data.get('section'),
                'status': 'generated',
                'received_at': datetime.now()
            }
            
            logger.info(f"Recorded content item: {content_key} (type: {content.get('type')})")
            
        workflow_state.updated_at = datetime.now()
        
    async def _handle_image_processed(self, event: Event, workflow_state: WorkflowState) -> None:
        """画像処理イベントの処理."""
        processed_images = event.data.get('processed_images', [])
        thumbnail = event.data.get('thumbnail')
        
        # 処理済み画像の記録
        for img in processed_images:
            if hasattr(img, 'metadata') and img.metadata:
                image_id = img.metadata.get('s3_url', f"img_{len(workflow_state.processed_images)}")
                workflow_state.processed_images[image_id] = {
                    'image_data': {
                        'original_type': img.original_type.value if hasattr(img.original_type, 'value') else str(img.original_type),
                        'format': img.format,
                        'width': img.width,
                        'height': img.height,
                        'file_size': img.file_size,
                        'metadata': img.metadata
                    },
                    'status': 'processed',
                    'received_at': datetime.now()
                }
                
        # サムネイルの記録
        if thumbnail:
            thumbnail_id = f"thumbnail_{workflow_state.workflow_id}"
            workflow_state.processed_images[thumbnail_id] = {
                'image_data': {
                    'original_type': thumbnail.original_type.value if hasattr(thumbnail.original_type, 'value') else str(thumbnail.original_type),
                    'format': thumbnail.format,
                    'width': thumbnail.width,
                    'height': thumbnail.height,
                    'file_size': thumbnail.file_size,
                    'metadata': thumbnail.metadata,
                    'is_thumbnail': True
                },
                'status': 'processed',
                'received_at': datetime.now()
            }
            
        logger.info(f"Recorded {len(processed_images)} processed images and {'1' if thumbnail else '0'} thumbnail")
        workflow_state.updated_at = datetime.now()
        
    async def _handle_metadata_generated(self, event: Event, workflow_state: WorkflowState) -> None:
        """メタデータ生成イベントの処理."""
        metadata = event.data.get('metadata')
        chapter = event.data.get('chapter')
        
        if metadata:
            metadata_id = f"metadata_{chapter.get('title', 'unknown') if chapter else 'general'}"
            workflow_state.metadata[metadata_id] = {
                'data': metadata,
                'chapter': chapter,
                'status': 'generated',
                'received_at': datetime.now()
            }
            
            logger.info(f"Recorded metadata: {metadata_id}")
            
        workflow_state.updated_at = datetime.now()
        
    async def _handle_paragraph_parsed(self, event: Event, workflow_state: WorkflowState) -> None:
        """パラグラフ解析イベントの処理."""
        # パーサーから直接送信されるデータを使用
        paragraph_data = event.data
        
        if paragraph_data and paragraph_data.get('content'):
            paragraph_id = self._generate_paragraph_id(paragraph_data)
            workflow_state.paragraphs[paragraph_id] = {
                'data': paragraph_data,
                'section': None,  # セクション情報は別途管理
                'status': 'parsed',
                'content_generated': {},  # 生成されたコンテンツを追跡
                'received_at': datetime.now()
            }
            
        workflow_state.updated_at = datetime.now()
        
    async def _handle_section_parsed(self, event: Event, workflow_state: WorkflowState) -> None:
        """セクション解析イベントの処理."""
        # パーサーから直接送信されるデータを使用
        section_data = event.data
        
        if section_data and section_data.get('content'):
            section_id = self._generate_section_id(section_data)
            workflow_state.sections[section_id] = {
                'data': section_data,
                'chapter': None,  # チャプター情報は別途管理
                'status': 'parsed',
                'paragraphs_count': 0,  # パラグラフは後で追加
                'received_at': datetime.now()
            }
            
        workflow_state.updated_at = datetime.now()
        
    async def _handle_chapter_parsed(self, event: Event, workflow_state: WorkflowState) -> None:
        """チャプター解析イベントの処理."""
        # パーサーから直接送信されるデータを使用
        chapter_data = event.data
        
        if chapter_data and (chapter_data.get('content') or chapter_data.get('title')):
            chapter_id = self._generate_chapter_id(chapter_data)
            if chapter_id in workflow_state.chapters:
                # 既存のチャプター情報を更新
                workflow_state.chapters[chapter_id].update({
                    'status': 'parsed',
                    'updated_at': datetime.now()
                })
            else:
                # 新しいチャプターとして記録
                workflow_state.chapters[chapter_id] = {
                    'data': chapter_data,
                    'status': 'parsed',
                    'sections_count': 0,  # セクションは後で追加
                    'received_at': datetime.now()
                }
                
        workflow_state.updated_at = datetime.now()
        
    async def _check_completion_and_aggregate(self, workflow_state: WorkflowState) -> None:
        """完了チェックと最終集約の実行."""
        completion_status = self._assess_completion_status(workflow_state)
        
        if completion_status['is_complete']:
            logger.info(f"Workflow {workflow_state.workflow_id} is complete. Starting final aggregation.")
            
            # 最終集約を実行
            aggregation_result = await self._perform_final_aggregation(workflow_state)
            
            # 完了イベントを発行
            if self.event_bus:
                completion_event = Event(
                    type=EventType.WORKFLOW_COMPLETED,
                    workflow_id=workflow_state.workflow_id,
                    data={
                        'aggregation_result': aggregation_result,
                        'workflow_state': self._serialize_workflow_state(workflow_state),
                        'completion_summary': completion_status
                    }
                )
                await self.event_bus.publish(completion_event)
                
            # 最終出力の生成（完了イベント発行後）
            await self._generate_final_outputs(workflow_state, aggregation_result)
            
            # ワークフロー状態を更新
            workflow_state.status = 'completed'
            workflow_state.updated_at = datetime.now()
            
        elif completion_status['progress'] > 0.5:  # 50%以上進行した場合
            # 中間集約を実行
            await self._perform_intermediate_aggregation(workflow_state, completion_status)
            
    def _assess_completion_status(self, workflow_state: WorkflowState) -> Dict[str, Any]:
        """完了状態を評価."""
        total_chapters = len(workflow_state.chapters)
        total_sections = len(workflow_state.sections)
        total_paragraphs = len(workflow_state.paragraphs)
        total_content_items = len(workflow_state.content_items)
        
        # より現実的な期待値を計算
        expected_content_items = max(total_paragraphs * 2, 1)  # パラグラフあたり最低2つのコンテンツ
        
        # 進行率を計算
        progress = 0.0
        if expected_content_items > 0:
            progress = min(total_content_items / expected_content_items, 1.0)
            
        # より緩い完了条件をチェック
        is_complete = (
            total_chapters >= 1 and  # 最低1つのチャプター
            total_sections >= 1 and  # 最低1つのセクション  
            total_paragraphs >= 1 and  # 最低1つのパラグラフ
            total_content_items >= total_paragraphs  # パラグラフ数以上のコンテンツ
        )
        
        # デバッグ情報をログに出力
        logger.info(f"Completion assessment - Chapters: {total_chapters}, Sections: {total_sections}, "
                   f"Paragraphs: {total_paragraphs}, Content items: {total_content_items}, "
                   f"Progress: {progress:.2f}, Complete: {is_complete}")
        
        return {
            'is_complete': is_complete,
            'progress': progress,
            'total_chapters': total_chapters,
            'total_sections': total_sections,
            'total_paragraphs': total_paragraphs,
            'total_content_items': total_content_items,
            'expected_content_items': expected_content_items,
            'completion_percentage': progress * 100
        }
        
    async def _perform_final_aggregation(self, workflow_state: WorkflowState) -> AggregationResult:
        """最終集約を実行."""
        logger.info(f"Performing final aggregation for workflow {workflow_state.workflow_id}")
        
        # 統計の計算
        content_summary = self._generate_content_summary(workflow_state)
        processing_stats = self._calculate_processing_stats(workflow_state)
        
        # 集約結果を作成
        result = AggregationResult(
            workflow_id=workflow_state.workflow_id,
            status='completed',
            total_content_items=len(workflow_state.content_items),
            processed_images=len(workflow_state.processed_images),
            generated_thumbnails=sum(1 for img in workflow_state.processed_images.values() 
                                   if img['image_data'].get('is_thumbnail', False)),
            metadata_entries=len(workflow_state.metadata),
            aggregated_at=datetime.now(),
            content_summary=content_summary,
            processing_stats=processing_stats
        )
        
        return result
        
    async def _perform_intermediate_aggregation(self, workflow_state: WorkflowState, completion_status: Dict[str, Any]) -> None:
        """中間集約を実行."""
        logger.info(f"Performing intermediate aggregation for workflow {workflow_state.workflow_id} ({completion_status['completion_percentage']:.1f}% complete)")
        
        # 中間集約イベントを発行
        if self.event_bus:
            intermediate_event = Event(
                type=EventType.INTERMEDIATE_AGGREGATED,
                workflow_id=workflow_state.workflow_id,
                data={
                    'completion_status': completion_status,
                    'content_summary': self._generate_content_summary(workflow_state),
                    'processing_stats': self._calculate_processing_stats(workflow_state)
                }
            )
            await self.event_bus.publish(intermediate_event)
            
    def _generate_content_summary(self, workflow_state: WorkflowState) -> Dict[str, Any]:
        """コンテンツサマリーを生成."""
        content_types = {}
        total_word_count = 0
        
        for content_item in workflow_state.content_items.values():
            content = content_item['content']
            content_type = content.get('type', 'unknown')
            
            if content_type not in content_types:
                content_types[content_type] = {
                    'count': 0,
                    'total_words': 0,
                    'items': []
                }
                
            content_types[content_type]['count'] += 1
            word_count = content.get('word_count', 0)
            content_types[content_type]['total_words'] += word_count
            total_word_count += word_count
            
            content_types[content_type]['items'].append({
                'title': content.get('title', 'Untitled'),
                'word_count': word_count
            })
            
        return {
            'content_types': content_types,
            'total_word_count': total_word_count,
            'total_chapters': len(workflow_state.chapters),
            'total_sections': len(workflow_state.sections),
            'total_paragraphs': len(workflow_state.paragraphs)
        }
        
    def _calculate_processing_stats(self, workflow_state: WorkflowState) -> Dict[str, Any]:
        """処理統計を計算."""
        now = datetime.now()
        processing_duration = (now - workflow_state.created_at).total_seconds()
        
        # 画像処理統計
        image_stats = {
            'total_processed': len(workflow_state.processed_images),
            'total_size': sum(img['image_data'].get('file_size', 0) 
                            for img in workflow_state.processed_images.values()),
            'format_distribution': {}
        }
        
        for img in workflow_state.processed_images.values():
            img_format = img['image_data'].get('format', 'unknown')
            image_stats['format_distribution'][img_format] = image_stats['format_distribution'].get(img_format, 0) + 1
            
        return {
            'processing_duration_seconds': processing_duration,
            'items_per_second': len(workflow_state.content_items) / max(processing_duration, 1),
            'image_stats': image_stats,
            'metadata_count': len(workflow_state.metadata),
            'last_updated': workflow_state.updated_at.isoformat()
        }
        
    async def _generate_final_outputs(self, workflow_state: WorkflowState, result: AggregationResult) -> None:
        """最終出力を生成."""
        # 出力ディレクトリを確保
        output_dir = Path(self.config.storage.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # JSONレポートの生成
        report = {
            'workflow_id': workflow_state.workflow_id,
            'aggregation_result': {
                'status': result.status,
                'total_content_items': result.total_content_items,
                'processed_images': result.processed_images,
                'generated_thumbnails': result.generated_thumbnails,
                'metadata_entries': result.metadata_entries,
                'aggregated_at': result.aggregated_at.isoformat(),
                'content_summary': result.content_summary,
                'processing_stats': result.processing_stats
            },
            'content_items': self._serialize_content_items(workflow_state),
            'processed_images': self._serialize_processed_images(workflow_state),
            'metadata': self._serialize_metadata(workflow_state)
        }
        
        # レポートファイルを保存
        report_file = output_dir / f"report_{workflow_state.workflow_id}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Generated final report: {report_file}")
        
        # 各コンテンツタイプ別にファイルを保存
        for content_id, content_item in workflow_state.content_items.items():
            content = content_item['content']
            content_type = content.get('type', 'unknown')
            title = content.get('title', 'untitled')
            
            # ファイル名を安全に生成
            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_title = safe_title.replace(' ', '_')[:50]
            
            content_file = output_dir / f"{content_type}_{safe_title}_{content_id}.txt"
            with open(content_file, 'w', encoding='utf-8') as f:
                f.write(f"Title: {title}\n")
                f.write(f"Type: {content_type}\n")
                f.write(f"Generated at: {content_item['received_at']}\n")
                f.write(f"\n{content.get('content', '')}\n")
                
        logger.info(f"Generated {len(workflow_state.content_items)} content files")
        
        # レポート保存イベントを発行
        if self.event_bus:
            report_event = Event(
                type=EventType.REPORT_GENERATED,
                workflow_id=workflow_state.workflow_id,
                data={
                    'report': report,
                    'format': 'json',
                    'output_dir': str(output_dir),
                    'files_generated': len(workflow_state.content_items) + 1
                }
            )
            await self.event_bus.publish(report_event)
            
    def _serialize_workflow_state(self, workflow_state: WorkflowState) -> Dict[str, Any]:
        """ワークフロー状態をシリアライズ."""
        return {
            'workflow_id': workflow_state.workflow_id,
            'status': workflow_state.status,
            'created_at': workflow_state.created_at.isoformat(),
            'updated_at': workflow_state.updated_at.isoformat(),
            'chapters_count': len(workflow_state.chapters),
            'sections_count': len(workflow_state.sections),
            'paragraphs_count': len(workflow_state.paragraphs),
            'content_items_count': len(workflow_state.content_items),
            'processed_images_count': len(workflow_state.processed_images),
            'metadata_count': len(workflow_state.metadata)
        }
        
    def _serialize_content_items(self, workflow_state: WorkflowState) -> Dict[str, Any]:
        """コンテンツアイテムをシリアライズ."""
        return {
            key: {
                'content': item['content'],
                'paragraph_index': item['paragraph'].get('index') if item['paragraph'] else None,
                'section_title': item['section'].get('title') if item['section'] else None,
                'status': item['status'],
                'received_at': item['received_at'].isoformat()
            }
            for key, item in workflow_state.content_items.items()
        }
        
    def _serialize_processed_images(self, workflow_state: WorkflowState) -> Dict[str, Any]:
        """処理済み画像をシリアライズ."""
        return {
            key: {
                'original_type': item['image_data']['original_type'],
                'format': item['image_data']['format'],
                'width': item['image_data']['width'],
                'height': item['image_data']['height'],
                'file_size': item['image_data']['file_size'],
                's3_url': item['image_data']['metadata'].get('s3_url') if item['image_data'].get('metadata') else None,
                'is_thumbnail': item['image_data'].get('is_thumbnail', False),
                'status': item['status'],
                'received_at': item['received_at'].isoformat()
            }
            for key, item in workflow_state.processed_images.items()
        }
        
    def _serialize_metadata(self, workflow_state: WorkflowState) -> Dict[str, Any]:
        """メタデータをシリアライズ."""
        return {
            key: {
                'data': item['data'],
                'chapter_title': item['chapter'].get('title') if item['chapter'] else None,
                'status': item['status'],
                'received_at': item['received_at'].isoformat()
            }
            for key, item in workflow_state.metadata.items()
        }
        
    def _generate_chapter_id(self, chapter: Dict[str, Any]) -> str:
        """チャプターIDを生成."""
        title = chapter.get('title', 'unknown')
        index = chapter.get('index', 0)
        return f"chapter_{index}_{title.replace(' ', '_')[:30]}"
        
    def _generate_section_id(self, section: Dict[str, Any]) -> str:
        """セクションIDを生成."""
        title = section.get('title', 'unknown')
        chapter_index = section.get('chapter_index', 0)
        section_index = section.get('section_index', 0)
        return f"section_{chapter_index}_{section_index}_{title.replace(' ', '_')[:20]}"
        
    def _generate_paragraph_id(self, paragraph: Dict[str, Any]) -> str:
        """パラグラフIDを生成."""
        chapter_index = paragraph.get('chapter_index', 0)
        section_index = paragraph.get('section_index', 0)
        paragraph_index = paragraph.get('paragraph_index', 0)
        return f"paragraph_{chapter_index}_{section_index}_{paragraph_index}"
        
    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """ワークフローの状態を取得."""
        if workflow_id in self.workflow_states:
            return self._serialize_workflow_state(self.workflow_states[workflow_id])
        return None
        
    def get_all_workflow_statuses(self) -> Dict[str, Dict[str, Any]]:
        """すべてのワークフロー状態を取得."""
        return {
            workflow_id: self._serialize_workflow_state(state)
            for workflow_id, state in self.workflow_states.items()
        }
        
    def cleanup_completed_workflows(self, older_than_hours: int = 24) -> int:
        """完了したワークフローをクリーンアップ."""
        cutoff_time = datetime.now() - timedelta(hours=older_than_hours)
        to_remove = []
        
        for workflow_id, state in self.workflow_states.items():
            if state.status == 'completed' and state.updated_at < cutoff_time:
                to_remove.append(workflow_id)
                
        for workflow_id in to_remove:
            del self.workflow_states[workflow_id]
            
        logger.info(f"Cleaned up {len(to_remove)} completed workflows")
        return len(to_remove) 