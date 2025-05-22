import os
import logging


class ClaudeAPIClient:
    """Claude API連携クライアント

    Claude APIを使用したテキスト生成を行うクライアントクラスです。
    """

    def __init__(self, api_key=None, model="claude-3-7-sonnet-20250219"):
        """初期化

        Args:
            api_key (str, optional): Claude API キー. デフォルトはNone (環境変数から取得)
            model (str, optional): 使用するモデル名. デフォルトは"claude-3-7-sonnet-20250219"
        """
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = model
        self.logger = logging.getLogger(__name__)

        if not self.api_key:
            self.logger.warning("API キーが設定されていません。環境変数 ANTHROPIC_API_KEY を設定してください。")

    def prepare_request(self, prompt, images=None):
        """リクエストを準備する

        Args:
            prompt (str): プロンプト
            images (list, optional): 画像データのリスト. デフォルトはNone

        Returns:
            dict: API リクエスト辞書
        """
        request = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 4000
        }
        
        # 画像がある場合は追加処理（実装が必要）
        # ...
        
        return request

    async def call_api(self, request):
        """APIを呼び出す

        Args:
            request (dict): API リクエスト辞書

        Returns:
            dict: API 応答
        """
        # この部分は実際の実装時に外部ライブラリを使用して実装
        # 現時点ではモックレスポンスを返す
        mock_response = {
            "content": [
                {
                    "type": "text",
                    "text": "これはモックレスポンスです。実際の実装では、外部APIを呼び出します。"
                }
            ]
        }
        return mock_response

    def extract_content(self, response, content_type="text"):
        """レスポンスから特定タイプのコンテンツを抽出する

        Args:
            response (dict): API 応答
            content_type (str, optional): 抽出するコンテンツタイプ. デフォルトは"text"

        Returns:
            str: 抽出されたコンテンツ
        """
        if not response or "content" not in response:
            return ""
            
        extracted_content = ""
        for content in response["content"]:
            if content.get("type") == content_type:
                extracted_content += content.get("text", "")
                
        return extracted_content 