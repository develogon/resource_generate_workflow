"""台本生成器."""

import asyncio
import logging
from typing import Dict, Any, Optional

from .base import BaseGenerator, GenerationType, GenerationRequest, GenerationResult

# Config のインポートをオプション化
try:
    from ..config import Config
except ImportError:
    # テスト環境など、config が利用できない場合のフォールバック
    class Config:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

logger = logging.getLogger(__name__)


class ScriptGenerator(BaseGenerator):
    """パラグラフから動画台本を生成する生成器."""
    
    def __init__(self, config: Config):
        """初期化."""
        super().__init__(config)
        self.ai_client = None  # AI客户端将在运行时注入
        
    def get_generation_type(self) -> GenerationType:
        """生成タイプを返す."""
        return GenerationType.SCRIPT
        
    async def generate(self, request: GenerationRequest) -> GenerationResult:
        """台本を生成.
        
        Args:
            request: 生成リクエスト
            
        Returns:
            生成結果
        """
        if not self.validate_request(request):
            return GenerationResult(
                content="",
                metadata={},
                generation_type=self.get_generation_type(),
                success=False,
                error="Invalid request"
            )
            
        try:
            # プロンプトを構築
            prompt = self.build_prompt(request)
            
            # AI生成を実行
            script_content = await self._generate_script_content(prompt, request.options)
            
            # 結果の後処理
            processed_script = self._post_process_script(script_content, request)
            
            # メタデータ生成
            metadata = self.extract_metadata(request, processed_script)
            metadata.update(self._analyze_script(processed_script))
            
            return GenerationResult(
                content=processed_script,
                metadata=metadata,
                generation_type=self.get_generation_type(),
                success=True
            )
            
        except Exception as e:
            logger.error(f"Script generation failed: {e}")
            return GenerationResult(
                content="",
                metadata={},
                generation_type=self.get_generation_type(),
                success=False,
                error=str(e)
            )
            
    async def _generate_script_content(self, prompt: str, options: Dict[str, Any]) -> str:
        """AIを使用して台本コンテンツを生成."""
        if not self.ai_client:
            # AI客户端未设置时使用模拟生成
            return await self._simulate_script_generation(prompt, options)
            
        try:
            # AI呼び出し
            response = await self.ai_client.generate(
                prompt=prompt,
                max_tokens=options.get("max_tokens", 2000),
                temperature=options.get("temperature", 0.7)
            )
            
            if response and "content" in response:
                return response["content"]
            else:
                raise ValueError("Invalid AI response")
                
        except Exception as e:
            logger.warning(f"AI generation failed, using fallback: {e}")
            return await self._simulate_script_generation(prompt, options)
            
    async def _simulate_script_generation(self, prompt: str, options: Dict[str, Any]) -> str:
        """AI生成のシミュレーション（テスト用）."""
        # 簡単な台本テンプレートを生成
        title = options.get("title", "動画タイトル")
        
        script_template = f'''{{
    "title": "{title}の解説動画",
    "duration": "2:30",
    "sections": [
        {{
            "type": "introduction",
            "duration": "15",
            "script": "こんにちは！今日は{title}について分かりやすく解説していきます。この動画を見れば、{title}の基本的な内容を理解できるようになります。",
            "notes": "明るい口調で視聴者の関心を引く"
        }},
        {{
            "type": "main",
            "duration": "120",
            "script": "それでは本題に入りましょう。{title}について、重要なポイントを順番に説明していきます。まず最初に覚えておきたいのは...（ここで詳細な説明を展開）",
            "notes": "適切な間を取りながら、理解しやすいペースで説明"
        }},
        {{
            "type": "conclusion",
            "duration": "15",
            "script": "いかがでしたでしょうか？今日は{title}について解説させていただきました。この内容が皆さんのお役に立てれば嬉しいです。チャンネル登録もよろしくお願いします！",
            "notes": "視聴者への感謝とアクションの促進"
        }}
    ],
    "visual_elements": [
        "タイトルテロップ",
        "要点の文字表示",
        "図表・グラフ（必要に応じて）"
    ],
    "key_points": [
        "{title}の基本概念",
        "実践的な応用方法",
        "注意すべきポイント"
    ]
}}'''
        
        # 非同期処理のシミュレーション
        await asyncio.sleep(0.1)
        
        return script_template
        
    def _post_process_script(self, script_content: str, request: GenerationRequest) -> str:
        """台本の後処理."""
        # JSON形式の検証と修正
        import json
        import re
        
        try:
            # JSONブロックを抽出
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', script_content, re.DOTALL)
            if json_match:
                json_content = json_match.group(1)
            else:
                # JSONブロックがない場合は全体をJSONとして扱う
                json_content = script_content.strip()
                
            # JSON解析をテスト
            parsed = json.loads(json_content)
            
            # 必要なフィールドが存在するかチェック
            required_fields = ["title", "duration", "sections"]
            for field in required_fields:
                if field not in parsed:
                    logger.warning(f"Missing required field in script: {field}")
                    
            return json_content
            
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in script, returning raw content: {e}")
            return script_content
            
    def _analyze_script(self, script_content: str) -> Dict[str, Any]:
        """台本を分析してメタデータを生成."""
        import json
        
        try:
            # JSONとして解析
            script_data = json.loads(script_content)
            
            # 基本情報の抽出
            title = script_data.get("title", "")
            duration = script_data.get("duration", "")
            sections = script_data.get("sections", [])
            
            # 統計情報の計算
            total_script_length = sum(len(section.get("script", "")) for section in sections)
            section_count = len(sections)
            
            # セクションタイプの分布
            section_types = {}
            for section in sections:
                section_type = section.get("type", "unknown")
                section_types[section_type] = section_types.get(section_type, 0) + 1
                
            return {
                "script_title": title,
                "estimated_duration": duration,
                "section_count": section_count,
                "section_types": section_types,
                "total_script_length": total_script_length,
                "has_visual_elements": bool(script_data.get("visual_elements")),
                "key_point_count": len(script_data.get("key_points", []))
            }
            
        except json.JSONDecodeError:
            # JSON解析失敗時は基本的な統計のみ
            return {
                "script_length": len(script_content),
                "line_count": len(script_content.split('\n')),
                "word_count": len(script_content.split())
            }
            
    def set_ai_client(self, ai_client):
        """AI客户端を設定."""
        self.ai_client = ai_client 