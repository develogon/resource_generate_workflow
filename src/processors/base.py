"""コンテンツ処理器の基底クラス."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, Optional, List, Union
import asyncio
import logging
from dataclasses import dataclass

from ..config import Config
from ..models import Content, Chapter, Section, Paragraph

logger = logging.getLogger(__name__)


class ProcessorType(Enum):
    """処理器タイプ."""
    CONTENT = "content"
    CHAPTER = "chapter"
    SECTION = "section"
    PARAGRAPH = "paragraph"
    STRUCTURE = "structure"


@dataclass
class ProcessingRequest:
    """処理リクエスト."""
    content: Union[Content, Chapter, Section, Paragraph, str]
    processor_type: ProcessorType
    options: Dict[str, Any]
    context: Dict[str, Any]


@dataclass
class ProcessingResult:
    """処理結果."""
    content: Union[Content, Chapter, Section, Paragraph, List[Any]]
    metadata: Dict[str, Any]
    processor_type: ProcessorType
    success: bool
    error: Optional[str] = None


class BaseProcessor(ABC):
    """コンテンツ処理器の基底クラス."""
    
    def __init__(self, config: Config):
        """初期化."""
        self.config = config
        self.semaphore = asyncio.Semaphore(config.workers.max_concurrent_tasks)
        
    @abstractmethod
    async def process(self, request: ProcessingRequest) -> ProcessingResult:
        """コンテンツの処理.
        
        Args:
            request: 処理リクエスト
            
        Returns:
            処理結果
        """
        pass
        
    @abstractmethod
    def get_processor_type(self) -> ProcessorType:
        """処理器タイプを返す."""
        pass
        
    async def batch_process(self, requests: List[ProcessingRequest]) -> List[ProcessingResult]:
        """複数コンテンツのバッチ処理.
        
        Args:
            requests: 処理リクエストのリスト
            
        Returns:
            処理結果のリスト
        """
        if not requests:
            return []
            
        tasks = []
        for request in requests:
            task = asyncio.create_task(self._safe_process(request))
            tasks.append(task)
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # エラーハンドリング
        processed_results = []
        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Failed to process content {idx}: {result}")
                processed_results.append(ProcessingResult(
                    content=requests[idx].content,
                    metadata={},
                    processor_type=requests[idx].processor_type,
                    success=False,
                    error=str(result)
                ))
            else:
                processed_results.append(result)
                
        return processed_results
        
    async def _safe_process(self, request: ProcessingRequest) -> ProcessingResult:
        """セマフォ制御付きの安全な処理."""
        async with self.semaphore:
            try:
                return await self.process(request)
            except Exception as e:
                logger.error(f"Processing error: {e}")
                return ProcessingResult(
                    content=request.content,
                    metadata={},
                    processor_type=request.processor_type,
                    success=False,
                    error=str(e)
                )
                
    def validate_request(self, request: ProcessingRequest) -> bool:
        """処理リクエストの検証.
        
        Args:
            request: 処理リクエスト
            
        Returns:
            検証結果
        """
        if not request or not request.content:
            return False
        if request.processor_type != self.get_processor_type():
            return False
        return True
        
    def extract_metadata(self, request: ProcessingRequest, result: Any) -> Dict[str, Any]:
        """処理結果からメタデータを抽出.
        
        Args:
            request: 処理リクエスト
            result: 処理結果
            
        Returns:
            抽出されたメタデータ
        """
        return {
            "processor_type": self.get_processor_type().value,
            "processed_at": asyncio.get_event_loop().time(),
            "input_type": type(request.content).__name__,
            "output_type": type(result).__name__
        } 