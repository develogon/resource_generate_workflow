"""Slack APIクライアント実装"""

import json
from datetime import datetime
from typing import Dict, List, Optional, Union, Any
from pathlib import Path

from .base import BaseClient
from ..utils.logger import get_logger

logger = get_logger(__name__)


class SlackError(Exception):
    """Slack API操作エラー"""
    pass


class ChannelNotFoundError(SlackError):
    """チャンネルが見つからないエラー"""
    pass


class UserNotFoundError(SlackError):
    """ユーザーが見つからないエラー"""
    pass


class SlackClient(BaseClient):
    """Slack APIクライアント"""
    
    def __init__(
        self,
        token: str,
        base_url: str = "https://slack.com/api",
        **kwargs
    ):
        super().__init__(base_url=base_url, **kwargs)
        self.token = token
        self.headers.update({
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        })
        
    async def send_message(
        self,
        channel: str,
        text: str,
        blocks: Optional[List[Dict]] = None,
        attachments: Optional[List[Dict]] = None,
        thread_ts: Optional[str] = None,
        reply_broadcast: bool = False,
        unfurl_links: bool = True,
        unfurl_media: bool = True
    ) -> Dict[str, Any]:
        """メッセージを送信
        
        Args:
            channel: チャンネルID、チャンネル名、またはユーザーID
            text: メッセージテキスト
            blocks: Block Kit要素のリスト
            attachments: 添付ファイルのリスト
            thread_ts: スレッドのタイムスタンプ（返信時）
            reply_broadcast: スレッド返信をチャンネルにも投稿するか
            unfurl_links: リンクの展開を有効にするか
            unfurl_media: メディアの展開を有効にするか
            
        Returns:
            送信されたメッセージ情報
        """
        data = {
            "channel": channel,
            "text": text,
            "unfurl_links": unfurl_links,
            "unfurl_media": unfurl_media
        }
        
        if blocks:
            data["blocks"] = blocks
        if attachments:
            data["attachments"] = attachments
        if thread_ts:
            data["thread_ts"] = thread_ts
            data["reply_broadcast"] = reply_broadcast
            
        try:
            response = await self._request("POST", "/chat.postMessage", json=data)
            
            if not response.get("ok"):
                error = response.get("error", "Unknown error")
                if error == "channel_not_found":
                    raise ChannelNotFoundError(f"チャンネルが見つかりません: {channel}")
                raise SlackError(f"メッセージ送信に失敗しました: {error}")
                
            logger.info(f"メッセージを送信しました: {channel}")
            self.stats['messages_sent'] = self.stats.get('messages_sent', 0) + 1
            
            return response
            
        except Exception as e:
            if isinstance(e, SlackError):
                raise
            raise SlackError(f"メッセージ送信に失敗しました: {e}")
            
    async def send_file(
        self,
        channels: Union[str, List[str]],
        file_path: Optional[Union[str, Path]] = None,
        content: Optional[str] = None,
        filename: Optional[str] = None,
        title: Optional[str] = None,
        initial_comment: Optional[str] = None,
        filetype: Optional[str] = None,
        thread_ts: Optional[str] = None
    ) -> Dict[str, Any]:
        """ファイルをアップロード
        
        Args:
            channels: チャンネルID、チャンネル名のリスト
            file_path: アップロードするファイルのパス
            content: ファイル内容（文字列）
            filename: ファイル名
            title: ファイルのタイトル
            initial_comment: 初期コメント
            filetype: ファイルタイプ
            thread_ts: スレッドのタイムスタンプ
            
        Returns:
            アップロードされたファイル情報
        """
        if not file_path and not content:
            raise SlackError("file_pathまたはcontentのいずれかを指定してください")
            
        # チャンネルリストを文字列に変換
        if isinstance(channels, list):
            channels_str = ",".join(channels)
        else:
            channels_str = channels
            
        data = {
            "channels": channels_str
        }
        
        if title:
            data["title"] = title
        if initial_comment:
            data["initial_comment"] = initial_comment
        if filetype:
            data["filetype"] = filetype
        if thread_ts:
            data["thread_ts"] = thread_ts
            
        files = {}
        
        if file_path:
            file_path = Path(file_path)
            if not file_path.exists():
                raise FileNotFoundError(f"ファイルが見つかりません: {file_path}")
                
            with open(file_path, 'rb') as f:
                files["file"] = (filename or file_path.name, f.read())
                
        elif content:
            if not filename:
                filename = "file.txt"
            files["file"] = (filename, content.encode("utf-8"))
            
        try:
            # ファイルアップロード用のヘッダーを一時的に変更
            original_headers = self.headers.copy()
            self.headers.pop("Content-Type", None)  # multipart/form-dataを自動設定させる
            
            response = await self._request(
                "POST",
                "/files.upload",
                data=data,
                files=files
            )
            
            # ヘッダーを元に戻す
            self.headers = original_headers
            
            if not response.get("ok"):
                error = response.get("error", "Unknown error")
                raise SlackError(f"ファイルアップロードに失敗しました: {error}")
                
            logger.info(f"ファイルをアップロードしました: {filename}")
            self.stats['files_uploaded'] = self.stats.get('files_uploaded', 0) + 1
            
            return response
            
        except Exception as e:
            if isinstance(e, SlackError):
                raise
            raise SlackError(f"ファイルアップロードに失敗しました: {e}")
            
    async def get_channel_info(self, channel: str) -> Dict[str, Any]:
        """チャンネル情報を取得
        
        Args:
            channel: チャンネルID
            
        Returns:
            チャンネル情報
        """
        try:
            response = await self._request(
                "GET",
                "/conversations.info",
                params={"channel": channel}
            )
            
            if not response.get("ok"):
                error = response.get("error", "Unknown error")
                if error == "channel_not_found":
                    raise ChannelNotFoundError(f"チャンネルが見つかりません: {channel}")
                raise SlackError(f"チャンネル情報の取得に失敗しました: {error}")
                
            logger.info(f"チャンネル情報を取得しました: {channel}")
            
            return response["channel"]
            
        except Exception as e:
            if isinstance(e, SlackError):
                raise
            raise SlackError(f"チャンネル情報の取得に失敗しました: {e}")
            
    async def list_channels(
        self,
        exclude_archived: bool = True,
        types: str = "public_channel,private_channel",
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """チャンネル一覧を取得
        
        Args:
            exclude_archived: アーカイブされたチャンネルを除外するか
            types: チャンネルタイプ（カンマ区切り）
            limit: 取得件数の上限
            
        Returns:
            チャンネル一覧
        """
        params = {
            "exclude_archived": exclude_archived,
            "types": types,
            "limit": limit
        }
        
        try:
            response = await self._request(
                "GET",
                "/conversations.list",
                params=params
            )
            
            if not response.get("ok"):
                error = response.get("error", "Unknown error")
                raise SlackError(f"チャンネル一覧の取得に失敗しました: {error}")
                
            channels = response.get("channels", [])
            logger.info(f"チャンネル一覧を取得しました: {len(channels)}件")
            
            return channels
            
        except Exception as e:
            if isinstance(e, SlackError):
                raise
            raise SlackError(f"チャンネル一覧の取得に失敗しました: {e}")
            
    async def get_user_info(self, user: str) -> Dict[str, Any]:
        """ユーザー情報を取得
        
        Args:
            user: ユーザーID
            
        Returns:
            ユーザー情報
        """
        try:
            response = await self._request(
                "GET",
                "/users.info",
                params={"user": user}
            )
            
            if not response.get("ok"):
                error = response.get("error", "Unknown error")
                if error == "user_not_found":
                    raise UserNotFoundError(f"ユーザーが見つかりません: {user}")
                raise SlackError(f"ユーザー情報の取得に失敗しました: {error}")
                
            logger.info(f"ユーザー情報を取得しました: {user}")
            
            return response["user"]
            
        except Exception as e:
            if isinstance(e, SlackError):
                raise
            raise SlackError(f"ユーザー情報の取得に失敗しました: {e}")
            
    async def list_users(
        self,
        limit: int = 100,
        include_locale: bool = False
    ) -> List[Dict[str, Any]]:
        """ユーザー一覧を取得
        
        Args:
            limit: 取得件数の上限
            include_locale: ロケール情報を含めるか
            
        Returns:
            ユーザー一覧
        """
        params = {
            "limit": limit,
            "include_locale": include_locale
        }
        
        try:
            response = await self._request(
                "GET",
                "/users.list",
                params=params
            )
            
            if not response.get("ok"):
                error = response.get("error", "Unknown error")
                raise SlackError(f"ユーザー一覧の取得に失敗しました: {error}")
                
            users = response.get("members", [])
            logger.info(f"ユーザー一覧を取得しました: {len(users)}件")
            
            return users
            
        except Exception as e:
            if isinstance(e, SlackError):
                raise
            raise SlackError(f"ユーザー一覧の取得に失敗しました: {e}")
            
    async def get_channel_history(
        self,
        channel: str,
        latest: Optional[str] = None,
        oldest: Optional[str] = None,
        limit: int = 100,
        inclusive: bool = False
    ) -> List[Dict[str, Any]]:
        """チャンネルの履歴を取得
        
        Args:
            channel: チャンネルID
            latest: 最新のタイムスタンプ
            oldest: 最古のタイムスタンプ
            limit: 取得件数の上限
            inclusive: 境界のメッセージを含めるか
            
        Returns:
            メッセージ履歴
        """
        params = {
            "channel": channel,
            "limit": limit,
            "inclusive": inclusive
        }
        
        if latest:
            params["latest"] = latest
        if oldest:
            params["oldest"] = oldest
            
        try:
            response = await self._request(
                "GET",
                "/conversations.history",
                params=params
            )
            
            if not response.get("ok"):
                error = response.get("error", "Unknown error")
                if error == "channel_not_found":
                    raise ChannelNotFoundError(f"チャンネルが見つかりません: {channel}")
                raise SlackError(f"チャンネル履歴の取得に失敗しました: {error}")
                
            messages = response.get("messages", [])
            logger.info(f"チャンネル履歴を取得しました: {channel} ({len(messages)}件)")
            
            return messages
            
        except Exception as e:
            if isinstance(e, SlackError):
                raise
            raise SlackError(f"チャンネル履歴の取得に失敗しました: {e}")
            
    async def add_reaction(
        self,
        channel: str,
        timestamp: str,
        name: str
    ) -> Dict[str, Any]:
        """リアクションを追加
        
        Args:
            channel: チャンネルID
            timestamp: メッセージのタイムスタンプ
            name: リアクション名（絵文字名）
            
        Returns:
            リアクション追加結果
        """
        data = {
            "channel": channel,
            "timestamp": timestamp,
            "name": name
        }
        
        try:
            response = await self._request("POST", "/reactions.add", json=data)
            
            if not response.get("ok"):
                error = response.get("error", "Unknown error")
                raise SlackError(f"リアクション追加に失敗しました: {error}")
                
            logger.info(f"リアクションを追加しました: {name}")
            self.stats['reactions_added'] = self.stats.get('reactions_added', 0) + 1
            
            return response
            
        except Exception as e:
            if isinstance(e, SlackError):
                raise
            raise SlackError(f"リアクション追加に失敗しました: {e}")
            
    async def create_channel(
        self,
        name: str,
        is_private: bool = False
    ) -> Dict[str, Any]:
        """チャンネルを作成
        
        Args:
            name: チャンネル名
            is_private: プライベートチャンネルかどうか
            
        Returns:
            作成されたチャンネル情報
        """
        data = {
            "name": name,
            "is_private": is_private
        }
        
        try:
            response = await self._request("POST", "/conversations.create", json=data)
            
            if not response.get("ok"):
                error = response.get("error", "Unknown error")
                raise SlackError(f"チャンネル作成に失敗しました: {error}")
                
            logger.info(f"チャンネルを作成しました: {name}")
            self.stats['channels_created'] = self.stats.get('channels_created', 0) + 1
            
            return response["channel"]
            
        except Exception as e:
            if isinstance(e, SlackError):
                raise
            raise SlackError(f"チャンネル作成に失敗しました: {e}")
            
    async def invite_to_channel(
        self,
        channel: str,
        users: Union[str, List[str]]
    ) -> Dict[str, Any]:
        """チャンネルにユーザーを招待
        
        Args:
            channel: チャンネルID
            users: ユーザーIDまたはユーザーIDのリスト
            
        Returns:
            招待結果
        """
        if isinstance(users, list):
            users_str = ",".join(users)
        else:
            users_str = users
            
        data = {
            "channel": channel,
            "users": users_str
        }
        
        try:
            response = await self._request("POST", "/conversations.invite", json=data)
            
            if not response.get("ok"):
                error = response.get("error", "Unknown error")
                raise SlackError(f"チャンネル招待に失敗しました: {error}")
                
            logger.info(f"チャンネルにユーザーを招待しました: {channel}")
            self.stats['invitations_sent'] = self.stats.get('invitations_sent', 0) + 1
            
            return response
            
        except Exception as e:
            if isinstance(e, SlackError):
                raise
            raise SlackError(f"チャンネル招待に失敗しました: {e}")
            
    async def health_check(self) -> bool:
        """Slack API接続のヘルスチェック"""
        try:
            response = await self._request("GET", "/auth.test")
            return response.get("ok", False)
        except Exception as e:
            logger.error(f"Slackヘルスチェックに失敗しました: {e}")
            return False 