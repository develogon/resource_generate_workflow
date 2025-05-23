"""OpenAI API クライアント."""

import base64
import hashlib
import json
import time
from typing import Any, Dict, List, Optional, Union

import httpx

from ..config.settings import Config
from ..utils.cache import AsyncCache
from ..utils.logger import get_logger
from .base import APIError, BaseClient

logger = get_logger(__name__)


class OpenAIClient(BaseClient):
    """OpenAI API クライアント."""
    
    def __init__(self, config: Config):
        super().__init__(config, "openai")
        
        if not config.openai.api_key:
            raise ValueError("OpenAI API key is required")
            
        self.api_key = config.openai.api_key
        self.base_url = config.openai.base_url
        self.model = config.openai.model
        self.max_tokens = config.openai.max_tokens
        self.temperature = config.openai.temperature
        
        # キャッシュの初期化
        self.cache = AsyncCache(
            max_size=config.cache.size,
            ttl=config.cache.ttl
        )
        
    def _get_rate_limit(self) -> int:
        """OpenAI API のレート制限を取得."""
        # OpenAIのレート制限は設定で指定されていない場合のデフォルト値
        return getattr(self.config.openai, 'rate_limit', 60)
        
    def _get_headers(self) -> Dict[str, str]:
        """リクエストヘッダーを取得."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "resource-generate-workflow/0.1.0",
        }
        
    async def _handle_response(self, response: httpx.Response) -> Dict[str, Any]:
        """OpenAI API のレスポンスを処理."""
        try:
            data = response.json()
            
            # OpenAI API 特有のエラーハンドリング
            if "error" in data:
                error_msg = data["error"].get("message", "Unknown error")
                error_type = data["error"].get("type", "unknown")
                error_code = data["error"].get("code", "unknown")
                
                if error_type == "insufficient_quota":
                    raise APIError(f"Quota exceeded: {error_msg}", response.status_code, data)
                elif error_type == "rate_limit_exceeded":
                    raise APIError(f"Rate limit exceeded: {error_msg}", response.status_code, data)
                elif error_type == "invalid_api_key":
                    raise APIError(f"Invalid API key: {error_msg}", response.status_code, data)
                else:
                    raise APIError(f"OpenAI API error ({error_type}): {error_msg}", response.status_code, data)
                    
            return data
            
        except json.JSONDecodeError as e:
            raise APIError(f"Invalid JSON response: {e}", response.status_code)
            
    async def _perform_health_check(self):
        """OpenAI API の健全性チェック."""
        # 最小限のリクエストで健全性をチェック
        await self.generate_text(
            prompt="Hello",
            max_tokens=10,
            use_cache=False
        )
        
    def _generate_cache_key(self, prompt: str, **kwargs) -> str:
        """キャッシュキーを生成."""
        # パラメータを正規化してハッシュ化
        cache_data = {
            "prompt": prompt,
            "model": kwargs.get("model", self.model),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "temperature": kwargs.get("temperature", self.temperature),
            "system_prompt": kwargs.get("system_prompt"),
        }
        
        # 画像データがある場合はハッシュ化
        if kwargs.get("images"):
            images_hash = hashlib.md5(
                str([base64.b64encode(img).decode() for img in kwargs["images"]]).encode()
            ).hexdigest()
            cache_data["images_hash"] = images_hash
            
        cache_str = json.dumps(cache_data, sort_keys=True)
        return hashlib.sha256(cache_str.encode()).hexdigest()
        
    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        images: Optional[List[bytes]] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """テキスト生成."""
        # キャッシュチェック
        if use_cache:
            cache_key = self._generate_cache_key(
                prompt,
                system_prompt=system_prompt,
                images=images,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            cached_result = await self.cache.get(cache_key)
            if cached_result:
                self.logger.debug("Cache hit for OpenAI API request")
                return cached_result
                
        # リクエスト構築
        request_data = self._build_request(
            prompt=prompt,
            system_prompt=system_prompt,
            images=images,
            model=model or self.model,
            max_tokens=max_tokens or self.max_tokens,
            temperature=temperature or self.temperature
        )
        
        # API呼び出し
        result = await self._make_request(
            method="POST",
            url=f"{self.base_url}/chat/completions",
            json=request_data
        )
        
        # キャッシュに保存
        if use_cache:
            await self.cache.set(cache_key, result)
            
        return result
        
    def _build_request(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        images: Optional[List[bytes]] = None,
        model: str = None,
        max_tokens: int = None,
        temperature: float = None
    ) -> Dict[str, Any]:
        """リクエストデータを構築."""
        # メッセージの構築
        messages = []
        
        # システムプロンプトがある場合
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
            
        # ユーザーメッセージの構築
        if images and len(images) > 0:
            # 画像がある場合（GPT-4 Vision）
            content = [
                {
                    "type": "text",
                    "text": prompt
                }
            ]
            
            # 画像データを追加
            for image_data in images:
                image_b64 = base64.b64encode(image_data).decode()
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{image_b64}"
                    }
                })
                
            messages.append({
                "role": "user",
                "content": content
            })
        else:
            # テキストのみの場合
            messages.append({
                "role": "user",
                "content": prompt
            })
        
        # リクエストデータ
        request_data = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        return request_data
        
    async def generate_structured_content(
        self,
        prompt: str,
        content_type: str,
        system_prompt: Optional[str] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """構造化コンテンツの生成."""
        # コンテンツタイプ別のシステムプロンプト
        type_prompts = {
            "article": """
