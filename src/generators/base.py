"""コンテンツ生成器の基底クラス."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, Optional, List
import asyncio
import logging
from dataclasses import dataclass

# Config のインポートをオプション化
try:
    from ..config import Config
except ImportError:
    # テスト環境など、config が利用できない場合のフォールバック
    class Config:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
            # デフォルト値の設定
            if not hasattr(self, 'workers'):
                from types import SimpleNamespace
                self.workers = SimpleNamespace()
                self.workers.max_concurrent_tasks = 10

# プロンプトローダーをインポート
from ..utils.prompt_loader import get_prompt_loader

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
    title: str
    content: str
    content_type: str
    lang: str
    options: Dict[str, Any] = None
    
    def __post_init__(self):
        """初期化後処理."""
        if self.options is None:
            self.options = {}


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
        # 実装されていない属性の安全な処理
        max_tasks = getattr(config.workers, 'max_concurrent_tasks', 10) if hasattr(config, 'workers') else 10
        self.semaphore = asyncio.Semaphore(max_tasks)
        self.prompt_loader = get_prompt_loader()
        
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
        
    def get_prompt_template(self) -> str:
        """プロンプトテンプレートを返す."""
        # デフォルトでは生成タイプに基づいてプロンプトファイルから読み込み
        generation_type = self.get_generation_type().value
        return self.prompt_loader.get_combined_prompt(generation_type)
        
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
                    generation_type=self.get_generation_type(),
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
                    generation_type=self.get_generation_type(),
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
        # コンテンツが空でないことを確認
        if not request.content or not request.content.strip():
            return False
        return True
        
    def build_prompt(self, request: GenerationRequest) -> str:
        """プロンプトの構築.
        
        Args:
            request: 生成リクエスト
            
        Returns:
            構築されたプロンプト
        """
        # プロンプトファイルから読み込み
        generation_type = self.get_generation_type().value
        
        # プロンプト変数を準備
        prompt_vars = {
            "CHAPTER_TITLE": request.options.get("chapter_title", ""),
            "SECTION_TITLE": request.title,
            "SECTION_CONTENT": request.content,
            "title": request.title,
            "content": request.content,
            "lang": request.lang,
            "content_type": request.content_type
        }
        
        # リクエストのオプションをマージ
        prompt_vars.update(request.options)
        
        # プロンプトテンプレートを取得してフォーマット
        return self.prompt_loader.get_combined_prompt(generation_type, **prompt_vars)
            
    def extract_metadata(self, request: GenerationRequest, generated_content: str) -> Dict[str, Any]:
        """生成されたコンテンツからメタデータを抽出.
        
        Args:
            request: 生成リクエスト
            generated_content: 生成されたコンテンツ
            
        Returns:
            抽出されたメタデータ
        """
        import time
        return {
            "word_count": len(generated_content.split()),
            "char_count": len(generated_content),
            "generation_type": self.get_generation_type().value,
            "source_title": request.title,
            "generated_at": time.time()
        } 