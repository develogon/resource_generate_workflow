import os
import logging
import re
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, Union

from app.generators.base import BaseGenerator
from app.clients.claude import ClaudeAPIClient


class DescriptionGenerator(BaseGenerator):
    """説明文ジェネレータ

    AIを活用して記事の説明文を生成するジェネレータクラス
    """

    def __init__(self, api_key=None, model="claude-3-7-sonnet-20250219"):
        """初期化

        Args:
            api_key (str, optional): Claude API キー. デフォルトはNone (環境変数から取得)
            model (str, optional): 使用するモデル名. デフォルトは"claude-3-7-sonnet-20250219"
        """
        super().__init__()
        self.client = ClaudeAPIClient(api_key, model)
        self.logger = logging.getLogger(__name__)

    def prepare_prompt(self, structure_md: str, article_content: str, **kwargs) -> str:
        """説明文生成用プロンプトを準備する

        Args:
            structure_md (str): 記事の構造（Markdown形式）
            article_content (str): 記事内容
            **kwargs: 追加オプション

        Returns:
            str: 準備されたプロンプト
        """
        # オプションパラメータの取得
        min_length = kwargs.get('min_length', 300)
        max_length = kwargs.get('max_length', 500)
        
        # システムプロンプト（役割設定）を取得
        system_prompt = self.get_system_prompt('description')
        
        # メッセージプロンプト（具体的な指示）を取得し、変数を置換
        message_prompt = self.get_message_prompt('description')
        message_prompt = message_prompt.replace('{{STRUCTURE_MD}}', structure_md[:300] + '... （省略）')
        message_prompt = message_prompt.replace('{{ARTICLE_CONTENT}}', article_content[:500] + '... （省略）')
        message_prompt = message_prompt.replace('{{MIN_LENGTH}}', str(min_length))
        message_prompt = message_prompt.replace('{{MAX_LENGTH}}', str(max_length))
        
        # システムプロンプトとメッセージプロンプトを組み合わせる
        combined_prompt = f"""
# 説明文作成

## システムプロンプト
{system_prompt}

## メッセージプロンプト
{message_prompt}
"""
        return combined_prompt

    def process_response(self, response: Union[Dict, str]) -> str:
        """API応答を処理する

        Args:
            response (Dict or str): Claude API 応答

        Returns:
            str: 生成された説明文
            
        Raises:
            ValueError: コンテンツが空の場合
        """
        if isinstance(response, str):
            # すでにテキスト形式の場合はそのまま返す
            return response
            
        # API応答からテキストを抽出
        description_text = self.client.extract_content(response)
        
        if not description_text:
            self.logger.error("APIレスポンスからコンテンツを抽出できませんでした")
            raise ValueError("APIレスポンスからコンテンツを抽出できませんでした")
        
        return description_text

    def append_template(self, description: str) -> str:
        """説明文にテンプレート要素を追加する

        Args:
            description (str): 生成された説明文

        Returns:
            str: テンプレート要素が追加された説明文
        """
        # テンプレートファイルの読み込み
        try:
            # ベースディレクトリの取得
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            template_path = os.path.join(base_dir, 'templates', 'description', 'footer.txt')
            
            with open(template_path, 'r', encoding='utf-8') as f:
                template = f.read()
                
            # 現在の年を取得
            current_year = datetime.now().year
            
            # テンプレートの変数を置換
            template = template.replace('{{year}}', str(current_year))
            
            # 説明文にテンプレートを追加
            return f"{description}\n\n---\n\n{template}"
                
        except FileNotFoundError:
            self.logger.warning(f"テンプレートファイルが見つかりません: {template_path}")
            # テンプレートファイルがない場合は簡易的なフッターを追加
            return f"{description}\n\n---\n\n© {datetime.now().year} All Rights Reserved."

    async def generate(self, structure: Dict, structure_md: str, article_content: str, 
                      min_length: int = 300, max_length: int = 500,
                      output_path: Optional[str] = None, 
                      append_footer: bool = True) -> str:
        """説明文を生成する

        Args:
            structure (Dict): コンテンツ構造情報
            structure_md (str): 記事の構造（Markdown形式）
            article_content (str): 記事内容
            min_length (int, optional): 最小文字数. デフォルトは300
            max_length (int, optional): 最大文字数. デフォルトは500
            output_path (str, optional): 出力先パス. デフォルトはNone
                                         Noneの場合はget_output_path()で自動生成
            append_footer (bool, optional): フッターを追加するかどうか. デフォルトはTrue

        Returns:
            str: 生成された説明文
        """
        # 出力パスが指定されていない場合は自動生成
        if output_path is None:
            # structureからlevelを判断
            if 'section_name' in structure:
                level = 'section'
            elif 'chapter_name' in structure:
                level = 'chapter'
            else:
                level = 'title'
            
            output_path = self.get_output_path(structure, level, 'description.md')
        
        # プロンプトを準備
        prompt = self.prepare_prompt(
            structure_md, 
            article_content, 
            min_length=min_length,
            max_length=max_length
        )
        
        # APIリクエストを準備
        request = self.client.prepare_request(prompt)
        
        # APIを呼び出し（同期関数なのでawaitは使わない）
        response = self.client.call_api(request)
        
        # 応答を処理
        description = self.process_response(response)
        
        # フッターの追加（オプション）
        if append_footer:
            description = self.append_template(description)
        
        # 出力先が指定されていれば保存（実際の実装時はFileUtilsを使用）
        if output_path:
            # ディレクトリが存在しない場合は作成
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            pass
            
        return description
        
    def generate_description(self, structure: Dict, structure_md: str, article_content: str,
                            min_length: int = 300, max_length: int = 500,
                            output_path: Optional[str] = None,
                            append_footer: bool = True) -> str:
        """説明文を生成する（同期版）

        Args:
            structure (Dict): コンテンツ構造情報
            structure_md (str): 記事の構造（Markdown形式）
            article_content (str): 記事内容
            min_length (int, optional): 最小文字数. デフォルトは300
            max_length (int, optional): 最大文字数. デフォルトは500
            output_path (str, optional): 出力先パス. デフォルトはNone
                                         Noneの場合はget_output_path()で自動生成
            append_footer (bool, optional): フッターを追加するかどうか. デフォルトはTrue

        Returns:
            str: 生成された説明文
        """
        try:
            # 現在のイベントループを取得
            loop = asyncio.get_event_loop()
            
            # イベントループの状態に関わらず非同期メソッドを実行
            return loop.run_until_complete(
                self.generate(structure, structure_md, article_content, min_length, max_length, output_path, append_footer)
            )
        except RuntimeError:
            # イベントループがない場合、新しく作成して実行
            return asyncio.run(
                self.generate(structure, structure_md, article_content, min_length, max_length, output_path, append_footer)
            ) 