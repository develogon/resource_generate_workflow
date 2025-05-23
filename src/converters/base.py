"""画像変換器の基底クラス."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional, Dict, Any
import asyncio
import logging

from ..config import Config

logger = logging.getLogger(__name__)


class ImageType(Enum):
    """画像タイプ."""
    SVG = "svg"
    DRAWIO = "drawio"
    MERMAID = "mermaid"
    PNG = "png"
    JPG = "jpg"


class BaseConverter(ABC):
    """画像変換器の基底クラス."""
    
    def __init__(self, config: Config):
        """初期化."""
        self.config = config
        self.semaphore = asyncio.Semaphore(config.workers.max_concurrent_tasks)
        
    @abstractmethod
    async def convert(self, source: str, **kwargs) -> bytes:
        """単一画像の変換.
        
        Args:
            source: 変換元の画像データ（文字列形式）
            **kwargs: 追加のオプション
            
        Returns:
            変換後の画像データ（バイナリ）
        """
        pass
        
    @abstractmethod
    def get_supported_type(self) -> ImageType:
        """サポートする画像タイプを返す."""
        pass
        
    async def batch_convert(self, sources: List[str], **kwargs) -> List[bytes]:
        """複数画像のバッチ変換.
        
        Args:
            sources: 変換元の画像データリスト
            **kwargs: 追加のオプション
            
        Returns:
            変換後の画像データリスト
        """
        if not sources:
            return []
            
        tasks = []
        for source in sources:
            task = asyncio.create_task(self._safe_convert(source, **kwargs))
            tasks.append(task)
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # エラーハンドリング
        converted_images = []
        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Failed to convert image {idx}: {result}")
                # エラー時はスキップ（または代替処理）
                continue
            converted_images.append(result)
            
        return converted_images
        
    async def _safe_convert(self, source: str, **kwargs) -> bytes:
        """セマフォ制御付きの安全な変換."""
        async with self.semaphore:
            try:
                return await self.convert(source, **kwargs)
            except Exception as e:
                logger.error(f"Conversion error: {e}")
                raise
                
    def validate_source(self, source: str) -> bool:
        """変換元データの検証.
        
        Args:
            source: 変換元データ
            
        Returns:
            検証結果
        """
        if not source or not isinstance(source, str):
            return False
        return True
        
    def get_output_format(self) -> str:
        """出力フォーマットを取得."""
        return self.config.image.format.lower()
        
    def get_output_size(self) -> tuple[int, int]:
        """出力サイズを取得."""
        return (self.config.image.width, self.config.image.height) 