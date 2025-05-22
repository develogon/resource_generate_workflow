import logging
import asyncio
from typing import Dict, Any, Optional, Union

from app.generators.base import BaseGenerator
from app.clients.claude import ClaudeAPIClient


class ScriptGenerator(BaseGenerator):
    """台本ジェネレータ

    AIを活用して台本を生成するジェネレータクラス
    """

    def __init__(self, api_key=None, model="claude-3-7-sonnet-20250219"):
        """初期化

        Args:
            api_key (str, optional): Claude API キー. デフォルトはNone (環境変数から取得)
            model (str, optional): 使用するモデル名. デフォルトは"claude-3-7-sonnet-20250219"
        """
        super().__init__()
        self.client = ClaudeAPIClient(api_key, model)

    def prepare_prompt(self, structure: Dict, article_content: str, **kwargs) -> str:
        """台本生成用プロンプトを準備する

        Args:
            structure (Dict): コンテンツ構造情報
            article_content (str): 記事内容
            **kwargs: 追加オプション

        Returns:
            str: 準備されたプロンプト
        """
        # システムプロンプト（役割設定）を取得
        system_prompt = self.get_system_prompt('script')
        
        # メッセージプロンプト（具体的な指示）を取得し、変数を置換
        message_prompt = self.get_message_prompt('script')
        message_prompt = message_prompt.replace('{{ARTICLE_CONTENT}}', article_content[:500] + '... （長いため省略）')
        
        # システムプロンプトとメッセージプロンプトを組み合わせる
        combined_prompt = f"""
# 台本作成

## システムプロンプト
{system_prompt}

## メッセージプロンプト
{message_prompt}

## 記事タイトル
{structure.get('title', 'タイトルなし')}
"""
        return combined_prompt

    def process_response(self, response: Union[Dict, str]) -> str:
        """API応答を処理する

        Args:
            response (Dict or str): Claude API 応答

        Returns:
            str: 生成された台本のMarkdown
            
        Raises:
            ValueError: コンテンツが空の場合
        """
        if isinstance(response, str):
            # すでにテキスト形式の場合はそのまま返す
            return response
            
        # API応答からテキストを抽出
        script_text = self.client.extract_content(response)
        
        if not script_text:
            self.logger.error("APIレスポンスからコンテンツを抽出できませんでした")
            raise ValueError("APIレスポンスからコンテンツを抽出できませんでした")
        
        return script_text

    async def generate(self, structure: Dict, article_content: str, output_path: Optional[str] = None) -> str:
        """台本を生成する

        Args:
            structure (Dict): コンテンツ構造情報
            article_content (str): 記事内容
            output_path (str, optional): 出力先パス. デフォルトはNone

        Returns:
            str: 生成された台本のMarkdown
        """
        # プロンプトを準備
        prompt = self.prepare_prompt(structure, article_content)
        
        # APIリクエストを準備
        request = self.client.prepare_request(prompt)
        
        # APIを呼び出し
        response = await self.client.call_api(request)
        
        # 応答を処理
        script = self.process_response(response)
        
        # 出力先が指定されていれば保存（実際の実装時はFileUtilsを使用）
        if output_path:
            # from app.utils.file import FileUtils
            # FileUtils.write_file(output_path, script)
            pass
            
        return script
        
    def generate_script(self, structure: Dict, article_content: str, output_path: Optional[str] = None) -> str:
        """台本を生成する（同期版）

        Args:
            structure (Dict): コンテンツ構造情報
            article_content (str): 記事内容
            output_path (str, optional): 出力先パス. デフォルトはNone

        Returns:
            str: 生成された台本のMarkdown
        """
        try:
            # 現在のイベントループを取得
            loop = asyncio.get_event_loop()
            
            # イベントループの状態に関わらず非同期メソッドを実行
            return loop.run_until_complete(self.generate(structure, article_content, output_path))
        except RuntimeError:
            # イベントループがない場合、新しく作成して実行
            return asyncio.run(self.generate(structure, article_content, output_path)) 