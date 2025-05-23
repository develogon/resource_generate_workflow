"""メディアワーカー."""

import logging
from typing import Set, Dict, Any, Optional, List, Tuple
import asyncio
import base64
import hashlib
import time
from dataclasses import dataclass
from enum import Enum

from .base import BaseWorker, Event, EventType
from ..config import Config

logger = logging.getLogger(__name__)


class ImageType(Enum):
    """画像タイプ列挙型."""
    SVG = "svg"
    DRAWIO = "drawio"
    MERMAID = "mermaid"
    PNG = "png"
    JPG = "jpg"
    WEBP = "webp"


@dataclass
class ImageProcessingRequest:
    """画像処理リクエストのデータ構造."""
    image_type: ImageType
    content: str
    options: Dict[str, Any] = None
    output_format: str = "png"


@dataclass
class ProcessedImage:
    """処理済み画像のデータ構造."""
    original_type: ImageType
    processed_data: bytes
    format: str
    width: int
    height: int
    file_size: int
    metadata: Dict[str, Any] = None


class MediaWorker(BaseWorker):
    """メディア処理ワーカー."""
    
    def __init__(self, config: Config, worker_id: str = "media_worker"):
        """初期化."""
        super().__init__(config, worker_id)
        self.s3_client = None  # 後で実装
        self.converter_pool = None  # 後で実装
        
    def get_subscriptions(self) -> Set[str]:
        """購読するイベントタイプを返す."""
        return {
            EventType.CONTENT_GENERATED,
            EventType.THUMBNAIL_GENERATED,
            EventType.METADATA_GENERATED
        }
        
    async def process(self, event: Event) -> None:
        """イベントを処理."""
        try:
            if event.type == EventType.CONTENT_GENERATED:
                await self._handle_content_generated(event)
            elif event.type == EventType.THUMBNAIL_GENERATED:
                await self._handle_thumbnail_generated(event)
            elif event.type == EventType.METADATA_GENERATED:
                await self._handle_metadata_generated(event)
            else:
                logger.warning(f"Unhandled event type: {event.type}")
                
        except Exception as e:
            logger.error(f"Media worker error: {e}")
            raise
            
    async def _handle_content_generated(self, event: Event) -> None:
        """コンテンツ生成イベントの処理."""
        content_data = event.data.get('content')
        if not content_data:
            raise ValueError("No content data provided")
            
        logger.info(f"Processing media for content type: {content_data.get('type', 'unknown')}")
        
        # コンテンツ内の画像を抽出・処理
        updated_content, processed_images = await self._process_content_images(
            content_data, event.workflow_id
        )
        
        # 処理済みコンテンツイベントを発行
        if updated_content or processed_images:
            if self.event_bus:
                processed_event = Event(
                    event_type=EventType.IMAGE_PROCESSED,
                    workflow_id=event.workflow_id,
                    data={
                        'original_content': content_data,
                        'updated_content': updated_content or content_data,
                        'processed_images': processed_images,
                        'paragraph': event.data.get('paragraph'),
                        'section': event.data.get('section')
                    },
                    trace_id=event.trace_id
                )
                await self.event_bus.publish(processed_event)
                
    async def _handle_thumbnail_generated(self, event: Event) -> None:
        """サムネイル生成イベントの処理."""
        thumbnail_data = event.data.get('thumbnail')
        if not thumbnail_data:
            logger.warning("No thumbnail data provided")
            return
            
        logger.info(f"Processing thumbnail: {thumbnail_data.get('title', 'Unknown')}")
        
        # サムネイル画像を生成
        generated_thumbnail = await self._generate_thumbnail_image(
            thumbnail_data, event.workflow_id
        )
        
        # サムネイル処理完了イベントを発行
        if generated_thumbnail and self.event_bus:
            thumbnail_event = Event(
                event_type=EventType.IMAGE_PROCESSED,
                workflow_id=event.workflow_id,
                data={
                    'thumbnail': generated_thumbnail,
                    'chapter': event.data.get('chapter'),
                    'metadata': event.data.get('metadata')
                },
                trace_id=event.trace_id
            )
            await self.event_bus.publish(thumbnail_event)
            
    async def _handle_metadata_generated(self, event: Event) -> None:
        """メタデータ生成イベントの処理."""
        # メタデータに含まれる画像処理が必要な場合の処理
        # 現在は特別な処理は不要
        logger.info("Metadata event received - no additional media processing needed")
        
    async def _process_content_images(self, content_data: Dict[str, Any], workflow_id: str) -> Tuple[Optional[Dict[str, Any]], List[ProcessedImage]]:
        """コンテンツ内の画像を処理."""
        content_text = content_data.get('content', '')
        if not content_text:
            return None, []
            
        # 画像を抽出
        images = self._extract_images_from_content(content_text)
        if not images:
            return None, []
            
        logger.info(f"Found {len(images)} images to process")
        
        # 画像を並列処理
        processing_tasks = []
        for idx, image_info in enumerate(images):
            task = self._process_single_image(image_info, workflow_id, idx)
            processing_tasks.append(task)
            
        processed_results = await asyncio.gather(*processing_tasks, return_exceptions=True)
        
        # 成功した結果のみを収集
        processed_images = []
        url_mapping = {}
        
        for idx, result in enumerate(processed_results):
            if isinstance(result, Exception):
                logger.error(f"Failed to process image {idx}: {result}")
                continue
                
            if result:
                processed_images.append(result)
                # 元の画像参照をS3 URLに置換するためのマッピング
                original_ref = images[idx]['reference']
                url_mapping[original_ref] = result.metadata.get('s3_url') if result.metadata else None
                
        # コンテンツ内の画像参照をS3 URLに置換
        updated_content = content_data.copy()
        if url_mapping:
            updated_content_text = content_text
            for original_ref, s3_url in url_mapping.items():
                if s3_url:
                    updated_content_text = updated_content_text.replace(original_ref, s3_url)
            updated_content['content'] = updated_content_text
            
        return updated_content if url_mapping else None, processed_images
        
    async def _process_single_image(self, image_info: Dict[str, Any], workflow_id: str, index: int) -> Optional[ProcessedImage]:
        """単一画像の処理."""
        try:
            image_type = ImageType(image_info['type'])
            content = image_info['content']
            
            # 画像を変換
            processed_data = await self._convert_image(image_type, content)
            if not processed_data:
                return None
                
            # S3にアップロード
            s3_url = await self._upload_to_s3(
                processed_data, 
                workflow_id, 
                f"image_{index}_{image_type.value}.png"
            )
            
            # ProcessedImageオブジェクトを作成
            processed_image = ProcessedImage(
                original_type=image_type,
                processed_data=processed_data,
                format="png",
                width=self.config.image.width,
                height=self.config.image.height,
                file_size=len(processed_data),
                metadata={
                    's3_url': s3_url,
                    'workflow_id': workflow_id,
                    'processed_at': time.time(),
                    'original_type': image_type.value
                }
            )
            
            return processed_image
            
        except Exception as e:
            logger.error(f"Failed to process single image: {e}")
            return None
            
    async def _generate_thumbnail_image(self, thumbnail_data: Dict[str, Any], workflow_id: str) -> Optional[ProcessedImage]:
        """サムネイル画像を生成."""
        try:
            # サムネイル生成（シミュレーション）
            title = thumbnail_data.get('title', 'Untitled')
            style = thumbnail_data.get('style', 'modern')
            color_scheme = thumbnail_data.get('color_scheme', 'blue')
            dimensions = thumbnail_data.get('dimensions', {'width': 1200, 'height': 630})
            
            # TODO: 実際の画像生成ライブラリを使用
            # 現在はプレースホルダー画像データを生成
            thumbnail_content = await self._create_thumbnail_placeholder(
                title, style, color_scheme, dimensions
            )
            
            # S3にアップロード
            s3_url = await self._upload_to_s3(
                thumbnail_content,
                workflow_id,
                f"thumbnail_{hashlib.md5(title.encode()).hexdigest()}.png"
            )
            
            processed_thumbnail = ProcessedImage(
                original_type=ImageType.PNG,
                processed_data=thumbnail_content,
                format="png",
                width=dimensions['width'],
                height=dimensions['height'],
                file_size=len(thumbnail_content),
                metadata={
                    's3_url': s3_url,
                    'workflow_id': workflow_id,
                    'generated_at': time.time(),
                    'title': title,
                    'style': style,
                    'color_scheme': color_scheme
                }
            )
            
            return processed_thumbnail
            
        except Exception as e:
            logger.error(f"Failed to generate thumbnail: {e}")
            return None
            
    def _extract_images_from_content(self, content: str) -> List[Dict[str, Any]]:
        """コンテンツから画像を抽出."""
        images = []
        
        # SVG画像の抽出
        svg_images = self._extract_svg_images(content)
        images.extend(svg_images)
        
        # Mermaid図の抽出
        mermaid_images = self._extract_mermaid_diagrams(content)
        images.extend(mermaid_images)
        
        # DrawIO図の抽出
        drawio_images = self._extract_drawio_diagrams(content)
        images.extend(drawio_images)
        
        return images
        
    def _extract_svg_images(self, content: str) -> List[Dict[str, Any]]:
        """SVG画像を抽出."""
        import re
        
        # SVGパターンを検索
        svg_pattern = r'<svg[^>]*>.*?</svg>'
        matches = re.finditer(svg_pattern, content, re.DOTALL)
        
        svg_images = []
        for match in matches:
            svg_content = match.group(0)
            svg_images.append({
                'type': 'svg',
                'content': svg_content,
                'reference': svg_content,  # 置換用の参照
                'start': match.start(),
                'end': match.end()
            })
            
        return svg_images
        
    def _extract_mermaid_diagrams(self, content: str) -> List[Dict[str, Any]]:
        """Mermaid図を抽出."""
        import re
        
        # Mermaidコードブロックパターン
        mermaid_pattern = r'```mermaid\n(.*?)\n```'
        matches = re.finditer(mermaid_pattern, content, re.DOTALL)
        
        mermaid_images = []
        for match in matches:
            mermaid_content = match.group(1).strip()
            full_match = match.group(0)
            mermaid_images.append({
                'type': 'mermaid',
                'content': mermaid_content,
                'reference': full_match,  # 置換用の参照
                'start': match.start(),
                'end': match.end()
            })
            
        return mermaid_images
        
    def _extract_drawio_diagrams(self, content: str) -> List[Dict[str, Any]]:
        """DrawIO図を抽出."""
        import re
        
        # DrawIOリンクパターン
        drawio_pattern = r'!\[.*?\]\((.*?\.drawio(?:\.png|\.svg)?)\)'
        matches = re.finditer(drawio_pattern, content)
        
        drawio_images = []
        for match in matches:
            drawio_url = match.group(1)
            full_match = match.group(0)
            drawio_images.append({
                'type': 'drawio',
                'content': drawio_url,
                'reference': full_match,  # 置換用の参照
                'start': match.start(),
                'end': match.end()
            })
            
        return drawio_images
        
    async def _convert_image(self, image_type: ImageType, content: str) -> Optional[bytes]:
        """画像を変換."""
        try:
            if image_type == ImageType.SVG:
                return await self._convert_svg_to_png(content)
            elif image_type == ImageType.MERMAID:
                return await self._convert_mermaid_to_png(content)
            elif image_type == ImageType.DRAWIO:
                return await self._convert_drawio_to_png(content)
            else:
                logger.warning(f"Unsupported image type: {image_type}")
                return None
                
        except Exception as e:
            logger.error(f"Image conversion failed: {e}")
            return None
            
    async def _convert_svg_to_png(self, svg_content: str) -> bytes:
        """SVGをPNGに変換."""
        # TODO: 実際のSVG変換ライブラリ（cairosvg等）を使用
        # 現在はプレースホルダー
        await asyncio.sleep(0.1)  # 変換時間のシミュレーション
        
        # プレースホルダー画像データ（1x1 PNG）
        placeholder_png = base64.b64decode(
            'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=='
        )
        return placeholder_png
        
    async def _convert_mermaid_to_png(self, mermaid_content: str) -> bytes:
        """MermaidをPNGに変換."""
        # TODO: 実際のMermaid変換（mermaid-cli等）を使用
        # 現在はプレースホルダー
        await asyncio.sleep(0.1)  # 変換時間のシミュレーション
        
        # プレースホルダー画像データ
        placeholder_png = base64.b64decode(
            'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=='
        )
        return placeholder_png
        
    async def _convert_drawio_to_png(self, drawio_url: str) -> bytes:
        """DrawIOをPNGに変換."""
        # TODO: 実際のDrawIO変換を実装
        # 現在はプレースホルダー
        await asyncio.sleep(0.1)  # 変換時間のシミュレーション
        
        # プレースホルダー画像データ
        placeholder_png = base64.b64decode(
            'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=='
        )
        return placeholder_png
        
    async def _create_thumbnail_placeholder(self, title: str, style: str, color_scheme: str, dimensions: Dict[str, int]) -> bytes:
        """サムネイルプレースホルダーを作成."""
        # TODO: 実際の画像生成ライブラリを使用
        # 現在はプレースホルダー
        await asyncio.sleep(0.1)  # 生成時間のシミュレーション
        
        # プレースホルダー画像データ
        placeholder_png = base64.b64decode(
            'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=='
        )
        return placeholder_png
        
    async def _upload_to_s3(self, image_data: bytes, workflow_id: str, filename: str) -> str:
        """S3に画像をアップロード."""
        try:
            # TODO: 実際のS3クライアントを実装
            # 現在はシミュレーション
            await asyncio.sleep(0.1)  # アップロード時間のシミュレーション
            
            # S3 URLをシミュレート
            bucket = self.config.aws.s3_bucket or "default-bucket"
            s3_key = f"workflows/{workflow_id}/images/{filename}"
            s3_url = f"https://{bucket}.s3.amazonaws.com/{s3_key}"
            
            logger.info(f"Simulated S3 upload: {filename} -> {s3_url}")
            return s3_url
            
        except Exception as e:
            logger.error(f"S3 upload failed: {e}")
            raise
            
    def get_supported_image_types(self) -> List[ImageType]:
        """サポートされている画像タイプを返す."""
        return [ImageType.SVG, ImageType.MERMAID, ImageType.DRAWIO]
        
    def get_processing_stats(self) -> Dict[str, Any]:
        """処理統計を返す."""
        # TODO: 実際の統計を実装
        return {
            'images_processed': 0,
            'total_size_processed': 0,
            'average_processing_time': 0,
            'supported_formats': [t.value for t in self.get_supported_image_types()]
        } 