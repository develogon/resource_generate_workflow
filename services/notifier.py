"""
Slack通知を担当するサービスモジュール。
slack_sdkを使用してSlackへの通知を行う。
"""
import slack_sdk
from typing import Dict, Any, Optional, Union

from utils.exceptions import APIException
from services.client import APIClient


class NotifierService(APIClient):
    """
    Slack通知を担当するサービスクラス。
    APIClientを継承し、Slack固有の機能を実装する。
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        NotifierServiceを初期化する。
        
        Args:
            config (Dict[str, Any]): 設定情報
                - slack.token: Slack API Token
                - slack.channel: 通知先チャンネル名
                - slack.username: 通知時のユーザー名
                - slack.icon_emoji: 通知時のアイコン
        """
        super().__init__(config)
        
        # 設定から必要なパラメータを取得
        slack_config = config.get("slack", {})
        self._token = slack_config.get("token")
        self._channel = slack_config.get("channel")
        self._username = slack_config.get("username", "通知Bot")
        self._icon_emoji = slack_config.get("icon_emoji", ":bell:")
        
        # Slackクライアント初期化
        self._slack_client = slack_sdk.WebClient(token=self._token)
    
    def send_message(
        self, 
        message: str, 
        channel: Optional[str] = None, 
        username: Optional[str] = None,
        icon_emoji: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        基本的なSlackメッセージを送信する。
        
        Args:
            message (str): 送信するメッセージ
            channel (str, optional): 送信先チャンネル. デフォルトはNone (self._channelを使用)
            username (str, optional): 表示ユーザー名. デフォルトはNone (self._usernameを使用)
            icon_emoji (str, optional): アイコン絵文字. デフォルトはNone (self._icon_emojiを使用)
        
        Returns:
            Optional[Dict[str, Any]]: Slack APIレスポンス (エラー時はNone)
        """
        target_channel = channel or self._channel
        target_username = username or self._username
        target_icon_emoji = icon_emoji or self._icon_emoji
        
        try:
            # Slackメッセージを送信
            response = self._slack_client.chat_postMessage(
                channel=target_channel,
                text=message,
                username=target_username,
                icon_emoji=target_icon_emoji
            )
            
            return response
        
        except Exception as e:
            # エラーログ出力
            print(f"Slack通知エラー: {str(e)}")
            return None
    
    def send_success(
        self, 
        message: str, 
        channel: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        成功通知を送信する。
        
        Args:
            message (str): 成功メッセージ
            channel (str, optional): 送信先チャンネル. デフォルトはNone (self._channelを使用)
        
        Returns:
            Optional[Dict[str, Any]]: Slack APIレスポンス (エラー時はNone)
        """
        # 成功アイコンを追加
        formatted_message = f":white_check_mark: *成功*: {message}"
        
        return self.send_message(
            message=formatted_message,
            channel=channel,
            icon_emoji=":white_check_mark:"
        )
    
    def send_error(
        self, 
        error_message: str, 
        details: Optional[str] = None,
        channel: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        エラー通知を送信する。
        
        Args:
            error_message (str): エラーメッセージ
            details (str, optional): エラー詳細. デフォルトはNone
            channel (str, optional): 送信先チャンネル. デフォルトはNone (self._channelを使用)
        
        Returns:
            Optional[Dict[str, Any]]: Slack APIレスポンス (エラー時はNone)
        """
        # エラーアイコンを追加
        formatted_message = f":x: *エラー*: {error_message}"
        
        # エラー詳細がある場合は追加
        if details:
            formatted_message += f"\n詳細: {details}"
        
        return self.send_message(
            message=formatted_message,
            channel=channel,
            icon_emoji=":x:"
        )
    
    def send_progress(
        self,
        status: str,
        percentage: int,
        channel: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        進捗状況を通知する。
        
        Args:
            status (str): 進捗状況のメッセージ
            percentage (int): 進捗率（0-100）
            channel (str, optional): 送信先チャンネル. デフォルトはNone (self._channelを使用)
        
        Returns:
            Optional[Dict[str, Any]]: Slack APIレスポンス (エラー時はNone)
        """
        # 進捗率のバリデーション
        valid_percentage = max(0, min(100, percentage))
        
        # 進捗状況アイコンと情報を追加
        formatted_message = f":hourglass_flowing_sand: *進捗状況*: {status} ({valid_percentage}%)"
        
        return self.send_message(
            message=formatted_message,
            channel=channel,
            icon_emoji=":hourglass_flowing_sand:"
        )
    
    def send_checkpoint_notification(
        self,
        checkpoint_id: str,
        channel: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        チェックポイント作成通知を送信する。
        
        Args:
            checkpoint_id (str): チェックポイントID
            channel (str, optional): 送信先チャンネル. デフォルトはNone (self._channelを使用)
        
        Returns:
            Optional[Dict[str, Any]]: Slack APIレスポンス (エラー時はNone)
        """
        # チェックポイント通知メッセージを構築
        formatted_message = f":floppy_disk: *チェックポイント作成*: `{checkpoint_id}`\n再開コマンド: `--resume {checkpoint_id}`"
        
        return self.send_message(
            message=formatted_message,
            channel=channel,
            icon_emoji=":floppy_disk:"
        ) 