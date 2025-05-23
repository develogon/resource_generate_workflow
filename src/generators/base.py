"""コンテンツ生成器の基底クラス."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, Optional, List
import asyncio
import logging
from dataclasses import dataclass

from ..config import Config
from ..models import Content

logger = logging.getLogger(__name__)


class GenerationType(Enum):
    """生成タイプ."""
    ARTICLE = "article"
    SCRIPT = "script"
    TWEET = "tweet"
    DESCRIPTION = "description"
    THUMBNAIL = "thumbnail"


@dataclass
class GenerationRequest:
    """生成リクエスト."""
    content: Content
    generation_type: GenerationType
    options: Dict[str, Any]
    context: Dict[str, Any]


@dataclass
class GenerationResult:
    """生成結果."""
    content: str
    metadata: Dict[str, Any]
    generation_type: GenerationType
    success: bool
    error: Optional[str] = None


class BaseGenerator(ABC):
    """コンテンツ生成器の基底クラス."""
    
    def __init__(self, config: Config):
        """初期化."""
        self.config = config
        self.semaphore = asyncio.Semaphore(config.workers.max_concurrent_tasks)
        
    @abstractmethod
    async def generate(self, request: GenerationRequest) -> GenerationResult:
        """コンテンツの生成.
        
        Args:
            request: 生成リクエスト
            
        Returns:
            生成結果
        """
        pass
        
    @abstractmethod
    def get_generation_type(self) -> GenerationType:
        """生成タイプを返す."""
        pass
        
    @abstractmethod
    def get_prompt_template(self) -> str:
        """プロンプトテンプレートを返す."""
        pass
        
    async def batch_generate(self, requests: List[GenerationRequest]) -> List[GenerationResult]:
        """複数コンテンツのバッチ生成.
        
        Args:
            requests: 生成リクエストのリスト
            
        Returns:
            生成結果のリスト
        """
        if not requests:
            return []
            
        tasks = []
        for request in requests:
            task = asyncio.create_task(self._safe_generate(request))
            tasks.append(task)
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # エラーハンドリング
        generated_results = []
        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Failed to generate content {idx}: {result}")
                generated_results.append(GenerationResult(
                    content="",
                    metadata={},
                    generation_type=requests[idx].generation_type,
                    success=False,
                    error=str(result)
                ))
            else:
                generated_results.append(result)
                
        return generated_results
        
    async def _safe_generate(self, request: GenerationRequest) -> GenerationResult:
        """セマフォ制御付きの安全な生成."""
        async with self.semaphore:
            try:
                return await self.generate(request)
            except Exception as e:
                logger.error(f"Generation error: {e}")
                return GenerationResult(
                    content="",
                    metadata={},
                    generation_type=request.generation_type,
                    success=False,
                    error=str(e)
                )
                
    def validate_request(self, request: GenerationRequest) -> bool:
        """生成リクエストの検証.
        
        Args:
            request: 生成リクエスト
            
        Returns:
            検証結果
        """
        if not request or not request.content:
            return False
        if request.generation_type != self.get_generation_type():
            return False
        # コンテンツが空でないことを確認
        if not request.content.content or not request.content.content.strip():
            return False
        return True
        
    def build_prompt(self, request: GenerationRequest) -> str:
        """プロンプトの構築.
        
        Args:
            request: 生成リクエスト
            
        Returns:
            構築されたプロンプト
        """
        template = self.get_prompt_template()
        
        # コンテンツの情報を抽出
        content_info = {
            "title": request.content.title,
            "content": request.content.content,
            "metadata": request.content.metadata
        }
        
        # 全ての変数を統合（優先順位: context > options > content_info）
        template_vars = {}
        template_vars.update(content_info)
        template_vars.update(request.options)
        template_vars.update(request.context)
        
        # テンプレートに値を埋め込み
        try:
            prompt = template.format(**template_vars)
            return prompt
        except KeyError as e:
            logger.warning(f"Missing template variable: {e}")
            return template
            
    def extract_metadata(self, request: GenerationRequest, generated_content: str) -> Dict[str, Any]:
        """生成されたコンテンツからメタデータを抽出.
        
        Args:
            request: 生成リクエスト
            generated_content: 生成されたコンテンツ
            
        Returns:
            抽出されたメタデータ
        """
        return {
            "word_count": len(generated_content.split()),
            "char_count": len(generated_content),
            "generation_type": self.get_generation_type().value,
            "source_title": request.content.title,
            "generated_at": asyncio.get_event_loop().time()
        } 