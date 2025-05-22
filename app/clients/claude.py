import os
import logging
import anthropic
from anthropic import Anthropic


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
        self.api_key = api_key or os.environ.get("CLAUDE_API_KEY")
        self.model = model
        self.logger = logging.getLogger(__name__)

        if not self.api_key:
            self.logger.warning("API キーが設定されていません。環境変数 CLAUDE_API_KEY を設定してください。")
        else:
            # APIキーの形式を確認し、必要に応じて修正
            if self.api_key.startswith('k-ant-'):
                # 新しいSDKはsk-で始まるAPIキーを期待している可能性があるため、ログに出力
                self.logger.warning("APIキーの形式が古い可能性があります。'k-ant-'で始まるキーは現在のSDKでは動作しない場合があります。")
                
            # APIキーが設定されているので、クライアントを初期化
            try:
                self.client = Anthropic(api_key=self.api_key)
                self.logger.info(f"Claude API クライアントを初期化しました。モデル: {self.model}")
            except Exception as e:
                self.logger.error(f"Claude API クライアントの初期化中にエラーが発生しました: {str(e)}")
                self.client = None

    def prepare_request(self, prompt, system_prompt=None, images=None):
        """リクエストを準備する

        Args:
            prompt (str): プロンプト
            system_prompt (str, optional): システムプロンプト. デフォルトはNone
            images (list, optional): 画像データのリスト. デフォルトはNone

        Returns:
            dict: API リクエスト辞書
        """
        messages = [
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        request = {
            "model": self.model,
            "messages": messages,
            "max_tokens": 4000
        }
        
        if system_prompt:
            request["system"] = system_prompt
            
        # 画像がある場合は追加処理
        if images:
            content_parts = []
            content_parts.append({"type": "text", "text": prompt})
            
            for image in images:
                if isinstance(image, str) and (image.startswith("http://") or image.startswith("https://")):
                    # URL形式の画像
                    content_parts.append({
                        "type": "image",
                        "source": {
                            "type": "url",
                            "url": image
                        }
                    })
                elif isinstance(image, bytes):
                    # バイナリ形式の画像
                    content_parts.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",  # デフォルトJPEG
                            "data": image.decode("utf-8") if isinstance(image, bytes) else image
                        }
                    })
            
            # メッセージのコンテンツを上書き
            request["messages"][0]["content"] = content_parts
        
        return request

    def call_api(self, request):
        """APIを呼び出す

        Args:
            request (dict): API リクエスト辞書

        Returns:
            dict: API 応答
        """
        if not self.api_key:
            self.logger.error("API キーが設定されていないため、APIを呼び出せません。")
            return None
            
        try:
            # メッセージを抽出
            messages = request.get("messages", [])
            # システムプロンプトを抽出
            system = request.get("system", None)
            
            # API呼び出しのパラメータを設定
            params = {
                "model": request["model"],
                "max_tokens": request.get("max_tokens", 4000),
                "messages": messages
            }
            
            # systemパラメータがある場合のみ追加
            if system is not None:
                params["system"] = system
            
            # Anthropicクライアントを使用してAPIを呼び出す
            response = self.client.messages.create(**params)
            
            return response
        except Exception as e:
            self.logger.exception(f"API 呼び出し中にエラーが発生しました: {str(e)}")
            return None

    def extract_content(self, response, content_type="text"):
        """レスポンスから特定タイプのコンテンツを抽出する

        Args:
            response (dict): API 応答
            content_type (str, optional): 抽出するコンテンツタイプ. デフォルトは"text"

        Returns:
            str: 抽出されたコンテンツ
        """
        if not response:
            return ""
            
        # Anthropic APIのレスポンス形式に合わせて変更
        if hasattr(response, 'content'):
            extracted_content = ""
            for content_block in response.content:
                if content_block.type == content_type:
                    extracted_content += content_block.text
                    
            return extracted_content
        
        return ""
        
    def analyze_structure(self, section_content, section_title=None, section_index=None):
        """セクションの構造を解析する

        Args:
            section_content (str): セクションのコンテンツ
            section_title (str, optional): セクションのタイトル. デフォルトはNone
            section_index (int, optional): セクションのインデックス. デフォルトはNone

        Returns:
            dict: 解析結果
        """
        prompt = f"""
        以下のセクション内容を解析し、その構造と主要な情報を抽出してください。

        セクションタイトル: {section_title or "不明"}
        
        セクション内容:
        ```
        {section_content}
        ```
        
        以下の形式でJSON形式で回答してください:
        
        1. 概要: このセクションの概要（100字以内）
        2. 主要なポイント: 箇条書きで3-5つ
        3. キーワード: 5-10個の重要な技術用語やキーワード
        4. 参考リンク: セクション内に含まれる外部リンク（URLとその内容の説明）
        """
        
        request = self.prepare_request(prompt)
        response = self.call_api(request)
        content = self.extract_content(response)
        
        return {
            "section_title": section_title,
            "section_index": section_index,
            "analysis": content,
            "success": True if content else False
        } 