以下の指示に従って記事を生成してください。
- 構造化されたマークダウン形式で出力
- 適切な見出し（H1, H2, H3）を使用
- 読みやすい段落構成
- 必要に応じてコードブロックやリストを使用
""",
            "script": """
以下の指示に従って動画台本を生成してください。
- セクション別に構成
- 話し言葉調
- 視聴者の理解を促進する構成
- 適切な間や強調ポイントを示す
""",
            "tweet": """
以下の指示に従ってツイートを生成してください。
- 280文字以内
- ハッシュタグを適切に使用
- エンゲージメントを促進する内容
- 複数のバリエーションを提供
""",
            "description": """
以下の指示に従って説明文を生成してください。
- 簡潔で分かりやすい表現
- 適切な長さ（50-150文字程度）
- SEOを考慮したキーワード配置
- 読者の興味を引く内容
"""
        }
        
        # システムプロンプトの組み合わせ
        full_system_prompt = type_prompts.get(content_type, "")
        if system_prompt:
            full_system_prompt += f"\n\n{system_prompt}"
            
        return await self.generate_text(
            prompt=prompt,
            system_prompt=full_system_prompt,
            use_cache=use_cache
        )
        
    async def batch_generate(
        self,
        prompts: List[str],
        content_type: str = "article",
        system_prompt: Optional[str] = None,
        max_concurrent: int = 3
    ) -> List[Dict[str, Any]]:
        """バッチ生成."""
        import asyncio
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def generate_single(prompt: str) -> Dict[str, Any]:
            async with semaphore:
                try:
                    return await self.generate_structured_content(
                        prompt=prompt,
                        content_type=content_type,
                        system_prompt=system_prompt
                    )
                except Exception as e:
                    self.logger.error(f"Batch generation failed for prompt: {e}")
                    return {"error": str(e), "prompt": prompt}
                    
        tasks = [generate_single(prompt) for prompt in prompts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 例外をログに記録し、エラー情報に変換
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"Batch generation exception for prompt {i}: {result}")
                processed_results.append({"error": str(result), "prompt": prompts[i]})
            else:
                processed_results.append(result)
                
        return processed_results
        
    async def get_cache_stats(self) -> Dict[str, Any]:
        """キャッシュ統計を取得."""
        cache_stats = await self.cache.get_stats()
        client_stats = self.get_stats()
        
        return {
            "client_stats": client_stats,
            "cache_stats": cache_stats,
            "service_name": self.service_name
        } 