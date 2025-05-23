"""プロンプトとテンプレートローダー."""

import os
from pathlib import Path
from typing import Dict, Optional, Any
import yaml
import logging

logger = logging.getLogger(__name__)


class PromptLoader:
    """プロンプトとテンプレートを読み込むローダー."""
    
    def __init__(self, base_path: Optional[Path] = None):
        """初期化.
        
        Args:
            base_path: ベースパス。Noneの場合は自動検出
        """
        if base_path is None:
            # src/utils/prompt_loader.py から ../../ を遡ってプロジェクトルートを見つける
            current_file = Path(__file__)
            self.base_path = current_file.parent.parent.parent
        else:
            self.base_path = base_path
            
        self.prompts_dir = self.base_path / "prompts"
        self.templates_dir = self.base_path / "templates"
        
        # キャッシュ
        self._system_prompts_cache: Dict[str, str] = {}
        self._message_prompts_cache: Dict[str, str] = {}
        self._templates_cache: Dict[str, Any] = {}
        
    def load_system_prompt(self, prompt_name: str) -> str:
        """システムプロンプトを読み込み.
        
        Args:
            prompt_name: プロンプト名（拡張子なし）
            
        Returns:
            プロンプト内容
        """
        if prompt_name in self._system_prompts_cache:
            return self._system_prompts_cache[prompt_name]
            
        prompt_path = self.prompts_dir / "system" / f"{prompt_name}.md"
        
        if not prompt_path.exists():
            logger.warning(f"System prompt not found: {prompt_path}")
            return ""
            
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                
            self._system_prompts_cache[prompt_name] = content
            return content
            
        except Exception as e:
            logger.error(f"Failed to load system prompt {prompt_name}: {e}")
            return ""
            
    def load_message_prompt(self, prompt_name: str) -> str:
        """メッセージプロンプトを読み込み.
        
        Args:
            prompt_name: プロンプト名（拡張子なし）
            
        Returns:
            プロンプト内容
        """
        if prompt_name in self._message_prompts_cache:
            return self._message_prompts_cache[prompt_name]
            
        prompt_path = self.prompts_dir / "message" / f"{prompt_name}.md"
        
        if not prompt_path.exists():
            logger.warning(f"Message prompt not found: {prompt_path}")
            return ""
            
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                
            self._message_prompts_cache[prompt_name] = content
            return content
            
        except Exception as e:
            logger.error(f"Failed to load message prompt {prompt_name}: {e}")
            return ""
            
    def load_template(self, template_name: str) -> Any:
        """テンプレートを読み込み.
        
        Args:
            template_name: テンプレート名（拡張子なし）
            
        Returns:
            テンプレート内容（YAML/JSONの場合は辞書、Markdownの場合は文字列）
        """
        if template_name in self._templates_cache:
            return self._templates_cache[template_name]
            
        # 複数の拡張子を試す
        extensions = ['.yml', '.yaml', '.json', '.md']
        template_path = None
        
        for ext in extensions:
            candidate_path = self.templates_dir / f"{template_name}{ext}"
            if candidate_path.exists():
                template_path = candidate_path
                break
                
        if template_path is None:
            logger.warning(f"Template not found: {template_name}")
            return {}
            
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # ファイル拡張子に応じて処理
            if template_path.suffix in ['.yml', '.yaml']:
                parsed_content = yaml.safe_load(content)
            elif template_path.suffix == '.json':
                import json
                parsed_content = json.loads(content)
            else:
                parsed_content = content.strip()
                
            self._templates_cache[template_name] = parsed_content
            return parsed_content
            
        except Exception as e:
            logger.error(f"Failed to load template {template_name}: {e}")
            return {} if template_path.suffix in ['.yml', '.yaml', '.json'] else ""
            
    def format_prompt(self, prompt_template: str, **kwargs) -> str:
        """プロンプトテンプレートに変数を埋め込み.
        
        Args:
            prompt_template: プロンプトテンプレート
            **kwargs: テンプレート変数
            
        Returns:
            フォーマット済みプロンプト
        """
        try:
            # {{変数名}} 形式の置換
            formatted = prompt_template
            for key, value in kwargs.items():
                placeholder = f"{{{{{key}}}}}"
                formatted = formatted.replace(placeholder, str(value))
                
            return formatted
            
        except Exception as e:
            logger.error(f"Failed to format prompt: {e}")
            return prompt_template
            
    def clear_cache(self):
        """キャッシュをクリア."""
        self._system_prompts_cache.clear()
        self._message_prompts_cache.clear()
        self._templates_cache.clear()
        
    def get_combined_prompt(self, prompt_type: str, **kwargs) -> str:
        """システムプロンプトとメッセージプロンプトを組み合わせ.
        
        Args:
            prompt_type: プロンプトタイプ（article, script, tweet等）
            **kwargs: テンプレート変数
            
        Returns:
            組み合わせ済みプロンプト
        """
        system_prompt = self.load_system_prompt(prompt_type)
        message_prompt = self.load_message_prompt(prompt_type)
        
        # メッセージプロンプトに変数を埋め込み
        formatted_message = self.format_prompt(message_prompt, **kwargs)
        
        # システムプロンプトとメッセージプロンプトを組み合わせ
        if system_prompt and formatted_message:
            return f"{system_prompt}\n\n{formatted_message}"
        elif system_prompt:
            return system_prompt
        elif formatted_message:
            return formatted_message
        else:
            return ""


# グローバルインスタンス
_prompt_loader = None


def get_prompt_loader() -> PromptLoader:
    """グローバルプロンプトローダーを取得."""
    global _prompt_loader
    if _prompt_loader is None:
        _prompt_loader = PromptLoader()
    return _prompt_loader