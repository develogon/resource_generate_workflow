import os
import logging
from typing import Dict, List, Optional, Any


class SlackClient:
    """Slack通知クライアント

    Slackへの通知を行うクライアントクラスです。
    """

    def __init__(self, token=None, channel=None):
        """初期化

        Args:
            token (str, optional): Slack API トークン. デフォルトはNone (環境変数から取得)
            channel (str, optional): 送信先チャンネル. デフォルトはNone (環境変数から取得)
        """
        self.token = token or os.environ.get("SLACK_API_TOKEN")
        self.channel = channel or os.environ.get("SLACK_CHANNEL")
        self.logger = logging.getLogger(__name__)

        if not self.token:
            self.logger.warning("Slack API トークンが設定されていません。環境変数 SLACK_API_TOKEN を設定してください。")
        if not self.channel:
            self.logger.warning("Slackチャンネルが設定されていません。環境変数 SLACK_CHANNEL を設定してください。")

    def send_notification(self, message: str, attachments: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """通知送信

        Args:
            message (str): 通知メッセージ
            attachments (List[Dict], optional): 添付ファイル情報のリスト. デフォルトはNone

        Returns:
            Dict[str, Any]: 送信結果
        """
        # 実際の実装時はSlack APIを呼び出す
        # 現時点ではモックレスポンスを返す
        self.logger.info(f"Slack通知送信: channel={self.channel}, message={message[:50]}...")
        
        return {
            "ok": True,
            "message": message,
            "attachments": attachments,
            "channel": self.channel,
            "ts": "1234567890.123456"
        }

    def send_error_alert(self, error: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """エラーアラート送信

        Args:
            error (str): エラーメッセージ
            context (Dict, optional): エラーのコンテキスト情報. デフォルトはNone

        Returns:
            Dict[str, Any]: 送信結果
        """
        # 実際の実装時はSlack APIを呼び出す
        # 現時点ではモックレスポンスを返す
        if context is None:
            context = {}
            
        # エラーメッセージの整形
        error_message = f"🚨 エラー発生: {error}"
        
        # エラー詳細のアタッチメント作成
        attachments = [{
            "title": "エラー詳細",
            "text": "\n".join([f"{k}: {v}" for k, v in context.items()]),
            "color": "#ff0000"
        }]
        
        self.logger.error(f"Slackエラーアラート送信: error={error}")
        
        return {
            "ok": True,
            "error": error,
            "context": context,
            "channel": self.channel,
            "ts": "1234567890.123456"
        }

    def upload_file(self, file_content: bytes, filename: str, title: Optional[str] = None, initial_comment: Optional[str] = None) -> Dict[str, Any]:
        """ファイルアップロード

        Args:
            file_content (bytes): アップロードするファイルの内容
            filename (str): ファイル名
            title (str, optional): ファイルのタイトル. デフォルトはNone (ファイル名を使用)
            initial_comment (str, optional): 初期コメント. デフォルトはNone

        Returns:
            Dict[str, Any]: アップロード結果
        """
        # 実際の実装時はSlack APIを呼び出す
        # 現時点ではモックレスポンスを返す
        if title is None:
            title = filename
            
        self.logger.info(f"Slackファイルアップロード: filename={filename}, title={title}")
        
        return {
            "ok": True,
            "file": {
                "id": "F01234567",
                "name": filename,
                "title": title,
                "url": f"https://slack.com/files/U1234567/{filename}"
            },
            "channel": self.channel,
            "ts": "1234567890.123456"
        } 