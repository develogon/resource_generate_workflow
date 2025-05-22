import os
import logging
from typing import Dict, Any, Optional, List, Union


class BaseGenerator:
    """ジェネレータの基底クラス

    AIを活用したコンテンツ生成の基底クラスです。
    各種ジェネレータはこのクラスを継承して実装します。
    """

    def __init__(self):
        """初期化"""
        self.logger = logging.getLogger(__name__)
        self.client = None  # 継承クラスで初期化される

    def prepare_prompt(self, structure: Dict, additional_context: Optional[Dict] = None) -> str:
        """プロンプトを準備する

        Args:
            structure (Dict): 構造情報
            additional_context (Dict, optional): 追加コンテキスト情報. デフォルトはNone

        Returns:
            str: 準備されたプロンプト
        """
        prompt = f"# {structure.get('title', 'タイトルなし')}\n\n"
        
        if 'sections' in structure:
            for section in structure['sections']:
                prompt += f"## {section.get('title', 'セクションタイトルなし')}\n\n"
                
                if 'paragraphs' in section:
                    for paragraph in section['paragraphs']:
                        content = paragraph.get('content', '')
                        prompt += f"{content}\n\n"
        
        if additional_context:
            prompt += f"\n追加コンテキスト：{additional_context}\n"
            
        return prompt

    def process_response(self, response: Union[Dict, str]) -> str:
        """API応答を処理する

        Args:
            response (Dict or str): API 応答

        Returns:
            str: 処理された応答テキスト
        """
        if isinstance(response, str):
            # すでにテキスト形式の場合はそのまま返す
            return response
            
        # API応答からテキストを抽出
        if isinstance(response, dict) and 'content' in response:
            if isinstance(response['content'], list):
                for item in response['content']:
                    if item.get('type') == 'text':
                        return item.get('text', '')
        
        return "レスポンス処理エラー"

    async def generate(self, structure: Dict, additional_context: Optional[Dict] = None, output_path: Optional[str] = None) -> str:
        """コンテンツを生成する

        Args:
            structure (Dict): 構造情報
            additional_context (Dict, optional): 追加コンテキスト情報. デフォルトはNone
            output_path (str, optional): 出力先パス. デフォルトはNone

        Returns:
            str: 生成されたコンテンツ
        """
        if not self.client:
            raise ValueError("APIクライアントが設定されていません")
            
        # プロンプトを準備
        prompt = self.prepare_prompt(structure, additional_context)
        
        # APIリクエストを準備
        request = self.client.prepare_request(prompt)
        
        # APIを呼び出し
        response = await self.client.call_api(request)
        
        # 応答を処理
        content = self.process_response(response)
        
        # 出力先が指定されていれば保存
        if output_path:
            # from app.utils.file import FileUtils
            # FileUtils.write_file(output_path, content)
            pass
            
        return content

    def load_prompt_template(self, prompt_type: str, component: str) -> str:
        """プロンプトテンプレートを読み込む

        Args:
            prompt_type (str): プロンプトタイプ ('system' または 'message')
            component (str): コンポーネント名 (例: 'script', 'article', 'tweet', etc.)

        Returns:
            str: テンプレート文字列
        """
        try:
            # ベースディレクトリの取得
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            template_path = os.path.join(base_dir, 'prompts', prompt_type, f"{component}.md")
            
            with open(template_path, 'r', encoding='utf-8') as f:
                return f.read()
                
        except FileNotFoundError:
            self.logger.warning(f"プロンプトファイルが見つかりません: {template_path}")
            return f"# {prompt_type}/{component}"

    def get_system_prompt(self, component: str) -> str:
        """システムプロンプトを取得する

        Args:
            component (str): コンポーネント名 (例: 'script', 'article', 'tweet', etc.)

        Returns:
            str: システムプロンプト文字列
        """
        return self.load_prompt_template('system', component)

    def get_message_prompt(self, component: str) -> str:
        """メッセージプロンプトを取得する

        Args:
            component (str): コンポーネント名 (例: 'script', 'article', 'tweet', etc.)

        Returns:
            str: メッセージプロンプト文字列
        """
        return self.load_prompt_template('message', component) 