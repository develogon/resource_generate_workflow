"""Slackクライアントのテスト"""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from src.clients.slack import (
    SlackClient,
    SlackError,
    ChannelNotFoundError,
    UserNotFoundError
)


@pytest.fixture
def slack_client():
    """Slackクライアントのフィクスチャ"""
    return SlackClient(token="xoxb-test-token")


class TestSlackClient:
    """Slackクライアントのテストクラス"""
    
    @pytest.mark.asyncio
    async def test_initialization(self, slack_client):
        """初期化のテスト"""
        assert slack_client.token == "xoxb-test-token"
        assert slack_client.base_url == "https://slack.com/api"
        assert "Authorization" in slack_client.headers
        assert slack_client.headers["Authorization"] == "Bearer xoxb-test-token"
        assert slack_client.headers["Content-Type"] == "application/json"
        
    @pytest.mark.asyncio
    async def test_send_message_success(self, slack_client):
        """メッセージ送信成功のテスト"""
        mock_response = {
            "ok": True,
            "channel": "C1234567890",
            "ts": "1234567890.123456",
            "message": {
                "text": "Hello, World!",
                "user": "U1234567890"
            }
        }
        
        with patch.object(slack_client, '_request', return_value=mock_response) as mock_request:
            result = await slack_client.send_message(
                channel="general",
                text="Hello, World!",
                blocks=[{"type": "section", "text": {"type": "mrkdwn", "text": "Hello!"}}],
                attachments=[{"color": "good", "text": "Attachment"}],
                thread_ts="1234567890.123456",
                reply_broadcast=True,
                unfurl_links=False,
                unfurl_media=False
            )
            
            assert result == mock_response
            
            args, kwargs = mock_request.call_args
            assert args[0] == "POST"
            assert args[1] == "/chat.postMessage"
            
            json_data = kwargs["json"]
            assert json_data["channel"] == "general"
            assert json_data["text"] == "Hello, World!"
            assert json_data["blocks"] == [{"type": "section", "text": {"type": "mrkdwn", "text": "Hello!"}}]
            assert json_data["attachments"] == [{"color": "good", "text": "Attachment"}]
            assert json_data["thread_ts"] == "1234567890.123456"
            assert json_data["reply_broadcast"] is True
            assert json_data["unfurl_links"] is False
            assert json_data["unfurl_media"] is False
            
    @pytest.mark.asyncio
    async def test_send_message_channel_not_found(self, slack_client):
        """チャンネルが見つからない場合のテスト"""
        mock_response = {
            "ok": False,
            "error": "channel_not_found"
        }
        
        with patch.object(slack_client, '_request', return_value=mock_response):
            with pytest.raises(ChannelNotFoundError):
                await slack_client.send_message("nonexistent", "Hello!")
                
    @pytest.mark.asyncio
    async def test_send_message_error(self, slack_client):
        """メッセージ送信エラーのテスト"""
        mock_response = {
            "ok": False,
            "error": "invalid_auth"
        }
        
        with patch.object(slack_client, '_request', return_value=mock_response):
            with pytest.raises(SlackError, match="メッセージ送信に失敗しました: invalid_auth"):
                await slack_client.send_message("general", "Hello!")
                
    @pytest.mark.asyncio
    async def test_send_file_with_path_success(self, slack_client):
        """ファイルパス指定でのファイル送信成功のテスト"""
        mock_response = {
            "ok": True,
            "file": {
                "id": "F1234567890",
                "name": "test.txt",
                "title": "Test File"
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("test content")
            temp_path = Path(f.name)
            
        try:
            with patch.object(slack_client, '_request', return_value=mock_response) as mock_request:
                result = await slack_client.send_file(
                    channels=["general", "random"],
                    file_path=temp_path,
                    filename="custom.txt",
                    title="Custom File",
                    initial_comment="Here's a file",
                    filetype="text",
                    thread_ts="1234567890.123456"
                )
                
                assert result == mock_response
                
                args, kwargs = mock_request.call_args
                assert args[0] == "POST"
                assert args[1] == "/files.upload"
                
                data = kwargs["data"]
                assert data["channels"] == "general,random"
                assert data["title"] == "Custom File"
                assert data["initial_comment"] == "Here's a file"
                assert data["filetype"] == "text"
                assert data["thread_ts"] == "1234567890.123456"
                
                files = kwargs["files"]
                assert "file" in files
                assert files["file"][0] == "custom.txt"
                
        finally:
            temp_path.unlink()
            
    @pytest.mark.asyncio
    async def test_send_file_with_content_success(self, slack_client):
        """コンテンツ指定でのファイル送信成功のテスト"""
        mock_response = {
            "ok": True,
            "file": {"id": "F1234567890"}
        }
        
        with patch.object(slack_client, '_request', return_value=mock_response) as mock_request:
            result = await slack_client.send_file(
                channels="general",
                content="Hello, World!",
                filename="hello.txt"
            )
            
            assert result == mock_response
            
            files = mock_request.call_args[1]["files"]
            assert files["file"][0] == "hello.txt"
            assert files["file"][1] == b"Hello, World!"
            
    @pytest.mark.asyncio
    async def test_send_file_no_path_or_content(self, slack_client):
        """ファイルパスもコンテンツも指定されていない場合のテスト"""
        with pytest.raises(SlackError, match="file_pathまたはcontentのいずれかを指定してください"):
            await slack_client.send_file(channels="general")
            
    @pytest.mark.asyncio
    async def test_send_file_not_found(self, slack_client):
        """存在しないファイルのテスト"""
        with pytest.raises(FileNotFoundError):
            await slack_client.send_file(
                channels="general",
                file_path="nonexistent.txt"
            )
            
    @pytest.mark.asyncio
    async def test_get_channel_info_success(self, slack_client):
        """チャンネル情報取得成功のテスト"""
        mock_response = {
            "ok": True,
            "channel": {
                "id": "C1234567890",
                "name": "general",
                "is_channel": True,
                "is_private": False
            }
        }
        
        with patch.object(slack_client, '_request', return_value=mock_response) as mock_request:
            result = await slack_client.get_channel_info("C1234567890")
            
            assert result == mock_response["channel"]
            mock_request.assert_called_once_with(
                "GET",
                "/conversations.info",
                params={"channel": "C1234567890"}
            )
            
    @pytest.mark.asyncio
    async def test_get_channel_info_not_found(self, slack_client):
        """チャンネルが見つからない場合のテスト"""
        mock_response = {
            "ok": False,
            "error": "channel_not_found"
        }
        
        with patch.object(slack_client, '_request', return_value=mock_response):
            with pytest.raises(ChannelNotFoundError):
                await slack_client.get_channel_info("C9999999999")
                
    @pytest.mark.asyncio
    async def test_list_channels_success(self, slack_client):
        """チャンネル一覧取得成功のテスト"""
        mock_response = {
            "ok": True,
            "channels": [
                {"id": "C1234567890", "name": "general"},
                {"id": "C0987654321", "name": "random"}
            ]
        }
        
        with patch.object(slack_client, '_request', return_value=mock_response) as mock_request:
            result = await slack_client.list_channels(
                exclude_archived=False,
                types="public_channel",
                limit=50
            )
            
            assert result == mock_response["channels"]
            
            args, kwargs = mock_request.call_args
            params = kwargs["params"]
            assert params["exclude_archived"] is False
            assert params["types"] == "public_channel"
            assert params["limit"] == 50
            
    @pytest.mark.asyncio
    async def test_get_user_info_success(self, slack_client):
        """ユーザー情報取得成功のテスト"""
        mock_response = {
            "ok": True,
            "user": {
                "id": "U1234567890",
                "name": "testuser",
                "real_name": "Test User"
            }
        }
        
        with patch.object(slack_client, '_request', return_value=mock_response) as mock_request:
            result = await slack_client.get_user_info("U1234567890")
            
            assert result == mock_response["user"]
            mock_request.assert_called_once_with(
                "GET",
                "/users.info",
                params={"user": "U1234567890"}
            )
            
    @pytest.mark.asyncio
    async def test_get_user_info_not_found(self, slack_client):
        """ユーザーが見つからない場合のテスト"""
        mock_response = {
            "ok": False,
            "error": "user_not_found"
        }
        
        with patch.object(slack_client, '_request', return_value=mock_response):
            with pytest.raises(UserNotFoundError):
                await slack_client.get_user_info("U9999999999")
                
    @pytest.mark.asyncio
    async def test_list_users_success(self, slack_client):
        """ユーザー一覧取得成功のテスト"""
        mock_response = {
            "ok": True,
            "members": [
                {"id": "U1234567890", "name": "user1"},
                {"id": "U0987654321", "name": "user2"}
            ]
        }
        
        with patch.object(slack_client, '_request', return_value=mock_response) as mock_request:
            result = await slack_client.list_users(
                limit=50,
                include_locale=True
            )
            
            assert result == mock_response["members"]
            
            args, kwargs = mock_request.call_args
            params = kwargs["params"]
            assert params["limit"] == 50
            assert params["include_locale"] is True
            
    @pytest.mark.asyncio
    async def test_get_channel_history_success(self, slack_client):
        """チャンネル履歴取得成功のテスト"""
        mock_response = {
            "ok": True,
            "messages": [
                {"type": "message", "text": "Hello", "ts": "1234567890.123456"},
                {"type": "message", "text": "World", "ts": "1234567891.123456"}
            ]
        }
        
        with patch.object(slack_client, '_request', return_value=mock_response) as mock_request:
            result = await slack_client.get_channel_history(
                channel="C1234567890",
                latest="1234567892.000000",
                oldest="1234567890.000000",
                limit=50,
                inclusive=True
            )
            
            assert result == mock_response["messages"]
            
            args, kwargs = mock_request.call_args
            params = kwargs["params"]
            assert params["channel"] == "C1234567890"
            assert params["latest"] == "1234567892.000000"
            assert params["oldest"] == "1234567890.000000"
            assert params["limit"] == 50
            assert params["inclusive"] is True
            
    @pytest.mark.asyncio
    async def test_add_reaction_success(self, slack_client):
        """リアクション追加成功のテスト"""
        mock_response = {"ok": True}
        
        with patch.object(slack_client, '_request', return_value=mock_response) as mock_request:
            result = await slack_client.add_reaction(
                channel="C1234567890",
                timestamp="1234567890.123456",
                name="thumbsup"
            )
            
            assert result == mock_response
            
            args, kwargs = mock_request.call_args
            assert args[0] == "POST"
            assert args[1] == "/reactions.add"
            
            json_data = kwargs["json"]
            assert json_data["channel"] == "C1234567890"
            assert json_data["timestamp"] == "1234567890.123456"
            assert json_data["name"] == "thumbsup"
            
    @pytest.mark.asyncio
    async def test_create_channel_success(self, slack_client):
        """チャンネル作成成功のテスト"""
        mock_response = {
            "ok": True,
            "channel": {
                "id": "C1234567890",
                "name": "new-channel",
                "is_private": False
            }
        }
        
        with patch.object(slack_client, '_request', return_value=mock_response) as mock_request:
            result = await slack_client.create_channel(
                name="new-channel",
                is_private=False
            )
            
            assert result == mock_response["channel"]
            
            args, kwargs = mock_request.call_args
            json_data = kwargs["json"]
            assert json_data["name"] == "new-channel"
            assert json_data["is_private"] is False
            
    @pytest.mark.asyncio
    async def test_invite_to_channel_success(self, slack_client):
        """チャンネル招待成功のテスト"""
        mock_response = {"ok": True}
        
        with patch.object(slack_client, '_request', return_value=mock_response) as mock_request:
            # 単一ユーザーの招待
            result = await slack_client.invite_to_channel(
                channel="C1234567890",
                users="U1234567890"
            )
            
            assert result == mock_response
            
            json_data = mock_request.call_args[1]["json"]
            assert json_data["users"] == "U1234567890"
            
            # 複数ユーザーの招待
            await slack_client.invite_to_channel(
                channel="C1234567890",
                users=["U1234567890", "U0987654321"]
            )
            
            json_data = mock_request.call_args[1]["json"]
            assert json_data["users"] == "U1234567890,U0987654321"
            
    @pytest.mark.asyncio
    async def test_health_check_success(self, slack_client):
        """ヘルスチェック成功のテスト"""
        mock_response = {
            "ok": True,
            "url": "https://test.slack.com/",
            "team": "Test Team",
            "user": "testuser"
        }
        
        with patch.object(slack_client, '_request', return_value=mock_response) as mock_request:
            is_healthy = await slack_client.health_check()
            
            assert is_healthy is True
            mock_request.assert_called_once_with("GET", "/auth.test")
            
    @pytest.mark.asyncio
    async def test_health_check_failure(self, slack_client):
        """ヘルスチェック失敗のテスト"""
        mock_response = {
            "ok": False,
            "error": "invalid_auth"
        }
        
        with patch.object(slack_client, '_request', return_value=mock_response):
            is_healthy = await slack_client.health_check()
            assert is_healthy is False
            
    @pytest.mark.asyncio
    async def test_health_check_exception(self, slack_client):
        """ヘルスチェック例外のテスト"""
        with patch.object(slack_client, '_request', side_effect=Exception("Connection failed")):
            is_healthy = await slack_client.health_check()
            assert is_healthy is False
            
    @pytest.mark.asyncio
    async def test_stats_tracking(self, slack_client):
        """統計情報追跡のテスト"""
        mock_response = {"ok": True}
        
        with patch.object(slack_client, '_request', return_value=mock_response):
            # メッセージ送信
            await slack_client.send_message("general", "Hello!")
            await slack_client.send_message("random", "World!")
            
            # ファイルアップロード
            await slack_client.send_file("general", content="test", filename="test.txt")
            
            # リアクション追加
            await slack_client.add_reaction("general", "123456", "thumbsup")
            await slack_client.add_reaction("general", "123457", "heart")
            
            # チャンネル作成
            await slack_client.create_channel("new-channel")
            
            # 招待送信
            await slack_client.invite_to_channel("general", "U123456")
            
            assert slack_client.stats['messages_sent'] == 2
            assert slack_client.stats['files_uploaded'] == 1
            assert slack_client.stats['reactions_added'] == 2
            assert slack_client.stats['channels_created'] == 1
            assert slack_client.stats['invitations_sent'] == 1
            
    @pytest.mark.asyncio
    async def test_error_handling(self, slack_client):
        """エラーハンドリングのテスト"""
        # 一般的なSlackエラー
        with patch.object(slack_client, '_request', side_effect=Exception("API Error")):
            with pytest.raises(SlackError):
                await slack_client.send_message("general", "Hello!")
                
        # Slack APIエラーレスポンス
        mock_response = {
            "ok": False,
            "error": "rate_limited"
        }
        
        with patch.object(slack_client, '_request', return_value=mock_response):
            with pytest.raises(SlackError, match="メッセージ送信に失敗しました: rate_limited"):
                await slack_client.send_message("general", "Hello!") 