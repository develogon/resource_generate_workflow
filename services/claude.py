"""
Claude APIとの通信を担当するサービスモジュール。
Anthropic社のClaude APIを使用したテキスト生成機能を提供する。
"""
import re
import time
import requests
from typing import Dict, Any, List, Optional, Union

from utils.exceptions import APIException
from services.client import APIClient


class ClaudeService(APIClient):
    """
    Claude APIとの通信を担当するサービスクラス。
    APIClientを継承し、Claude固有の機能を実装する。
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        ClaudeServiceを初期化する。
        
        Args:
            config (Dict[str, Any]): 設定情報
                - claude.api_key: Claude API Key
                - claude.model: 使用するモデル名
                - claude.max_tokens: 最大トークン数
                - claude.temperature: 温度パラメータ
                - claude.timeout: タイムアウト秒数
                - claude.retry_count: リトライ回数
                - claude.retry_delay: リトライ間隔（秒）
        """
        super().__init__(config)
        
        # 設定から必要なパラメータを取得
        claude_config = config.get("claude", {})
        self.api_key = claude_config.get("api_key")
        self.model = claude_config.get("model", "claude-3-7-sonnet-20250219")
        self.max_tokens = claude_config.get("max_tokens", 4000)
        self.temperature = claude_config.get("temperature", 0.7)
        self.timeout = claude_config.get("timeout", 30)
        self.retry_count = claude_config.get("retry_count", 3)
        self.retry_delay = claude_config.get("retry_delay", 1)
        
        # API設定
        self.base_url = "https://api.anthropic.com/v1"
        self.headers = {
            "x-api-key": self.api_key,
            "content-type": "application/json",
            "anthropic-version": "2023-06-01"
        }
    
    def generate_content(
        self, 
        prompt: str, 
        images: Optional[List[str]] = None,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Claude APIを使用してコンテンツを生成する。
        
        Args:
            prompt (str): 生成プロンプト
            images (List[str], optional): Base64エンコードされた画像データのリスト
                "data:image/jpeg;base64,..."または"data:image/png;base64,..."形式
            system_prompt (str, optional): システムプロンプト
        
        Returns:
            Dict[str, Any]: APIレスポンス
                - content: 生成されたテキスト
                - id: レスポンスID
        
        Raises:
            APIException: API呼び出しに失敗した場合
        """
        # メッセージの構築
        if images and len(images) > 0:
            # 画像付きメッセージの構築
            message_content = []
            
            # テキストコンテンツ
            message_content.append({
                "type": "text",
                "text": prompt
            })
            
            # 画像コンテンツ
            for image in images:
                # Base64エンコードデータの抽出 (data:image/jpeg;base64,xxxxx の形式から)
                match = re.match(r'data:image/([^;]+);base64,(.+)', image)
                if match:
                    image_type, image_data = match.groups()
                    message_content.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": f"image/{image_type}",
                            "data": image_data
                        }
                    })
            
            messages = [{"role": "user", "content": message_content}]
        else:
            # テキストのみのメッセージ
            messages = [{"role": "user", "content": prompt}]
        
        # システムプロンプトが提供されている場合は追加
        request_body = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature
        }
        
        # システムプロンプトの追加
        if system_prompt:
            request_body["system"] = system_prompt
        
        request_body["messages"] = messages
        
        # リトライロジック
        for attempt in range(self.retry_count):
            try:
                # APIリクエスト
                response = requests.post(
                    f"{self.base_url}/messages",
                    headers=self.headers,
                    json=request_body,
                    timeout=self.timeout
                )
                
                # ステータスコードによる分岐
                if response.status_code == 200:
                    # 成功レスポンスの処理
                    api_response = response.json()
                    self.validate_response(api_response)
                    
                    # レスポンスからテキストを抽出
                    content = ""
                    for item in api_response.get("content", []):
                        if item.get("type") == "text":
                            content += item.get("text", "")
                    
                    return {
                        "content": content,
                        "id": api_response.get("id")
                    }
                
                elif response.status_code == 429:
                    # レート制限の場合は待機して再試行
                    retry_after = int(response.headers.get("retry-after", self.retry_delay))
                    time.sleep(retry_after)
                    continue
                
                else:
                    # その他のエラー
                    error_data = response.json()
                    raise APIException(
                        f"Claude API error: {error_data.get('error', {}).get('message', 'Unknown error')}",
                        service_name="ClaudeService",
                        status_code=response.status_code
                    )
            
            except Exception as e:
                # 最後の試行で失敗した場合は例外を発生
                if attempt == self.retry_count - 1:
                    if isinstance(e, APIException):
                        raise e
                    else:
                        raise APIException(
                            f"Claude API通信エラー: {str(e)}",
                            service_name="ClaudeService",
                            inner_exception=e
                        )
                
                # 一時的なエラーの場合は待機して再試行
                time.sleep(self.retry_delay)
        
        # 通常ここには到達しないが、念のため
        raise APIException(
            "Claude APIへの接続に失敗しました。",
            service_name="ClaudeService"
        )
    
    def extract_yaml(self, response: str) -> Optional[str]:
        """
        APIレスポンスからYAMLコンテンツを抽出する。
        
        Args:
            response (str): APIレスポンスのテキスト
        
        Returns:
            Optional[str]: 抽出されたYAMLコンテンツ（見つからない場合はNone）
        """
        # YAMLブロックの抽出 (```yaml ... ``` の形式)
        yaml_pattern = r'```yaml\s*([\s\S]+?)\s*```'
        match = re.search(yaml_pattern, response)
        
        if match:
            # 取得したYAMLを整形（テスト用）
            yaml_content = match.group(1)
            # 行頭の余分な空白を削除
            lines = yaml_content.splitlines()
            cleaned_lines = []
            
            # 各行の先頭のインデントを除去
            min_indent = float('inf')
            for line in lines:
                if line.strip():  # 空行でない場合
                    indent = len(line) - len(line.lstrip())
                    min_indent = min(min_indent, indent)
            
            # 最小インデントがある場合、それを各行から除去
            if min_indent < float('inf'):
                for line in lines:
                    if line.strip():  # 空行でない場合
                        cleaned_lines.append(line[min_indent:])
                    else:
                        cleaned_lines.append(line)
            else:
                cleaned_lines = lines
            
            return "\n".join(cleaned_lines)
        
        return None
    
    def extract_markdown(self, response: str) -> str:
        """
        APIレスポンスからMarkdownコンテンツを抽出（または整形）する。
        
        Args:
            response (str): APIレスポンスのテキスト
        
        Returns:
            str: 抽出または整形されたMarkdownコンテンツ
        """
        # すでにMarkdown形式の場合はそのまま返す
        return response
    
    def handle_rate_limit(self) -> None:
        """
        レート制限対応のためのユーティリティメソッド。
        一定時間待機する。
        """
        time.sleep(self.retry_delay)
    
    def validate_response(self, response: Dict[str, Any]) -> bool:
        """
        APIレスポンスが有効かどうかを検証する。
        
        Args:
            response (Dict[str, Any]): APIレスポンス
        
        Returns:
            bool: レスポンスが有効な場合はTrue
            
        Raises:
            ValueError: レスポンスが無効な場合
        """
        if not response:
            raise ValueError("Empty response from Claude API")
        
        if "content" not in response:
            raise ValueError("Missing 'content' field in Claude API response")
        
        return True 