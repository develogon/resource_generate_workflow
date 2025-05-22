import json
import logging
import asyncio
import re
from typing import Dict, Any, Optional, Union, List

from app.generators.base import BaseGenerator
from app.clients.claude import ClaudeAPIClient


class ScriptJsonGenerator(BaseGenerator):
    """台本JSONジェネレータ

    Markdown形式の台本をJSON形式に変換するジェネレータクラス
    """

    def __init__(self, api_key=None, model="claude-3-7-sonnet-20250219"):
        """初期化

        Args:
            api_key (str, optional): Claude API キー. デフォルトはNone (環境変数から取得)
            model (str, optional): 使用するモデル名. デフォルトは"claude-3-7-sonnet-20250219"
        """
        super().__init__()
        self.client = ClaudeAPIClient(api_key, model)

    def prepare_prompt(self, script_content: str, **kwargs) -> str:
        """台本JSON変換用プロンプトを準備する

        Args:
            script_content (str): Markdown形式の台本内容
            **kwargs: 追加オプション

        Returns:
            str: 準備されたプロンプト
        """
        # システムプロンプト（役割設定）を取得
        system_prompt = self.get_system_prompt('script_json')
        
        # メッセージプロンプト（具体的な指示）を取得し、変数を置換
        message_prompt = self.get_message_prompt('script_json')
        message_prompt = message_prompt.replace('{{SCRIPT_CONTENT}}', script_content)
        
        # システムプロンプトとメッセージプロンプトを組み合わせる
        combined_prompt = f"""
# 台本のJSON変換

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
            str: 処理されたJSON文字列

        Raises:
            ValueError: コンテンツが空、またはJSON形式でない場合
        """
        if isinstance(response, str):
            # すでにテキスト形式の場合はそのまま返す
            return response
            
        # API応答からテキストを抽出
        content = self.client.extract_content(response)
        
        if not content:
            self.logger.error("APIレスポンスからコンテンツを抽出できませんでした")
            raise ValueError("APIレスポンスからコンテンツを抽出できませんでした")
        
        # JSON部分を抽出
        json_content = self._extract_json(content)
        
        if not json_content:
            self.logger.error("レスポンスからJSON形式を抽出できませんでした")
            raise ValueError("レスポンスからJSON形式を抽出できませんでした")
            
        # JSONの検証と成形
        try:
            # 文字列をJSONとしてパース
            json_obj = json.loads(json_content)
            # インデント付きで整形して返す
            return json.dumps(json_obj, ensure_ascii=False, indent=2)
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON解析エラー: {e}")
            raise ValueError(f"JSON解析エラー: {e}")

    def _extract_json(self, content: str) -> str:
        """テキストからJSON部分を抽出する

        Args:
            content (str): 抽出元テキスト

        Returns:
            str: 抽出されたJSON文字列
        """
        # JSONのコードブロックを探す
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content)
        if json_match:
            return json_match.group(1).strip()
            
        # JSON形式のテキストを探す（{ で始まり } で終わる）
        json_match = re.search(r"(\{[\s\S]*\})", content)
        if json_match:
            return json_match.group(1).strip()
            
        return ""

    async def generate(self, script_content: str, output_path: Optional[str] = None) -> str:
        """台本JSONを生成する

        Args:
            script_content (str): Markdown形式の台本内容
            output_path (str, optional): 出力先パス. デフォルトはNone

        Returns:
            str: 生成されたJSON文字列
        """
        # プロンプトを準備
        prompt = self.prepare_prompt(script_content)
        
        # APIリクエストを準備
        request = self.client.prepare_request(prompt)
        
        # APIを呼び出し
        response = await self.client.call_api(request)
        
        # 応答を処理
        json_content = self.process_response(response)
        
        # 出力先が指定されていれば保存（実際の実装時はFileUtilsを使用）
        if output_path:
            # from app.utils.file import FileUtils
            # FileUtils.write_file(output_path, json_content)
            pass
            
        return json_content
        
    def generate_script_json(self, script_content: str, output_path: Optional[str] = None) -> str:
        """台本JSONを生成する（同期版）

        Args:
            script_content (str): Markdown形式の台本内容
            output_path (str, optional): 出力先パス. デフォルトはNone

        Returns:
            str: 生成されたJSON文字列
        """
        try:
            # 現在のイベントループを取得
            loop = asyncio.get_event_loop()
            
            # イベントループの状態に関わらず非同期メソッドを実行
            return loop.run_until_complete(self.generate(script_content, output_path))
        except RuntimeError:
            # イベントループがない場合、新しく作成して実行
            return asyncio.run(self.generate(script_content, output_path)) 